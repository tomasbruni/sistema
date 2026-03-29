# routes/subtipos_accesorios.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from typing import Optional
from sqlmodel import Session, SQLModel, select, col
from sqlalchemy import exc
from sqlalchemy.sql.expression import literal

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(
            prefix="/subtipos-accesorios",
            tags=["subtipos-accesorios"],
            #dependencies=[Depends(require_admin)]
            )


@router.post("/", response_model=SubtipoAccesorio)
def crear_subtipo_accesorio(
    subtipo_data: SubtipoAccesorioCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Crea un nuevo subtipo de accesorio"""
    try:
        subtipo = SubtipoAccesorio(**subtipo_data.model_dump())
        session.add(subtipo)
        session.commit()
        session.refresh(subtipo)
        return subtipo
        
    except exc.IntegrityError as e:
        session.rollback()
        
        # Mensaje genérico pero útil
        raise HTTPException(
            status_code=400,
            detail=(
                "No se pudo crear el subtipo. "
                "Verifique que el nombre no esté duplicado y que el tipo seleccionado exista."
            )
        )


@router.get("/{subtipo_id}", response_model=SubtipoAccesorio)
def obtener_subtipo_accesorio(
    subtipo_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Obtiene un subtipo por ID"""
    subtipo = session.get(SubtipoAccesorio, subtipo_id)
    if not subtipo:
        raise HTTPException(status_code=404, detail="Subtipo no encontrado")
    return subtipo


@router.get("/", response_model=list[SubtipoAccesorio])
def listar_subtipos_accesorios(
    skip: int = 0,
    limit: int = 100,
    tipo_id: Optional[int] = None,
    buscar: Optional[str] = None,
    activo: Optional[bool] = True,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """
    Lista subtipos de accesorios.
    - **tipo_id**: Filtrar por tipo de accesorio
    - **buscar**: Búsqueda parcial por nombre
    - **activo**: Filtrar por estado (default: activos)
    """
    statement = select(SubtipoAccesorio).offset(skip).limit(limit)
    if activo is not None:
        statement = statement.where(SubtipoAccesorio.activo == activo)
    if tipo_id:
        statement = statement.where(SubtipoAccesorio.tipo_id == tipo_id)
    if buscar:
        statement = statement.where(
            SubtipoAccesorio.nombre.ilike(f"%{buscar}%")  # type: ignore
        )
    return session.exec(statement).all()


@router.patch("/{subtipo_id}", response_model=SubtipoAccesorio)
def actualizar_subtipo_accesorio(
    subtipo_id: int,
    subtipo_act: SubtipoAccesorioUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    subtipo = session.get(SubtipoAccesorio, subtipo_id)
    if not subtipo:
        raise HTTPException(status_code=404, detail="Subtipo no encontrado")

    update_data = subtipo_act.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un campo para actualizar")

    try:
        for key, value in update_data.items():
            setattr(subtipo, key, value)

        session.add(subtipo)
        session.commit()
        session.refresh(subtipo)
        return subtipo
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo actualizar el subtipo. Verifique que el nombre no esté duplicado y que el tipo seleccionado exista."
        )
        


@router.delete("/{subtipo_id}")
def eliminar_subtipo_accesorio(
    subtipo_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Desactiva un subtipo de accesorio (soft-delete).
    Los subtipos siempre se desactivan ya que pueden estar referenciados en accesorios.
    """
    subtipo = session.get(SubtipoAccesorio, subtipo_id)
    if not subtipo:
        raise HTTPException(status_code=404, detail="Subtipo no encontrado")
    if not subtipo.activo:
        raise HTTPException(
            status_code=400,
            detail="El subtipo ya se encuentra inactivo"
        )

    try:
        subtipo.activo = False
        session.add(subtipo)
        session.commit()
        session.refresh(subtipo)
        return {
            "message": f"Subtipo '{subtipo.nombre}' desactivado",
            "subtipo_id": subtipo_id
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )