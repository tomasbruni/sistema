# PARA VENTAS
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import exc
from typing import Optional

from app.db.session import get_session
from app.db.models import (
    Venta, PagoVenta,
    DetalleVentaAccesorio, DetalleVentaCelular, DetalleVentaChip,
    Accesorio, Celular, Chip,
    StockAccesorio, MovimientoStock, TipoMovimiento,
    ConfigComision, Usuario
)
from app.api.modelscreate import VentaCreate
from app.api.deps import get_current_user, UsuarioActual
from app.api.funciones.fechas import start_of_day

router = APIRouter(
    prefix="/ventas",
    tags=["VENTAS"],
)

MEDIOS_DE_PAGO_VALIDOS = {"EFECTIVO", "DEBITO", "CREDITO", "QR", "TRANSFERENCIA", "MERCADOPAGO"}
TIPOS_DE_VENTAS_VALIDOS = {"VENTA", "DEVOLUCION", "ONLINE"}

def _calcular_comision(config: ConfigComision | None, precio_unitario: int, cantidad: int = 1) -> int:
    """Calcula el importe de comisión. Si no hay config retorna 0."""
    if config is None:
        return 0
    if config.tipo_calculo == "PORCENTAJE":
        return round(precio_unitario * cantidad * config.valor / 100)
    else:  # FIJO: monto fijo por unidad
        return config.valor * cantidad


