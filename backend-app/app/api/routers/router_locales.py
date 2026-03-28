from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import exc
from sqlalchemy.sql.expression import literal
from typing import List, Optional

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(
    prefix="/locales", 
    tags=["Locales"],
    #dependencies=[Depends(require_admin)]
    )

@router.get("/", response_model=list[Local])
def listar_locales(
    activo: Optional[bool] = True,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    statement = select(Local)
    if activo is not None:
        statement = statement.where(Local.activo == activo)
    return session.exec(statement).all()

@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_local(
    local: LocalCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    try:
        if not (local.tipo in ["LOCAL","DEPOSITO","ONLINE"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error, tipo debe ser: LOCAL, DEPOSITO, ONLINE"
            )

        nuevo_local = Local(**local.model_dump())
        session.add(nuevo_local)
        session.commit()
        session.refresh(nuevo_local)
        
        return {
            "mensaje": "Local creado exitosamente",
            "local": nuevo_local
        }
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error: {str(e)}"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )


@router.put("/{local_id}")
def actualizar_local(
    local_id: int,
    local_update: LocalUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Actualizar un local"""
    local = session.get(Local, local_id)
    if not local:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local no encontrado"
        )
    
    try:
        update_data = local_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(local, key, value)
        
        session.commit()
        session.refresh(local)
        
        return {
            "mensaje": "Local actualizado exitosamente",
            "local": local
        }
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un local con ese nombre"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )


@router.delete("/{local_id}", status_code=status.HTTP_200_OK)
def eliminar_local(
    local_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Desactiva un local (soft-delete).
    Los locales siempre se desactivan ya que pueden estar referenciados
    en celulares, chips, stock, movimientos, transferencias, ventas o reparaciones.
    """
    local = session.get(Local, local_id)
    if not local:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local no encontrado"
        )
    if not local.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El local ya se encuentra inactivo"
        )

    try:
        local.activo = False
        session.commit()
        session.refresh(local)
        return {"mensaje": "Local desactivado exitosamente", "local": local}
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )
