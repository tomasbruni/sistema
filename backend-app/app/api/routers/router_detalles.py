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
from app.api.funciones.accesorios_funciones import generar_nombre_accesorio
from app.api.funciones.ventas_funciones import get_detalles_by_venta, get_pagos_by_venta
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

    detalles_by_venta = get_detalles_by_venta(session, [venta_id])
    detalles = detalles_by_venta[venta_id]

    return {
        "venta_id": venta_id,
        "vendedor": vendedor.nombre,  # type: ignore
        "accesorios": [d for d in detalles if d["tipo_producto"] == "ACCESORIO"],
        "celulares":  [d for d in detalles if d["tipo_producto"] == "CELULAR"],
        "chips":      [d for d in detalles if d["tipo_producto"] == "CHIP"],
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
    pagos_by_venta: dict[int, list[PagoResumen]] = {
        vid: [PagoResumen(medio_de_pago=p.medio_de_pago, importe=p.importe) for p in pagos]
        for vid, pagos in get_pagos_by_venta(session, venta_ids).items() # type: ignore
    }

    # --- Detalles agrupados por venta ---
    raw = get_detalles_by_venta(session, venta_ids) #type: ignore
    detalles_by_venta: dict[int, list[DetalleRow]] = {
        vid: [
            DetalleRow(
                tipo_producto=d["tipo_producto"],
                nombre_producto=d["nombre_producto"],
                precio_lista=d["precio_lista"],
                precio_unitario=d["precio_unitario"],
                cantidad=d["cantidad"],
                codigo=d["codigo"],
            )
            for d in dets
        ]
        for vid, dets in raw.items()
    }

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