@router.post("/crear-venta", status_code=status.HTTP_201_CREATED)
def crear_venta(
    venta_data: VentaCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """
    Crear una venta completa:
    - Valida pagos y productos
    - Calcula monto_total desde los detalles (no se recibe del frontend)
    - Calcula comisiones por producto según ConfigComision
    - Registra pagos
    - Crea detalles de accesorios, celulares y chips
    - Actualiza stock de accesorios y registra movimientos
    - Actualiza estado de celulares y chips a VENDIDO
    - En DEVOLUCION: revierte stock y estados, guarda monto_total negativo
    """
    
    if venta_data.tipo.upper() not in TIPOS_DE_VENTAS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de venta inválido: Válidos: {TIPOS_DE_VENTAS_VALIDOS}"
        )
    
    es_devolucion = venta_data.tipo.upper() == "DEVOLUCION"

    # ── Validar medios de pago ────────────────────────────────────────────────
    for pago in venta_data.pagos:
        if pago.medio_de_pago.upper() not in MEDIOS_DE_PAGO_VALIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Medio de pago inválido: '{pago.medio_de_pago}'. Válidos: {MEDIOS_DE_PAGO_VALIDOS}"
            )
        
        if pago.medio_de_pago.upper() == "EFECTIVO" and pago.cuotas and pago.cuotas > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El pago en efectivo no puede tener cuotas."
            )

    # ── Validar que haya al menos un producto ─────────────────────────────────
    if not venta_data.detalles_accesorios and not venta_data.detalles_celulares and not venta_data.detalles_chips:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La venta debe incluir al menos un producto."
        )

    # ── Validar duplicados en listas ──────────────────────────────────────────
    if venta_data.detalles_accesorios:
        ids = [d.accesorio_id for d in venta_data.detalles_accesorios]
        if len(ids) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se permiten accesorios duplicados. Ajustá las cantidades en una sola línea."
            )

    if venta_data.detalles_celulares:
        ids = [d.celular_id for d in venta_data.detalles_celulares]
        if len(ids) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se permiten celulares duplicados en la venta."
            )

    if venta_data.detalles_chips:
        ids = [d.chip_id for d in venta_data.detalles_chips]
        if len(ids) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se permiten chips duplicados en la venta."
            )

    # ── Cargar configs de comisiones (una sola query cada una) ───────────────
    config_acc  = session.exec(select(ConfigComision).where(ConfigComision.tipo_producto == "ACCESORIO")).first()
    config_cel  = session.exec(select(ConfigComision).where(ConfigComision.tipo_producto == "CELULAR")).first()
    config_chip = session.exec(select(ConfigComision).where(ConfigComision.tipo_producto == "CHIP")).first()

    try:
        monto_total = 0

        # Comprobacion de usuario
        if current_user.rol == 'admin' and venta_data.usuario_id is not None:
            usuario = session.get(Usuario, venta_data.usuario_id)
            if not usuario:
                raise HTTPException(404, "Usuario no existe")
            usuarioAsignado = usuario.usuario_id        
        else:
            usuarioAsignado = current_user.usuario_id
            
        # ── 1. Crear la venta principal (monto_total se actualiza al final) ───
        venta_kwargs: dict = dict(
            local_id=venta_data.local_id,
            usuario_id=usuarioAsignado,
            monto_total=0,  # se calcula y actualiza antes del commit
            tipo=venta_data.tipo.upper(),
        )
        if current_user.rol == 'admin' and venta_data.fecha_ingreso is not None:
            venta_kwargs["fecha_ingreso"] = start_of_day(venta_data.fecha_ingreso)
        venta = Venta(**venta_kwargs)
        session.add(venta)
        session.flush()  # obtener venta_id

        # ── 2. Registrar pagos ────────────────────────────────────────────────
        # En devolución el importe es negativo para que la suma de pagos refleje
        # correctamente la ganancia del período sin lógica extra en los reportes
        for pago in venta_data.pagos:
            session.add(PagoVenta(
                venta_id=venta.venta_id,  # type: ignore
                medio_de_pago=pago.medio_de_pago.upper(),
                importe=-pago.importe if es_devolucion else pago.importe,
                cuotas=pago.cuotas
            ))

        detalles_creados = {"accesorios": [], "celulares": [], "chips": []}
        movimientos_stock = []

        # ── 3. Procesar accesorios ────────────────────────────────────────────
        for detalle_acc in (venta_data.detalles_accesorios or []):
            if detalle_acc.cantidad <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La cantidad del accesorio {detalle_acc.accesorio_id} debe ser mayor a cero."
                )

            accesorio = session.get(Accesorio, detalle_acc.accesorio_id)
            if not accesorio:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Accesorio ID {detalle_acc.accesorio_id} no encontrado.")
            if not accesorio.activo:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El accesorio '{accesorio.nombre}' no está activo.")

            # Stock con lock para evitar race conditions
            stock = session.exec(
                select(StockAccesorio)
                .where(
                    StockAccesorio.accesorio_id == detalle_acc.accesorio_id,
                    StockAccesorio.local_id == venta_data.local_id,
                )
                .with_for_update() # bloquea hasta el commit
            ).first()

            if not stock:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No hay stock registrado para '{accesorio.nombre}' en este local.")

            if es_devolucion:
                stock.cantidad += detalle_acc.cantidad
            else:
                if stock.cantidad < detalle_acc.cantidad:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Stock insuficiente para '{accesorio.nombre}'. "
                               f"Disponible: {stock.cantidad}, solicitado: {detalle_acc.cantidad}.")
                stock.cantidad -= detalle_acc.cantidad

            comision    = _calcular_comision(config_acc, detalle_acc.precio_unitario, detalle_acc.cantidad)
            comision    = -comision if es_devolucion else comision
            subtotal    = detalle_acc.precio_unitario * detalle_acc.cantidad
            monto_total += subtotal

            #Precio lista se pone automaticamente desde aca
            session.add(DetalleVentaAccesorio(
                venta_id=venta.venta_id,  # type: ignore
                accesorio_id=detalle_acc.accesorio_id,
                precio_lista=accesorio.precio,
                precio_unitario=detalle_acc.precio_unitario,
                cantidad=detalle_acc.cantidad,
                comision_importe=comision,
            ))

            # Movimiento negativo en venta, positivo en devolución
            cantidad_mov = detalle_acc.cantidad if es_devolucion else -detalle_acc.cantidad
            session.add(MovimientoStock(
                accesorio_id=detalle_acc.accesorio_id,
                local_id=venta_data.local_id,
                tipo_movimiento=TipoMovimiento.VENTA,
                cantidad=cantidad_mov,
                venta_id= venta.venta_id, 
                motivo=f"{'Devolución' if es_devolucion else 'Venta'} #{venta.venta_id} - {accesorio.nombre}",
                usuario_id=usuarioAsignado,
            )) # type: ignore
            movimientos_stock.append(detalle_acc.accesorio_id)

            detalles_creados["accesorios"].append({
                "accesorio_id": detalle_acc.accesorio_id,
                "nombre": accesorio.nombre,
                "cantidad": detalle_acc.cantidad,
                "precio_unitario": detalle_acc.precio_unitario,
                "comision_importe": comision,
            })

        # ── 4. Procesar celulares ─────────────────────────────────────────────
        for detalle_cel in (venta_data.detalles_celulares or []):
            celular = session.get(Celular, detalle_cel.celular_id)
            if not celular:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Celular ID {detalle_cel.celular_id} no encontrado.")
            if celular.local_id != venta_data.local_id:                          
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El celular IMEI {celular.imei} no pertenece a este local.")
            if es_devolucion:
                if celular.estado.upper() != "VENDIDO":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"El celular IMEI {celular.imei} no figura como vendido, no se puede devolver.")
                celular.estado = "DISPONIBLE"
            else:
                if celular.estado.upper() == "VENDIDO":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"El celular IMEI {celular.imei} ya fue vendido.")
                celular.estado = "VENDIDO"

            comision    = _calcular_comision(config_cel, detalle_cel.precio_unitario)
            comision    = -comision if es_devolucion else comision
            monto_total += detalle_cel.precio_unitario

            session.add(DetalleVentaCelular(
                venta_id=venta.venta_id,  # type: ignore
                celular_id=detalle_cel.celular_id,
                imei=celular.imei,
                precio_lista=celular.precio,
                precio_unitario=detalle_cel.precio_unitario,
                comision_importe=comision,
            ))

            detalles_creados["celulares"].append({
                "celular_id": detalle_cel.celular_id,
                "imei": celular.imei,
                "precio_unitario": detalle_cel.precio_unitario,
                "comision_importe": comision,
            })

        # ── 5. Procesar chips ─────────────────────────────────────────────────
        for detalle_chip in (venta_data.detalles_chips or []):
            chip = session.get(Chip, detalle_chip.chip_id)
            if not chip:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chip ID {detalle_chip.chip_id} no encontrado.")
            if chip.local_id != venta_data.local_id:                            
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El chip {chip.numero_serie} no pertenece a este local.")
            if es_devolucion:
                if chip.estado.upper() != "VENDIDO":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"El chip {chip.numero_serie} no figura como vendido, no se puede devolver.")
                chip.estado = "DISPONIBLE"
            else:
                if chip.estado.upper() == "VENDIDO":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"El chip {chip.numero_serie} ya fue vendido.")
                chip.estado = "VENDIDO"

            comision    = _calcular_comision(config_chip, detalle_chip.precio_unitario)
            comision    = -comision if es_devolucion else comision
            monto_total += detalle_chip.precio_unitario

            session.add(DetalleVentaChip(
                venta_id=venta.venta_id,  # type: ignore
                chip_id=detalle_chip.chip_id,
                numero_serie=chip.numero_serie,
                precio_lista=chip.precio,
                precio_unitario=detalle_chip.precio_unitario,
                comision_importe=comision,
            ))

            detalles_creados["chips"].append({
                "chip_id": detalle_chip.chip_id,
                "numero_serie": chip.numero_serie,
                "precio_unitario": detalle_chip.precio_unitario,
                "comision_importe": comision,
            })

        # ── 6. Validar que la suma de pagos coincida con el total de productos ──
        total_pagado = sum(pago.importe for pago in venta_data.pagos)
        if total_pagado != monto_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La suma de los pagos ({total_pagado}) no coincide con el total de los productos ({monto_total})."
            )
 
        # ── 7. Actualizar monto_total ─────────────────────────────────────────
        # Devolución se guarda negativo para que los reportes cuadren
        venta.monto_total = -monto_total if es_devolucion else monto_total

        session.commit()
        session.refresh(venta)

        return {
            "mensaje": "Devolución registrada exitosamente" if es_devolucion else "Venta registrada exitosamente",
            "venta": {
                "venta_id": venta.venta_id,
                "local_id": venta.local_id,
                "usuario_id": venta.usuario_id,
                "fecha_ingreso": venta.fecha_ingreso,
                "monto_total": venta.monto_total,
                "tipo": venta.tipo,
            },
            "pagos": [
                {"medio_de_pago": p.medio_de_pago, "importe": p.importe}
                for p in venta_data.pagos
            ],
            "detalles": detalles_creados,
            "movimientos_stock_generados": len(movimientos_stock),
        }

    except HTTPException:
        session.rollback()
        raise
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Error de integridad: {str(e)}.'
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )
    

