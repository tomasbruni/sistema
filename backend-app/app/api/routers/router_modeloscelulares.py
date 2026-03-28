from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from typing import Optional, List
from sqlmodel import Session, SQLModel, select, col, or_
from sqlalchemy import exc
from sqlalchemy.sql.expression import literal

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(
        prefix="/modelos-celulares",
        tags=["Modelos Celulares"],
        #dependencies=[Depends(require_admin)]
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_modelo(
    modelo: ModeloCelularCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Crear un nuevo modelo de celular"""
    try:
        nuevo_modelo = ModeloCelular(**modelo.model_dump())
        session.add(nuevo_modelo)
        session.commit()
        session.refresh(nuevo_modelo)
        
        return {
            "mensaje": "Modelo creado exitosamente",
            "modelo": nuevo_modelo
        }
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un modelo con esa marca y modelo"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )


@router.get("/", response_model=List[ModeloCelular])
def listar_modelos(
    session: Session = Depends(get_session),
    buscar: Optional[str] = "",
    activo: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    current_user: UsuarioActual = Depends(get_current_user)
):
    statement = select(ModeloCelular).offset(skip).limit(limit)
    if activo is not None:
        statement = statement.where(ModeloCelular.activo == activo)
    if buscar:
        statement = statement.where(
            or_(
                ModeloCelular.marca.ilike(f"%{buscar}%"),  # type: ignore
                ModeloCelular.modelo.ilike(f"%{buscar}%")  # type: ignore
            )
        )
    return session.exec(statement).all()


@router.get("/{modelo_id}")
def obtener_modelo(
    modelo_id: int,
    session: Session = Depends(get_session)
):
    """Obtener un modelo específico por ID"""
    modelo = session.get(ModeloCelular, modelo_id)
    if not modelo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modelo no encontrado"
        )
    return modelo


@router.put("/{modelo_id}")
def actualizar_modelo(
    modelo_id: int,
    modelo_update: ModeloCelularUpdate,
    session: Session = Depends(get_session)
):
    """Actualizar un modelo de celular"""
    modelo = session.get(ModeloCelular, modelo_id)
    if not modelo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modelo no encontrado"
        )
    
    try:
        # Actualizar solo los campos proporcionados
        update_data = modelo_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(modelo, key, value)
        
        session.commit()
        session.refresh(modelo)
        
        return {
            "mensaje": "Modelo actualizado exitosamente",
            "modelo": modelo
        }
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un modelo con esa marca y modelo"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )


@router.delete("/{modelo_id}", status_code=status.HTTP_200_OK)
def eliminar_modelo(
    modelo_id: int,
    session: Session = Depends(get_session)
):
    """
    Desactiva un modelo de celular (soft-delete).
    Los modelos siempre se desactivan ya que pueden estar referenciados
    en celulares o accesorios.
    """
    modelo = session.get(ModeloCelular, modelo_id)
    if not modelo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modelo no encontrado"
        )
    if not modelo.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El modelo ya se encuentra inactivo"
        )

    try:
        modelo.activo = False
        session.commit()
        session.refresh(modelo)
        return {"mensaje": "Modelo desactivado exitosamente", "modelo": modelo}
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )
