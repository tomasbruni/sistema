from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import exc
from datetime import datetime, timezone
from typing import Optional

from app.db.session import get_session
from app.db.models import (
    PedidoOnline, DetallePedidoAccesorio, DetallePedidoCelular, DetallePedidoChip,
    Accesorio, Celular, Chip,
    StockAccesorio, MovimientoStock, TipoMovimiento,
    Venta, PagoVenta, DetalleVentaAccesorio, DetalleVentaCelular, DetalleVentaChip,
    Local,
)
from app.api.modelscreate import PedidoOnlineCreate
from app.api.modelsupdate import PedidoOnlineAdminNota, PedidoOnlineAprobarBody
from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(
    prefix="/pedidos-online",
    tags=["PEDIDOS ONLINE"],
)
# ARREGLAR LOGICA DE PRECIO UNITARIO, VIENE DESDE EL FRONT Y NO DEBERIA
MODOS_ENTREGA_VALIDOS = {"RETIRO_LOCAL", "ENVIO"}
MEDIOS_DE_PAGO_VALIDOS = {"EFECTIVO", "MERCADOPAGO"}


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_pedido(
    pedido_data: PedidoOnlineCreate,
    session: Session = Depends(get_session),
):
    """
    Endpoint público (sin autenticación) para que la tienda online cree pedidos.
    Calcula monto_total sumando precio_lista de cada producto.
    Reglas:
    - EFECTIVO solo puede ser RETIRO_LOCAL
    - RETIRO_LOCAL requiere local_retiro_id
    - ENVIO requiere direccion_envio
    - Al menos un producto en el pedido
    """
    modo = pedido_data.modo_entrega.upper()
    medio = pedido_data.medio_de_pago.upper()

    if modo not in MODOS_ENTREGA_VALIDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modo de entrega inválido. Válidos: {MODOS_ENTREGA_VALIDOS}")

    if medio not in MEDIOS_DE_PAGO_VALIDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Medio de pago inválido. Válidos: {MEDIOS_DE_PAGO_VALIDOS}")

    if medio == "EFECTIVO" and modo != "RETIRO_LOCAL":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pago en efectivo solo está disponible para retiro en local.")

    if modo == "RETIRO_LOCAL" and not pedido_data.local_retiro_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe especificar el local de retiro.")

    if modo == "ENVIO" and not pedido_data.direccion_envio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe especificar la dirección de envío.")

    if not pedido_data.detalles_accesorios and not pedido_data.detalles_celulares and not pedido_data.detalles_chips:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido debe incluir al menos un producto.")

    if pedido_data.detalles_accesorios:
        ids = [d.accesorio_id for d in pedido_data.detalles_accesorios]
        if len(ids) != len(set(ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se permiten accesorios duplicados. Ajustá las cantidades en una sola línea.")

    if pedido_data.detalles_celulares:
        ids = [d.celular_id for d in pedido_data.detalles_celulares]
        if len(ids) != len(set(ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se permiten celulares duplicados en el pedido.")

    if pedido_data.detalles_chips:
        ids = [d.chip_id for d in pedido_data.detalles_chips]
        if len(ids) != len(set(ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se permiten chips duplicados en el pedido.")

    # Validar local de retiro si aplica
    if pedido_data.local_retiro_id:
        local = session.get(Local, pedido_data.local_retiro_id)
        if not local or not local.activo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Local de retiro {pedido_data.local_retiro_id} no encontrado o inactivo.")

    try:
        monto_total = 0

        pedido = PedidoOnline(
            estado="PENDIENTE_APROBACION",
            modo_entrega=modo,
            local_retiro_id=pedido_data.local_retiro_id,
            direccion_envio=pedido_data.direccion_envio,
            nombre_cliente=pedido_data.nombre_cliente,
            telefono_cliente=pedido_data.telefono_cliente,
            mail_cliente=pedido_data.mail_cliente,
            notas_cliente=pedido_data.notas_cliente,
            medio_de_pago=medio,
            referencia_pago=pedido_data.referencia_pago,
            estado_pago="PAGADO" if pedido_data.referencia_pago else "PENDIENTE",
            costo_envio=pedido_data.costo_envio,
            total_productos=0,
            monto_total=0,
        )
        session.add(pedido)
        session.flush()  # obtener pedido_id

        # Detalles accesorios
        for item in (pedido_data.detalles_accesorios or []):
            accesorio = session.get(Accesorio, item.accesorio_id)
            if not accesorio:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Accesorio ID {item.accesorio_id} no encontrado.")
            if not accesorio.activo:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El accesorio '{accesorio.nombre}' no está activo.")
            session.add(DetallePedidoAccesorio(
                pedido_id=pedido.pedido_id,  # type: ignore
                accesorio_id=item.accesorio_id,
                precio_lista=accesorio.precio,
                precio_unitario=item.precio_unitario, #problema de seguridad, precio_unitario viene del front
                cantidad=item.cantidad,
            ))
            monto_total += item.precio_unitario * item.cantidad

        # Detalles celulares
        for item in (pedido_data.detalles_celulares or []):
            celular = session.get(Celular, item.celular_id)
            if not celular:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Celular ID {item.celular_id} no encontrado.")
            if celular.estado.upper() not in ("DISPONIBLE",):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El celular IMEI {celular.imei} no está disponible.")
            session.add(DetallePedidoCelular(
                pedido_id=pedido.pedido_id,  # type: ignore
                celular_id=item.celular_id,
                imei=celular.imei,
                precio_lista=celular.precio,
            ))
            monto_total += celular.precio

        # Detalles chips
        for item in (pedido_data.detalles_chips or []):
            chip = session.get(Chip, item.chip_id)
            if not chip:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chip ID {item.chip_id} no encontrado.")
            if chip.estado.upper() not in ("DISPONIBLE",):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El chip {chip.numero_serie} no está disponible.")
            session.add(DetallePedidoChip(
                pedido_id=pedido.pedido_id,  # type: ignore
                chip_id=item.chip_id,
                numero_serie=chip.numero_serie,
                precio_lista=chip.precio,
            ))
            monto_total += chip.precio

        pedido.total_productos = monto_total
        pedido.monto_total = monto_total + pedido_data.costo_envio
        session.commit()
        session.refresh(pedido)

        return {
            "mensaje": "Pedido recibido exitosamente",
            "pedido_id": pedido.pedido_id,
            "estado": pedido.estado,
            "monto_total": pedido.monto_total,
        }

    except HTTPException:
        session.rollback()
        raise
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de integridad: {str(e)}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}")


@router.get("/")
def listar_pedidos(
    skip: int = 0,
    limit: int = 20,
    estado: Optional[str] = None,
    local_retiro_id: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    query = select(PedidoOnline)

    if estado:
        query = query.where(PedidoOnline.estado == estado.upper())
    if local_retiro_id:
        query = query.where(PedidoOnline.local_retiro_id == local_retiro_id)
    if fecha_desde:
        query = query.where(PedidoOnline.fecha_creacion >= fecha_desde) #type: ignore
    if fecha_hasta:
        query = query.where(PedidoOnline.fecha_creacion <= fecha_hasta) #type: ignore

    query = query.order_by(PedidoOnline.fecha_creacion.desc()).offset(skip).limit(limit)  # type: ignore
    return session.exec(query).all()


@router.get("/{pedido_id}")
def obtener_pedido(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    pedido = session.get(PedidoOnline, pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido {pedido_id} no encontrado.")

    accesorios = session.exec(
        select(DetallePedidoAccesorio).where(DetallePedidoAccesorio.pedido_id == pedido_id)
    ).all()
    celulares = session.exec(
        select(DetallePedidoCelular).where(DetallePedidoCelular.pedido_id == pedido_id)
    ).all()
    chips = session.exec(
        select(DetallePedidoChip).where(DetallePedidoChip.pedido_id == pedido_id)
    ).all()

    return {
        **pedido.model_dump(),
        "detalles": {
            "accesorios": [d.model_dump() for d in accesorios],
            "celulares": [d.model_dump() for d in celulares],
            "chips": [d.model_dump() for d in chips],
        },
    }


@router.post("/{pedido_id}/aprobar", status_code=status.HTTP_200_OK)
def aprobar_pedido(
    pedido_id: int,
    body: PedidoOnlineAprobarBody,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    """
    Aprueba un pedido: reserva stock de accesorios (movimiento RESERVA) y
    marca celulares/chips como RESERVADO.
    El admin debe indicar local_stock_id (de dónde sale el stock).
    """
    pedido = session.get(PedidoOnline, pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido {pedido_id} no encontrado.")
    if pedido.estado != "PENDIENTE_APROBACION":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
            detail=f"El pedido está en estado '{pedido.estado}', no se puede aprobar.")

    accesorios = session.exec(
        select(DetallePedidoAccesorio).where(DetallePedidoAccesorio.pedido_id == pedido_id)
    ).all()
    celulares = session.exec(
        select(DetallePedidoCelular).where(DetallePedidoCelular.pedido_id == pedido_id)
    ).all()
    chips = session.exec(
        select(DetallePedidoChip).where(DetallePedidoChip.pedido_id == pedido_id)
    ).all()

    try:
        pedido.estado = "APROBADO"
        pedido.local_stock_id = body.local_stock_id
        pedido.notas_admin = body.notas_admin
        pedido.usuario_id_admin = current_user.usuario_id
        pedido.fecha_actualizacion = datetime.now(timezone.utc)

        # Reservar accesorios
        for detalle in accesorios:
            stock = session.exec(
                select(StockAccesorio)
                .where(
                    StockAccesorio.accesorio_id == detalle.accesorio_id,
                    StockAccesorio.local_id == body.local_stock_id,
                )
                .with_for_update()
            ).first()

            if not stock:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No hay stock registrado para accesorio ID {detalle.accesorio_id} en el local {body.local_stock_id}.")
            if stock.cantidad < detalle.cantidad:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para accesorio ID {detalle.accesorio_id}. "
                           f"Disponible: {stock.cantidad}, solicitado: {detalle.cantidad}.")

            stock.cantidad -= detalle.cantidad
            session.add(MovimientoStock(
                accesorio_id=detalle.accesorio_id,
                local_id=body.local_stock_id,
                tipo_movimiento=TipoMovimiento.RESERVA,
                cantidad=-detalle.cantidad,
                pedido_online_id=pedido.pedido_id,
                motivo=f"Reserva pedido online #{pedido.pedido_id}",
                usuario_id=current_user.usuario_id,
            ))  # type: ignore

        # Reservar celulares
        for detalle in celulares:
            celular = session.exec(
                select(Celular).where(Celular.celular_id == detalle.celular_id).with_for_update()
            ).first()
            if not celular:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Celular ID {detalle.celular_id} no encontrado.")
            if celular.local_id != body.local_stock_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El celular IMEI {celular.imei} no pertenece al local de stock seleccionado.")
            if celular.estado.upper() != "DISPONIBLE":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El celular IMEI {celular.imei} no está disponible (estado: {celular.estado}).")
            celular.estado = "RESERVADO"

        # Reservar chips
        for detalle in chips:
            chip = session.exec(
                select(Chip).where(Chip.chip_id == detalle.chip_id).with_for_update()
            ).first()
            if not chip:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chip ID {detalle.chip_id} no encontrado.")
            if chip.local_id != body.local_stock_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El chip {chip.numero_serie} no pertenece al local de stock seleccionado.")
            if chip.estado.upper() != "DISPONIBLE":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El chip {chip.numero_serie} no está disponible (estado: {chip.estado}).")
            chip.estado = "RESERVADO"

        session.commit()
        session.refresh(pedido)
        return {"mensaje": "Pedido aprobado y stock reservado.", "pedido_id": pedido.pedido_id, "estado": pedido.estado}

    except HTTPException:
        session.rollback()
        raise
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente (violación de constraint): {str(e)}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}")


@router.post("/{pedido_id}/rechazar", status_code=status.HTTP_200_OK)
def rechazar_pedido(
    pedido_id: int,
    body: PedidoOnlineAdminNota,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    pedido = session.get(PedidoOnline, pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido {pedido_id} no encontrado.")
    if pedido.estado != "PENDIENTE_APROBACION":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
            detail=f"El pedido está en estado '{pedido.estado}', no se puede rechazar.")

    pedido.estado = "RECHAZADO"
    pedido.notas_admin = body.notas_admin
    pedido.usuario_id_admin = current_user.usuario_id
    pedido.fecha_actualizacion = datetime.now(timezone.utc)
    session.commit()
    return {"mensaje": "Pedido rechazado.", "pedido_id": pedido_id, "estado": "RECHAZADO"}


@router.post("/{pedido_id}/entregar", status_code=status.HTTP_200_OK)
def entregar_pedido(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    """
    Marca el pedido como ENTREGADO y genera una Venta de tipo ONLINE:
    - Usa el local con tipo='ONLINE' como local_id de la venta (fallback: local_stock_id del pedido)
    - Crea DetalleVenta* sin modificar stock (ya bajó en aprobación)
    - Cambia celulares/chips de RESERVADO → VENDIDO
    - Reclasifica los movimientos RESERVA del pedido a VENTA y les asigna venta_id
    """
    pedido = session.get(PedidoOnline, pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido {pedido_id} no encontrado.")
    if pedido.estado != "APROBADO":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
            detail=f"El pedido está en estado '{pedido.estado}', no se puede marcar como entregado.")

    accesorios = session.exec(
        select(DetallePedidoAccesorio).where(DetallePedidoAccesorio.pedido_id == pedido_id)
    ).all()
    celulares = session.exec(
        select(DetallePedidoCelular).where(DetallePedidoCelular.pedido_id == pedido_id)
    ).all()
    chips = session.exec(
        select(DetallePedidoChip).where(DetallePedidoChip.pedido_id == pedido_id)
    ).all()

    try:
        # Buscar local ONLINE; si no existe, usar local_stock_id del pedido
        local_online = session.exec(
            select(Local).where(Local.tipo == "ONLINE", Local.activo == True)
        ).first()
        local_venta_id = local_online.local_id if local_online else pedido.local_stock_id

        # ── 1. Crear la Venta ─────────────────────────────────────────────────
        venta = Venta(
            local_id=local_venta_id, #type: ignore
            usuario_id=current_user.usuario_id,
            monto_total=pedido.total_productos,
            tipo="ONLINE",
            pedido_online_id=pedido.pedido_id,
        )
        session.add(venta)
        session.flush()  # obtener venta_id

        # ── 2. Registrar pago ─────────────────────────────────────────────────
        session.add(PagoVenta(
            venta_id=venta.venta_id,  # type: ignore
            medio_de_pago=pedido.medio_de_pago,
            importe=pedido.total_productos,
        ))

        # ── 3. Detalles accesorios (sin tocar stock) ──────────────────────────
        for detalle in accesorios:
            session.add(DetalleVentaAccesorio(
                venta_id=venta.venta_id,  # type: ignore
                accesorio_id=detalle.accesorio_id,
                precio_lista=detalle.precio_lista,
                precio_unitario=detalle.precio_unitario,
                cantidad=detalle.cantidad,
                comision_importe=0,
            ))

        # ── 4. Detalles celulares + marcar VENDIDO ────────────────────────────
        for detalle in celulares:
            celular = session.exec(
                select(Celular).where(Celular.celular_id == detalle.celular_id).with_for_update()
            ).first()
            if not celular:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Celular ID {detalle.celular_id} no encontrado.")
            if celular.estado.upper() != "RESERVADO":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El celular IMEI {celular.imei} no está en estado RESERVADO (estado: {celular.estado}).")
            celular.estado = "VENDIDO"
            session.add(DetalleVentaCelular(
                venta_id=venta.venta_id,  # type: ignore
                celular_id=detalle.celular_id,
                imei=detalle.imei,
                precio_lista=detalle.precio_lista,
                precio_unitario=detalle.precio_lista,
                comision_importe=0,
            ))

        # ── 5. Detalles chips + marcar VENDIDO ────────────────────────────────
        for detalle in chips:
            chip = session.exec(
                select(Chip).where(Chip.chip_id == detalle.chip_id).with_for_update()
            ).first()
            if not chip:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chip ID {detalle.chip_id} no encontrado.")
            if chip.estado.upper() != "RESERVADO":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El chip {chip.numero_serie} no está en estado RESERVADO (estado: {chip.estado}).")
            chip.estado = "VENDIDO"
            session.add(DetalleVentaChip(
                venta_id=venta.venta_id,  # type: ignore
                chip_id=detalle.chip_id,
                numero_serie=detalle.numero_serie,
                precio_lista=detalle.precio_lista,
                precio_unitario=detalle.precio_lista,
                comision_importe=0,
            ))

        # ── 6. Reclasificar movimientos RESERVA → VENTA ───────────────────────
        movimientos = session.exec(
            select(MovimientoStock).where(MovimientoStock.pedido_online_id == pedido_id)
        ).all()
        for mov in movimientos:
            mov.tipo_movimiento = TipoMovimiento.VENTA
            mov.venta_id = venta.venta_id  # type: ignore
            mov.motivo = f"Venta online #{venta.venta_id} (pedido #{pedido_id})"

        # ── 7. Actualizar pedido ──────────────────────────────────────────────
        pedido.estado = "ENTREGADO"
        pedido.estado_pago = "PAGADO"
        pedido.usuario_id_admin = current_user.usuario_id
        pedido.fecha_actualizacion = datetime.now(timezone.utc)

        session.commit()
        return {
            "mensaje": "Pedido marcado como entregado.",
            "pedido_id": pedido_id,
            "estado": "ENTREGADO",
            "venta_id": venta.venta_id,
        }

    except HTTPException:
        session.rollback()
        raise
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de integridad: {str(e)}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}")


@router.post("/{pedido_id}/cancelar", status_code=status.HTTP_200_OK)
def cancelar_pedido(
    pedido_id: int,
    body: PedidoOnlineAdminNota,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    """
    Cancela un pedido APROBADO: revierte stock de accesorios (movimiento ENTRADA)
    y vuelve celulares/chips a DISPONIBLE.
    """
    pedido = session.get(PedidoOnline, pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido {pedido_id} no encontrado.")
    if pedido.estado != "APROBADO":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
            detail=f"El pedido está en estado '{pedido.estado}', no se puede cancelar.")

    accesorios = session.exec(
        select(DetallePedidoAccesorio).where(DetallePedidoAccesorio.pedido_id == pedido_id)
    ).all()
    celulares = session.exec(
        select(DetallePedidoCelular).where(DetallePedidoCelular.pedido_id == pedido_id)
    ).all()
    chips = session.exec(
        select(DetallePedidoChip).where(DetallePedidoChip.pedido_id == pedido_id)
    ).all()

    local_stock_id = pedido.local_stock_id

    try:
        pedido.estado = "CANCELADO"
        pedido.notas_admin = body.notas_admin
        pedido.usuario_id_admin = current_user.usuario_id
        pedido.fecha_actualizacion = datetime.now(timezone.utc)

        # Revertir accesorios
        for detalle in accesorios:
            stock = session.exec(
                select(StockAccesorio)
                .where(
                    StockAccesorio.accesorio_id == detalle.accesorio_id,
                    StockAccesorio.local_id == local_stock_id,
                )
                .with_for_update()
            ).first()

            if not stock:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No se encontró stock para revertir accesorio ID {detalle.accesorio_id}.")

            stock.cantidad += detalle.cantidad
            session.add(MovimientoStock(
                accesorio_id=detalle.accesorio_id,
                local_id=local_stock_id,
                tipo_movimiento=TipoMovimiento.ENTRADA,
                cantidad=detalle.cantidad,
                pedido_online_id=pedido.pedido_id,
                motivo=f"Cancelación pedido online #{pedido.pedido_id}",
                usuario_id=current_user.usuario_id,
            ))  # type: ignore

        # Liberar celulares
        for detalle in celulares:
            celular = session.exec(
                select(Celular).where(Celular.celular_id == detalle.celular_id).with_for_update()
            ).first()
            if not celular:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Celular ID {detalle.celular_id} no encontrado.")
            if celular.estado.upper() != "RESERVADO":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El celular IMEI {celular.imei} no está en estado RESERVADO (estado actual: {celular.estado}).")
            celular.estado = "DISPONIBLE"

        # Liberar chips
        for detalle in chips:
            chip = session.exec(
                select(Chip).where(Chip.chip_id == detalle.chip_id).with_for_update()
            ).first()
            if not chip:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chip ID {detalle.chip_id} no encontrado.")
            if chip.estado.upper() != "RESERVADO":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El chip {chip.numero_serie} no está en estado RESERVADO (estado actual: {chip.estado}).")
            chip.estado = "DISPONIBLE"

        session.commit()
        return {"mensaje": "Pedido cancelado y stock revertido.", "pedido_id": pedido_id, "estado": "CANCELADO"}

    except HTTPException:
        session.rollback()
        raise
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de integridad: {str(e)}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}")