@router.get("/")
def listar_ventas(
    skip: int = 0,
    limit: int = 20,
    local_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """
    Listado paginado de ventas.
    Devuelve fecha, tipo, monto_total y pagos de cada venta.
    Para ver los detalles de productos usar GET /ventas/{venta_id}.
    """

    # 🔹 Query base
    query = select(Venta)

    # 🔹 Filtro opcional
    if local_id is not None:
        query = query.where(Venta.local_id == local_id)

    # 🔹 Orden + paginación
    query = query.order_by(Venta.fecha_ingreso.desc()).offset(skip).limit(limit)  # type: ignore

    ventas = session.exec(query).all()

    resultado = []
    for venta in ventas:
        pagos = session.exec(
            select(PagoVenta).where(PagoVenta.venta_id == venta.venta_id)
        ).all()

        resultado.append({
            "venta_id":      venta.venta_id,
            "fecha_ingreso": venta.fecha_ingreso,
            "tipo":          venta.tipo,
            "monto_total":   venta.monto_total,
            "pagos": [
                {"medio_de_pago": p.medio_de_pago, "importe": p.importe}
                for p in pagos
            ],
        })

    return resultado
 
 
@router.get("/{venta_id}")
def obtener_venta(
    venta_id: int,
    session: Session = Depends(get_session)
):
    """
    Detalle completo de una venta: datos principales, pagos y
    todos los productos vendidos (accesorios, celulares, chips).
    """
    venta = session.get(Venta, venta_id)
    if not venta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Venta {venta_id} no encontrada.")
 
    pagos = session.exec(
        select(PagoVenta).where(PagoVenta.venta_id == venta_id)
    ).all()
 
    accesorios = session.exec(
        select(DetalleVentaAccesorio).where(DetalleVentaAccesorio.venta_id == venta_id)
    ).all()
 
    celulares = session.exec(
        select(DetalleVentaCelular).where(DetalleVentaCelular.venta_id == venta_id)
    ).all()
 
    chips = session.exec(
        select(DetalleVentaChip).where(DetalleVentaChip.venta_id == venta_id)
    ).all()
 
    return {
        "venta_id":      venta.venta_id,
        "fecha_ingreso": venta.fecha_ingreso,
        "tipo":          venta.tipo,
        "monto_total":   venta.monto_total,
        "local_id":      venta.local_id,
        "usuario_id":    venta.usuario_id,
        "pagos": [
            {"medio_de_pago": p.medio_de_pago, "importe": p.importe}
            for p in pagos
        ],
        "detalles": {
            "accesorios": [
                {
                    "detalle_id":       d.detalle_id,
                    "accesorio_id":     d.accesorio_id,
                    "precio_unitario":  d.precio_unitario,
                    "cantidad":         d.cantidad,
                    "comision_importe": d.comision_importe,
                }
                for d in accesorios
            ],
            "celulares": [
                {
                    "detalle_id":       d.detalle_id,
                    "celular_id":       d.celular_id,
                    "imei":             d.imei,
                    "precio_unitario":  d.precio_unitario,
                    "comision_importe": d.comision_importe,
                }
                for d in celulares
            ],
            "chips": [
                {
                    "detalle_id":       d.detalle_id,
                    "chip_id":          d.chip_id,
                    "numero_serie":     d.numero_serie,
                    "precio_unitario":  d.precio_unitario,
                    "comision_importe": d.comision_importe,
                }
                for d in chips
            ],
        },
    }