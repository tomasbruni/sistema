from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from typing import Optional, List
from sqlmodel import Session, SQLModel, select, col
from sqlalchemy import exc
from sqlalchemy.sql.expression import literal

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *
from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(prefix="/celulares", 
                   #dependencies=[Depends(require_admin)],
                   tags=["Celulares"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_celular(
    celular: CelularCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Crear un nuevo celular"""
    # Validar que el modelo existe
    modelo = session.get(ModeloCelular, celular.modelo_id)
    if not modelo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modelo de celular no encontrado"
        )
    
    # Validar que el local existe
    local = session.get(Local, celular.local_id)
    if not local:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local no encontrado"
        )
    
    try:
        nuevo_celular = Celular(**celular.model_dump())
        session.add(nuevo_celular)
        session.commit()
        session.refresh(nuevo_celular)
        
        return {
            "mensaje": "Celular creado exitosamente",
            "celular": nuevo_celular
        }
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un celular con ese IMEI"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )


@router.get("/marcas/disponibles")
def listar_marcas_celulares(session: Session = Depends(get_session), current_user: UsuarioActual = Depends(get_current_user)):
    marcas = session.exec(
        select(ModeloCelular.marca).distinct().order_by(ModeloCelular.marca)
    ).all()
    return marcas

@router.get("/", response_model=List[Celular],)
def listar_celulares(
    session: Session = Depends(get_session),
    local_id: Optional[int] = None,
    estado: Optional[str] = None,
    imei: Optional[str] = None,
    marca: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UsuarioActual = Depends(get_current_user)
):
    query = select(Celular).join(ModeloCelular, Celular.modelo_id == ModeloCelular.modelo_id)  # type: ignore

    if local_id:
        query = query.where(Celular.local_id == local_id)
    if estado:
        query = query.where(Celular.estado == estado.upper())
    if imei:
        query = query.where(col(Celular.imei).contains(imei))
    if marca:
        query = query.where(ModeloCelular.marca == marca)

    return session.exec(query.offset(skip).limit(limit)).all()


@router.get("/{celular_id}")
def obtener_celular(
    celular_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Obtener un celular específico por ID"""
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular no encontrado"
        )
    return celular

# deprecado
@router.get("/imei/{imei}")
def buscar_por_imei(
    imei: str,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Buscar celular por IMEI"""
    celular = session.exec(
        select(Celular).where(Celular.imei == imei)
    ).first()
    
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular no encontrado"
        )
    return celular


@router.put("/{celular_id}")
def actualizar_celular(
    celular_id: int,
    celular_update: CelularUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Actualizar un celular"""
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular no encontrado"
        )
    
    try:
        update_data = celular_update.model_dump(exclude_unset=True)
        
        # Validar modelo si se está actualizando
        if "modelo_id" in update_data:
            modelo = session.get(ModeloCelular, update_data["modelo_id"])
            if not modelo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Modelo de celular no encontrado"
                )
        
        # Validar local si se está actualizando
        if "local_id" in update_data:
            local = session.get(Local, update_data["local_id"])
            if not local:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Local no encontrado"
                )
        
        for key, value in update_data.items():
            setattr(celular, key, value)
        
        session.commit()
        session.refresh(celular)
        
        return {
            "mensaje": "Celular actualizado exitosamente",
            "celular": celular
        }
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un celular con ese IMEI"
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )


@router.delete("/{celular_id}", status_code=status.HTTP_200_OK)
def eliminar_celular(
    celular_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Elimina un celular físicamente.
    Si el celular tiene ventas asociadas (detalles_ventas_celulares), 
    la operación es rechazada — en ese caso actualizá el estado a 'VENDIDO' en su lugar.
    """
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular no encontrado"
        )
    
    try:
        session.delete(celular)
        session.commit()
        return {"mensaje": "Celular eliminado exitosamente"}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se puede eliminar el celular porque tiene ventas asociadas. "
                "Actualizá el estado a 'VENDIDO' en su lugar."
            )
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )
