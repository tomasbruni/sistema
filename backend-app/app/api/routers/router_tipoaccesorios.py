# routes/tipos_accesorios.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import literal
from typing import Optional

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *
from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(
            prefix="/tipos-accesorios", 
            tags=["tipos-accesorios"],
            )


@router.post("/", response_model=TipoAccesorio)
def crear_tipo_accesorio(
    tipo_data: TipoAccesorioCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Crea un nuevo tipo de accesorio"""
    try:
        tipo = TipoAccesorio(**tipo_data.model_dump())
        session.add(tipo)
        session.commit()
        session.refresh(tipo)
        return tipo
        
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un tipo con el nombre '{tipo_data.nombre}'"
        )


@router.get("/{tipo_id}", response_model=TipoAccesorio)
def obtener_tipo_accesorio(
    tipo_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Obtiene un tipo por ID"""
    tipo = session.get(TipoAccesorio, tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    return tipo


@router.get("/", response_model=list[TipoAccesorio])
def listar_tipos_accesorios(
    skip: int = 0,
    limit: int = 100,
    buscar: Optional[str] = None,
    activo: Optional[bool] = True,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Lista tipos de accesorios con búsqueda opcional"""
    statement = select(TipoAccesorio).offset(skip).limit(limit)
    if activo is not None:
        statement = statement.where(TipoAccesorio.activo == activo)
    if buscar:
        statement = statement.where(
            TipoAccesorio.nombre.ilike(f"%{buscar}%")  # type: ignore
        )
    return session.exec(statement).all()

@router.patch("/{tipo_id}", response_model=TipoAccesorio)
def actualizar_tipo_accesorio(
    tipo_id: int,
    tipo_act: TipoAccesorioUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Actualiza el nombre de un tipo"""
    tipo = session.get(TipoAccesorio, tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    
    try:
        tipo.nombre = tipo_act.nombre
        session.add(tipo)
        session.commit()
        session.refresh(tipo)
        return tipo
        
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe otro tipo con el nombre '{tipo_act.nombre}'"
        )


@router.delete("/{tipo_id}")
def eliminar_tipo_accesorio(
    tipo_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Desactiva un tipo de accesorio (soft-delete).
    Los tipos siempre se desactivan ya que pueden estar referenciados
    en accesorios o subtipos.
    """
    tipo = session.get(TipoAccesorio, tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    if not tipo.activo:
        raise HTTPException(
            status_code=400,
            detail="El tipo ya se encuentra inactivo"
        )

    try:
        tipo.activo = False
        session.add(tipo)
        session.commit()
        session.refresh(tipo)
        return {"message": f"Tipo '{tipo.nombre}' desactivado", "tipo_id": tipo_id}
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )