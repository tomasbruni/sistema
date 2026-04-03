from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from collections import defaultdict
from datetime import datetime, date, timezone
from typing import Optional
from sqlmodel import Session, SQLModel, select, col
from sqlalchemy import exc

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *
from app.api.funciones.accesorios_funciones import normalizar_texto, generar_sku_accesorio, generar_nombre_accesorio
from app.api.deps import get_current_user, require_admin, UsuarioActual

from zoneinfo import ZoneInfo

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


router = APIRouter(prefix="/detalles", 
                   tags=["Detalles"])

@router.get("/venta/{venta_id}")
def detalles_de_venta(
    venta_id: int,
    session: SessionDep,
    usuario: UsuarioActual = Depends(get_current_user)
):
    venta = session.get(Venta, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    vendedor = session.get(Usuario, venta.usuario_id)

    accesorios = session.exec(
        select(DetalleVentaAccesorio, Accesorio)
        .join(Accesorio, Accesorio.accesorio_id == DetalleVentaAccesorio.accesorio_id) #type: ignore
        .where(DetalleVentaAccesorio.venta_id == venta_id)
    ).all()

    celulares = session.exec(
        select(DetalleVentaCelular, MarcaCelular, ModeloCelular)
        .join(Celular, Celular.celular_id == DetalleVentaCelular.celular_id) #type: ignore
        .join(MarcaCelular, MarcaCelular.marca_celular_id == Celular.marca_celular_id) #type: ignore
        .join(ModeloCelular,ModeloCelular.modelo_celular_id == Celular.modelo_celular_id) #type: ignore
        .where(DetalleVentaCelular.venta_id == venta_id)
    ).all()

    chips = session.exec(
        select(DetalleVentaChip, Chip)
        .join(Chip, Chip.chip_id == DetalleVentaChip.chip_id) #type: ignore
        .where(DetalleVentaChip.venta_id == venta_id)
    ).all()

    return {
        "venta_id": venta_id,
        "vendedor": vendedor.nombre, #type: ignore
        "accesorios": [
            {
                **detalle.model_dump(),
                "nombre": accesorio.nombre,
            }
            for detalle, accesorio in accesorios
        ],
        "celulares": [
            {
                **detalle.model_dump(),
                "marca": marca.nombre,
                "modelo": modelo.nombre,
            }
            for detalle, marca, modelo in celulares
        ],
        "chips": [
            {
                **detalle.model_dump(),
                "compania": chip.compania,
            }
            for detalle, chip in chips
        ],
    }

# ---- Schemas corregidos ----

class PagoResumen(SQLModel):
    medio_de_pago: str
    importe: int

class DetalleRow(SQLModel):
    tipo_producto: str        # ACCESORIO | CELULAR | CHIP
    nombre_producto: str
    precio_lista: int
    precio_unitario: int
    cantidad: int
    codigo: Optional[str] = None

class VentaRow(SQLModel):
    venta_id: int
    tipo: str
    fecha: datetime
    detalles: list[DetalleRow]
    pagos: list[PagoResumen]
    monto_total: int

class VentasPorPeriodoResponse(SQLModel):
    vendedora: str
    local: str
    desde: date
    hasta: date
    ventas: list[VentaRow]


# ---- Endpoint ----

@router.get("/ventas-por-periodo", response_model=VentasPorPeriodoResponse)
def ventas_por_periodo(
    local_id: int,
    usuario_id: int,
    fecha: Optional[date] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    session: Session = Depends(get_session),
    usuario: UsuarioActual = Depends(get_current_user)
):
    # --- Resolver rango ---
    if fecha:
        dt_desde = datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0, tzinfo=TZ_AR)
        dt_hasta = datetime(fecha.year, fecha.month, fecha.day, 23, 59, 59, tzinfo=TZ_AR)
    elif desde and hasta:
        dt_desde = datetime(desde.year, desde.month, desde.day, 0, 0, 0, tzinfo=TZ_AR)
        dt_hasta = datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59, tzinfo=TZ_AR)
    else:
        raise HTTPException(status_code=400, detail="Debe indicar 'fecha' o 'desde' + 'hasta'")


    # --- Vendedora ---
    vendedora = session.get(Usuario, usuario_id)
    if not vendedora:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")


    # --- Local ---
    local = session.get(Local, local_id)
    if not local:
        raise HTTPException(status_code=404, detail="Local no encontrado")


    # --- Ventas ---
    ventas = session.exec(
        select(Venta)
        .where(Venta.local_id == local_id)
        .where(Venta.usuario_id == usuario_id)
        .where(Venta.fecha_ingreso >= dt_desde) #type: ignore
        .where(Venta.fecha_ingreso <= dt_hasta) #type: ignore
    ).all()


    if not ventas:
        return VentasPorPeriodoResponse(
            vendedora=vendedora.nombre,
            local=local.nombre,
            desde=desde or fecha, #type: ignore
            hasta=hasta or fecha, #type: ignore
            ventas=[],
        )

    venta_ids = [v.venta_id for v in ventas]
    ventas_by_id = {v.venta_id: v for v in ventas}

    # --- Pagos agrupados por venta ---
    pagos_by_venta: dict[int, list[PagoResumen]] = defaultdict(list)
    for p in session.exec(select(PagoVenta).where(PagoVenta.venta_id.in_(venta_ids))).all(): #type: ignore
        pagos_by_venta[p.venta_id].append(
            PagoResumen(medio_de_pago=p.medio_de_pago, importe=p.importe)
        )

    # --- Detalles agrupados por venta ---
    detalles_by_venta: dict[int, list[DetalleRow]] = defaultdict(list)

    # Accesorios
    for detalle, acc in session.exec(
        select(DetalleVentaAccesorio, Accesorio)
        .join(Accesorio, DetalleVentaAccesorio.accesorio_id == Accesorio.accesorio_id) #type: ignore
        .where(DetalleVentaAccesorio.venta_id.in_(venta_ids)) #type: ignore
    ).all():
        detalles_by_venta[detalle.venta_id].append(DetalleRow(
            tipo_producto="ACCESORIO",
            nombre_producto=acc.nombre,
            precio_lista=detalle.precio_lista,
            precio_unitario=detalle.precio_unitario,
            cantidad=detalle.cantidad,
        ))

    # Celulares
    for detalle, cel, modelo, marca in session.exec(
        select(DetalleVentaCelular, Celular, ModeloCelular, MarcaCelular)
        .join(Celular, DetalleVentaCelular.celular_id == Celular.celular_id) #type: ignore
        .join(ModeloCelular, Celular.modelo_celular_id == ModeloCelular.modelo_celular_id) #type: ignore
        .join(MarcaCelular, Celular.marca_celular_id == MarcaCelular.marca_celular_id) #type: ignore
        .where(DetalleVentaCelular.venta_id.in_(venta_ids)) #type: ignore
    ).all():
        detalles_by_venta[detalle.venta_id].append(DetalleRow(
            tipo_producto="CELULAR",
            nombre_producto=f"{marca.nombre} {modelo.nombre}",
            precio_lista=detalle.precio_lista,
            precio_unitario=detalle.precio_unitario,
            cantidad=1,
            codigo=cel.imei,
        ))

    # Chips
    for detalle, chip in session.exec(
        select(DetalleVentaChip, Chip)
        .join(Chip, DetalleVentaChip.chip_id == Chip.chip_id) #type: ignore
        .where(DetalleVentaChip.venta_id.in_(venta_ids)) #type: ignore
    ).all():
        detalles_by_venta[detalle.venta_id].append(DetalleRow(
            tipo_producto="CHIP",
            nombre_producto=f"Chip {chip.compania}",
            precio_lista=detalle.precio_lista,
            precio_unitario=detalle.precio_unitario,
            cantidad=1,
            codigo = chip.numero_serie,
        ))

    # --- Armar respuesta ---
    ventas_rows = [
        VentaRow(
            venta_id=v.venta_id,
            tipo= v.tipo,
            fecha=v.fecha_ingreso,
            detalles=detalles_by_venta[v.venta_id],
            pagos=pagos_by_venta[v.venta_id],
            monto_total=v.monto_total,
        )
        for v in sorted(ventas, key=lambda v: v.fecha_ingreso) #type: ignore
    ]

    return VentasPorPeriodoResponse(
        local=local.nombre,
        vendedora=vendedora.nombre,
        desde=desde or fecha, #type: ignore
        hasta=hasta or fecha, #type: ignore
        ventas=ventas_rows,
    )