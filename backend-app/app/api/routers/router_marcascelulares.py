from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from typing import Optional, List
from sqlmodel import select, col
from sqlalchemy import exc

from app.db.session import get_session
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(
    prefix="/marcas-celulares",
    tags=["Marcas Celulares"],
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_marca(
    marca: MarcaCelularCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    try:
        nueva_marca = MarcaCelular(**marca.model_dump())
        session.add(nueva_marca)
        session.commit()
        session.refresh(nueva_marca)
        return {"mensaje": "Marca creada exitosamente", "marca": nueva_marca}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una marca con ese nombre"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.get("/", response_model=List[MarcaCelular])
def listar_marcas(
    session: Session = Depends(get_session),
    buscar: Optional[str] = "",
    activo: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    current_user: UsuarioActual = Depends(get_current_user)
):
    statement = select(MarcaCelular).offset(skip).limit(limit)

    if activo is not None:
        statement = statement.where(MarcaCelular.activo == activo)
    if buscar:
        statement = statement.where(col(MarcaCelular.nombre).ilike(f"%{buscar}%"))

    return session.exec(statement).all()


@router.get("/{marca_id}")
def obtener_marca(
    marca_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    marca = session.get(MarcaCelular, marca_id)
    if not marca:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marca no encontrada")
    return marca


@router.put("/{marca_id}")
def actualizar_marca(
    marca_id: int,
    marca_update: MarcaCelularUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    marca = session.get(MarcaCelular, marca_id)
    if not marca:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marca no encontrada")

    try:
        update_data = marca_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(marca, key, value)

        session.commit()
        session.refresh(marca)
        return {"mensaje": "Marca actualizada exitosamente", "marca": marca}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una marca con ese nombre"
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.delete("/{marca_id}", status_code=status.HTTP_200_OK)
def eliminar_marca(
    marca_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Desactiva una marca de celular (soft-delete).
    No se puede desactivar una marca que tenga modelos activos asociados.
    """
    marca = session.get(MarcaCelular, marca_id)
    if not marca:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marca no encontrada")
    if not marca.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La marca ya se encuentra inactiva")

    # Verificar que no tenga modelos activos
    modelos_activos = session.exec(
        select(ModeloCelular).where(
            ModeloCelular.marca_celular_id == marca_id,
            ModeloCelular.activo == True
        )
    ).first()
    if modelos_activos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede desactivar la marca porque tiene modelos activos asociados. Desactivalos primero."
        )

    try:
        marca.activo = False
        session.commit()
        session.refresh(marca)
        return {"mensaje": "Marca desactivada exitosamente", "marca": marca}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")