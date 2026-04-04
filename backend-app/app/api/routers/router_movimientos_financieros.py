from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import SQLModel, Session, select

from app.db.session import get_session
from app.db.models import MovimientoFinanciero, TipoMovimientoFinanciero
from app.api.deps import require_admin, UsuarioActual


router = APIRouter(prefix="/movimientos-financieros", tags=["Movimientos Financieros"])

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


# ── Schemas ───────────────────────────────────────────────────────────────────

class MovimientoFinancieroCreate(SQLModel):
    tipo: TipoMovimientoFinanciero
    monto: int
    descripcion: str


class MovimientoFinancieroUpdate(SQLModel):
    tipo: Optional[TipoMovimientoFinanciero] = None
    monto: Optional[int] = None
    descripcion: Optional[str] = None


class MovimientoFinancieroRead(SQLModel):
    id: int
    tipo: TipoMovimientoFinanciero
    monto: int
    descripcion: str
    fecha: Optional[datetime]
    usuario_id: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _start_of_day(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=TZ_AR)


def _end_of_day(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=TZ_AR)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=MovimientoFinancieroRead, status_code=status.HTTP_201_CREATED)
def crear_movimiento(
    payload: MovimientoFinancieroCreate,
    session: Session = Depends(get_session),
    admin: UsuarioActual = Depends(require_admin),
):
    mov = MovimientoFinanciero(
        tipo=payload.tipo,
        monto=payload.monto,
        descripcion=payload.descripcion,
        usuario_id=admin.usuario_id,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov


@router.get("/", response_model=list[MovimientoFinancieroRead])
def listar_movimientos(
    tipo: Optional[TipoMovimientoFinanciero] = Query(default=None),
    fecha: Optional[date] = Query(default=None),
    fecha_desde: Optional[date] = Query(default=None),
    fecha_hasta: Optional[date] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
    admin: UsuarioActual = Depends(require_admin),
):
    query = select(MovimientoFinanciero)

    if tipo:
        query = query.where(MovimientoFinanciero.tipo == tipo)

    if fecha:
        query = query.where(
            MovimientoFinanciero.fecha >= _start_of_day(fecha),  # type: ignore
            MovimientoFinanciero.fecha <= _end_of_day(fecha),    # type: ignore
        )
    else:
        if fecha_desde:
            query = query.where(MovimientoFinanciero.fecha >= _start_of_day(fecha_desde))  # type: ignore
        if fecha_hasta:
            query = query.where(MovimientoFinanciero.fecha <= _end_of_day(fecha_hasta))    # type: ignore

    query = query.order_by(MovimientoFinanciero.fecha.desc()).offset(offset).limit(limit)  # type: ignore
    return session.exec(query).all()


@router.get("/{mov_id}", response_model=MovimientoFinancieroRead)
def obtener_movimiento(
    mov_id: int,
    session: Session = Depends(get_session),
    admin: UsuarioActual = Depends(require_admin),
):
    mov = session.get(MovimientoFinanciero, mov_id)
    if not mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return mov


@router.patch("/{mov_id}", response_model=MovimientoFinancieroRead)
def actualizar_movimiento(
    mov_id: int,
    payload: MovimientoFinancieroUpdate,
    session: Session = Depends(get_session),
    admin: UsuarioActual = Depends(require_admin),
):
    mov = session.get(MovimientoFinanciero, mov_id)
    if not mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")

    data = payload.model_dump(exclude_unset=True)
    for campo, valor in data.items():
        setattr(mov, campo, valor)

    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov


@router.delete("/{mov_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_movimiento(
    mov_id: int,
    session: Session = Depends(get_session),
    admin: UsuarioActual = Depends(require_admin),
):
    mov = session.get(MovimientoFinanciero, mov_id)
    if not mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    session.delete(mov)
    session.commit()
