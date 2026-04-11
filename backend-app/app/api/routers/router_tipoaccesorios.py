# routes/tipos_accesorios.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import literal
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *
from app.api.deps import get_current_user, require_admin, UsuarioActual

class SeedTiposRequest(BaseModel):
    data: dict[str, list[str]]


router = APIRouter(
            prefix="/tipos-accesorios", 
            tags=["tipos-accesorios"],
            )


@router.post("/seed")
def seed_tipos_y_subtipos(
    request: SeedTiposRequest,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Carga masiva de tipos y subtipos a partir de un dict.
    Ej: {"funda": ["silicona", "rígida"], "cargador": ["v8", "tipo c"]}
    Es idempotente: si el tipo/subtipo ya existe lo omite.
    """
    tipos_creados = []
    tipos_existentes = []
    subtipos_creados = []
    subtipos_existentes = []

    for nombre_tipo, nombres_subtipos in request.data.items():
        tipo = session.exec(
            select(TipoAccesorio).where(TipoAccesorio.nombre == nombre_tipo)
        ).first()

        if tipo:
            tipos_existentes.append(nombre_tipo)
        else:
            tipo = TipoAccesorio(nombre=nombre_tipo)
            session.add(tipo)
            session.flush()  # para obtener tipo_id antes del commit
            tipos_creados.append(nombre_tipo)

        for nombre_subtipo in nombres_subtipos:
            subtipo = session.exec(
                select(SubtipoAccesorio).where(
                    SubtipoAccesorio.tipo_id == tipo.tipo_id,
                    SubtipoAccesorio.nombre == nombre_subtipo
                )
            ).first()

            if subtipo:
                subtipos_existentes.append({"tipo": nombre_tipo, "subtipo": nombre_subtipo})
            else:
                subtipo = SubtipoAccesorio(nombre=nombre_subtipo, tipo_id=tipo.tipo_id)
                session.add(subtipo)
                subtipos_creados.append({"tipo": nombre_tipo, "subtipo": nombre_subtipo})

    session.commit()

    return {
        "tipos_creados": tipos_creados,
        "tipos_existentes": tipos_existentes,
        "subtipos_creados": subtipos_creados,
        "subtipos_existentes": subtipos_existentes,
    }


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
    tipo = session.get(TipoAccesorio, tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    try:
        update_data = tipo_act.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tipo, key, value)

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