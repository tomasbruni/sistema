from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from typing import Optional, List
from sqlmodel import Session, SQLModel, select, col, or_
from sqlalchemy import exc

from app.db.session import get_session
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(
        prefix="/modelos-celulares",
        tags=["Modelos Celulares"],
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_modelo(
    modelo: ModeloCelularCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    # Validar que la marca existe
    marca = session.get(MarcaCelular, modelo.marca_celular_id)
    if not marca:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marca de celular no encontrada")

    try:
        nuevo_modelo = ModeloCelular(**modelo.model_dump())
        session.add(nuevo_modelo)
        session.commit()
        session.refresh(nuevo_modelo)
        return {"mensaje": "Modelo creado exitosamente", "modelo": nuevo_modelo}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un modelo con ese nombre para esa marca"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.get("/", response_model=List[ModeloCelular])
def listar_modelos(
    session: Session = Depends(get_session),
    buscar: Optional[str] = "",
    marca_celular_id: Optional[int] = None,
    activo: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    current_user: UsuarioActual = Depends(get_current_user)
):
    statement = select(ModeloCelular).offset(skip).limit(limit)

    if activo is not None:
        statement = statement.where(ModeloCelular.activo == activo)
    if marca_celular_id:
        statement = statement.where(ModeloCelular.marca_celular_id == marca_celular_id)
    if buscar:
        statement = statement.where(ModeloCelular.nombre.ilike(f"%{buscar}%"))  # type: ignore

    return session.exec(statement).all()


@router.get("/{modelo_id}")
def obtener_modelo(
    modelo_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    modelo = session.get(ModeloCelular, modelo_id)
    if not modelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")
    return modelo


@router.put("/{modelo_id}")
def actualizar_modelo(
    modelo_id: int,
    modelo_update: ModeloCelularUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    modelo = session.get(ModeloCelular, modelo_id)
    if not modelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")

    try:
        update_data = modelo_update.model_dump(exclude_unset=True)

        # Validar la nueva marca si se está actualizando
        if "marca_celular_id" in update_data:
            marca = session.get(MarcaCelular, update_data["marca_celular_id"])
            if not marca:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marca de celular no encontrada")

        for key, value in update_data.items():
            setattr(modelo, key, value)

        session.commit()
        session.refresh(modelo)
        return {"mensaje": "Modelo actualizado exitosamente", "modelo": modelo}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un modelo con ese nombre para esa marca"
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.delete("/{modelo_id}", status_code=status.HTTP_200_OK)
def eliminar_modelo(
    modelo_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Desactiva un modelo de celular (soft-delete)."""
    modelo = session.get(ModeloCelular, modelo_id)
    if not modelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")
    if not modelo.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El modelo ya se encuentra inactivo")

    try:
        modelo.activo = False
        session.commit()
        session.refresh(modelo)
        return {"mensaje": "Modelo desactivado exitosamente", "modelo": modelo}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")