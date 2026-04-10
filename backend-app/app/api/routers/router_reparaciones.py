from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, SQLModel
from sqlalchemy import exc
from typing import Optional
from datetime import datetime

from app.db.session import get_session
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(
    prefix="/reparaciones",
    tags=["Reparaciones"],
)


# ── Inputs para transiciones ──────────────────────────────────────────────────

class CambioPrecioInput(SQLModel):
    monto_agregado: int
    observaciones: Optional[str] = None


class TransicionInput(SQLModel):
    observaciones: Optional[str] = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_or_404(reparacion_id: int, session: Session) -> Reparacion:
    reparacion = session.get(Reparacion, reparacion_id)
    if not reparacion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reparación no encontrada")
    return reparacion


# ── GET ───────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[Reparacion])
def listar_reparaciones(
    estado: Optional[str] = None,
    local_id: Optional[int] = None,
    dni_cliente: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    statement = select(Reparacion)
    if estado is not None:
        statement = statement.where(Reparacion.estado == estado)
    if local_id is not None:
        statement = statement.where(Reparacion.local_id == local_id)
    if dni_cliente is not None:
        statement = statement.where(Reparacion.dni_cliente.contains(dni_cliente))  # type: ignore
    if fecha_desde is not None:
        statement = statement.where(Reparacion.fecha_ingreso >= fecha_desde)  # type: ignore
    if fecha_hasta is not None:
        statement = statement.where(Reparacion.fecha_ingreso <= fecha_hasta)  # type: ignore
    return session.exec(statement).all()


@router.get("/{reparacion_id}", response_model=Reparacion)
def obtener_reparacion(
    reparacion_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    return _get_or_404(reparacion_id, session)


@router.get("/{reparacion_id}/historial", response_model=list[MovimientoReparacion])
def listar_historial_reparacion(
    reparacion_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    _get_or_404(reparacion_id, session)
    statement = (
        select(MovimientoReparacion)
        .where(MovimientoReparacion.reparacion_id == reparacion_id)
        .order_by(MovimientoReparacion.fecha)  # type: ignore
    )
    return session.exec(statement).all()


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_reparacion(
    data: ReparacionCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    try:
        nueva = Reparacion(
            **data.model_dump(),
            estado="EN_REPARACION",
            usuario_id=current_user.usuario_id,
        )
        session.add(nueva)
        session.commit()
        session.refresh(nueva)
        return {"mensaje": "Reparación creada exitosamente", "reparacion": nueva}
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error: {str(e)}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


# ── UPDATE (campos de datos, sin estado) ──────────────────────────────────────

@router.put("/{reparacion_id}")
def actualizar_reparacion(
    reparacion_id: int,
    data: ReparacionUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    try:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(reparacion, key, value)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Reparación actualizada exitosamente", "reparacion": reparacion}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error de integridad al actualizar")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


# ── TRANSICIONES ──────────────────────────────────────────────────────────────

@router.post("/{reparacion_id}/cambio-de-precio")
def cambio_de_precio(
    reparacion_id: int,
    data: CambioPrecioInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    try:
        monto_anterior = reparacion.total
        monto_nuevo = monto_anterior + data.monto_agregado
        reparacion.total = monto_nuevo

        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_PRECIO",
            estado_anterior=reparacion.estado,
            estado_nuevo=reparacion.estado,
            monto_total_anterior=monto_anterior,
            monto_total_nuevo=monto_nuevo,
            usuario_id=current_user.usuario_id,
            observaciones=data.observaciones,
        )
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Precio actualizado exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.post("/{reparacion_id}/entregar")
def entregar(
    reparacion_id: int,
    data: TransicionInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    if reparacion.estado != "EN_REPARACION":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se puede entregar una reparación en estado EN_REPARACION (actual: {reparacion.estado})")
    try:
        estado_anterior = reparacion.estado
        reparacion.estado = "ENTREGADO"

        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ESTADO",
            estado_anterior=estado_anterior,
            estado_nuevo="ENTREGADO",
            monto_entrega_recibido=reparacion.total - reparacion.adelanto,
            usuario_id=current_user.usuario_id,
            observaciones=data.observaciones,
        )
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Reparación entregada exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.post("/{reparacion_id}/garantia")
def garantia(
    reparacion_id: int,
    data: TransicionInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    if reparacion.estado != "ENTREGADO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se puede enviar a garantía una reparación en estado ENTREGADO (actual: {reparacion.estado})")
    try:
        estado_anterior = reparacion.estado
        reparacion.estado = "REPARACION_GARANTIA"

        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ESTADO",
            estado_anterior=estado_anterior,
            estado_nuevo="REPARACION_GARANTIA",
            usuario_id=current_user.usuario_id,
            observaciones=data.observaciones,
        )
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Reparación enviada a garantía exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.post("/{reparacion_id}/entregar-garantia")
def entregar_garantia(
    reparacion_id: int,
    data: TransicionInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    if reparacion.estado != "REPARACION_GARANTIA":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se puede entregar la garantía de una reparación en estado REPARACION_GARANTIA (actual: {reparacion.estado})")
    try:
        estado_anterior = reparacion.estado
        reparacion.estado = "ENTREGADO_GARANTIA"

        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ESTADO",
            estado_anterior=estado_anterior,
            estado_nuevo="ENTREGADO_GARANTIA",
            usuario_id=current_user.usuario_id,
            observaciones=data.observaciones,
        )
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Garantía entregada exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")
