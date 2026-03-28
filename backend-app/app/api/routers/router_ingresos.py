from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from sqlmodel import Session, SQLModel, select, col, Field
from sqlalchemy import exc
from datetime import datetime, date

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from fastapi.responses import StreamingResponse
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from app.api.deps import get_current_user, require_admin, UsuarioActual


router = APIRouter(
    prefix="/ingresos",
    tags=["Ingresos"],
    dependencies=[Depends(require_admin)],
)


class MovimientoDetalleResponse(SQLModel):
    nombre_accesorio: str
    cantidad: int


class IngresoLoteDetalleResponse(SQLModel):
    ingreso_lote_id: int
    fecha: Optional[datetime]
    nombre_receptor: Optional[str]
    movimientos: list[MovimientoDetalleResponse]


@router.get("/")
def listar_ingresos(
    skip: int = 0,
    limit: int = 20,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    local_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    Receptor = aliased(Usuario) # type: ignore

    stmt = (
        select(IngresoLote, Receptor)
        .outerjoin(Receptor, IngresoLote.receptor_id == Receptor.usuario_id)
        .order_by(IngresoLote.fecha.desc())# type: ignore
        .offset(skip)
        .limit(limit)
    )

    if fecha_desde:
        stmt = stmt.where(IngresoLote.fecha >= fecha_desde)# type: ignore
    if fecha_hasta:
        stmt = stmt.where(IngresoLote.fecha <= fecha_hasta)# type: ignore

    rows = session.exec(stmt).all()

    resultado = []
    for ingreso, receptor in rows:
        resultado.append({
            "ingreso_lote_id": ingreso.ingreso_lote_id,
            "fecha":           ingreso.fecha,
            "observaciones":   ingreso.observaciones,
            "nombre_receptor": receptor.nombre if receptor else None,
        })

    return resultado

@router.get("/{ingreso_lote_id}", response_model=IngresoLoteDetalleResponse)
def get_movimientos_por_ingreso_lote(
    ingreso_lote_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    # 1. Buscar el ingreso_lote
    ingreso = session.get(IngresoLote, ingreso_lote_id)
    if not ingreso:
        raise HTTPException(status_code=404, detail="Ingreso de lote no encontrado")

    # 2. Nombre del receptor (puede ser null)
    receptor_nombre = None
    if ingreso.receptor_id:
        receptor = session.get(Usuario, ingreso.receptor_id)
        receptor_nombre = receptor.nombre if receptor else None

    # 3. Movimientos asociados al lote
    movimientos = session.exec(
        select(MovimientoStock)
        .where(MovimientoStock.ingreso_lote_id == ingreso_lote_id)
    ).all()

    if not movimientos:
        raise HTTPException(status_code=404, detail="No hay movimientos para este ingreso de lote")

    # 4. Construir detalle por movimiento
    detalle_movimientos = []
    for mov in movimientos:
        accesorio = session.get(Accesorio, mov.accesorio_id)
        detalle_movimientos.append(
            MovimientoDetalleResponse(
                nombre_accesorio=accesorio.nombre if accesorio else f"ID {mov.accesorio_id}",
                cantidad=mov.cantidad,
            )
        )

    return IngresoLoteDetalleResponse(
        ingreso_lote_id=ingreso.ingreso_lote_id, # type: ignore
        fecha=ingreso.fecha,
        nombre_receptor=receptor_nombre,
        movimientos=detalle_movimientos,
    )