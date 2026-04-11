from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from pydantic import BaseModel

from typing import Optional, List
from sqlmodel import Session, SQLModel, select, col
from sqlalchemy import exc

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *
from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(prefix="/celulares",
                   tags=["Celulares"])


class SeedCelularItem(BaseModel):
    marca: str
    modelo: str
    imei: str
    precio: int


class SeedCelularesRequest(BaseModel):
    local_id: int
    estado: str = "DISPONIBLE"
    data: List[SeedCelularItem]


@router.post("/seed")
def seed_celulares(
    request: SeedCelularesRequest,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Carga masiva de celulares referenciando marca y modelo por nombre.
    Es idempotente: si el IMEI ya existe lo omite.
    """
    local = session.get(Local, request.local_id)
    if not local:
        raise HTTPException(status_code=404, detail="Local no encontrado")

    creados = []
    omitidos = []
    errores = []

    for item in request.data:
        # Idempotencia por IMEI
        if session.exec(select(Celular).where(Celular.imei == item.imei)).first():
            omitidos.append(item.imei)
            continue

        marca = session.exec(
            select(MarcaCelular).where(MarcaCelular.nombre == item.marca)
        ).first()
        if not marca:
            errores.append({"imei": item.imei, "motivo": f"Marca '{item.marca}' no encontrada"})
            continue

        modelo = session.exec(
            select(ModeloCelular).where(
                ModeloCelular.nombre == item.modelo,
                ModeloCelular.marca_celular_id == marca.marca_celular_id
            )
        ).first()
        if not modelo:
            errores.append({"imei": item.imei, "motivo": f"Modelo '{item.modelo}' no encontrado para marca '{item.marca}'"})
            continue

        try:
            celular = Celular(
                marca_celular_id=marca.marca_celular_id,
                modelo_celular_id=modelo.modelo_celular_id,
                imei=item.imei,
                precio=item.precio,
                local_id=request.local_id,
                estado=request.estado,
            )
            session.add(celular)
            session.flush()
            creados.append({"imei": item.imei, "marca": item.marca, "modelo": item.modelo})
        except Exception as e:
            session.rollback()
            errores.append({"imei": item.imei, "motivo": str(e)})
            continue

    session.commit()

    return {
        "creados": creados,
        "omitidos": omitidos,
        "errores": errores,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_celular(
    celular: CelularCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    # Validar que la marca existe
    marca = session.get(MarcaCelular, celular.marca_celular_id)
    if not marca:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marca de celular no encontrada")

    # Validar que el modelo existe y pertenece a esa marca
    modelo = session.get(ModeloCelular, celular.modelo_celular_id)
    if not modelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo de celular no encontrado")
    if modelo.marca_celular_id != celular.marca_celular_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El modelo no pertenece a la marca indicada")

    # Validar que el local existe
    local = session.get(Local, celular.local_id)
    if not local:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local no encontrado")

    try:
        nuevo_celular = Celular(**celular.model_dump())
        session.add(nuevo_celular)
        session.commit()
        session.refresh(nuevo_celular)
        return {"mensaje": "Celular creado exitosamente", "celular": nuevo_celular}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un celular con ese IMEI")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.get("/marcas/disponibles")
def listar_marcas_celulares(
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    marcas = session.exec(select(MarcaCelular).where(MarcaCelular.activo == True)).all()
    return marcas


@router.get("/modelos/disponibles")
def listar_modelos_celulares(
    session: Session = Depends(get_session),
    marca_celular_id: Optional[int] = None,
    current_user: UsuarioActual = Depends(get_current_user)
):
    query = select(ModeloCelular).where(ModeloCelular.activo == True)
    if marca_celular_id:
        query = query.where(ModeloCelular.marca_celular_id == marca_celular_id)
    return session.exec(query).all()


@router.get("/", response_model=List[Celular])
def listar_celulares(
    session: Session = Depends(get_session),
    local_id: Optional[int] = None,
    estado: Optional[str] = None,
    imei: Optional[str] = None,
    marca_celular_id: Optional[int] = None,
    modelo_celular_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UsuarioActual = Depends(get_current_user)
):
    query = select(Celular)

    if local_id:
        query = query.where(Celular.local_id == local_id)
    if estado:
        query = query.where(Celular.estado == estado.upper())
    if imei:
        query = query.where(col(Celular.imei).contains(imei))
    if marca_celular_id:
        query = query.where(Celular.marca_celular_id == marca_celular_id)
    if modelo_celular_id:
        query = query.where(Celular.modelo_celular_id == modelo_celular_id)

    return session.exec(query.offset(skip).limit(limit)).all()


@router.get("/{celular_id}")
def obtener_celular(
    celular_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Celular no encontrado")
    return celular


@router.get("/imei/{imei}")  # deprecado
def buscar_por_imei(
    imei: str,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    celular = session.exec(select(Celular).where(Celular.imei == imei)).first()
    if not celular:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Celular no encontrado")
    return celular


@router.put("/{celular_id}")
def actualizar_celular(
    celular_id: int,
    celular_update: CelularUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Celular no encontrado")

    try:
        update_data = celular_update.model_dump(exclude_unset=True)

        # Validar marca si se está actualizando
        if "marca_celular_id" in update_data:
            marca = session.get(MarcaCelular, update_data["marca_celular_id"])
            if not marca:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marca de celular no encontrada")

        # Validar modelo si se está actualizando
        if "modelo_celular_id" in update_data:
            modelo = session.get(ModeloCelular, update_data["modelo_celular_id"])
            if not modelo:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo de celular no encontrado")
            # Usar la marca del update si viene, sino la actual del celular
            marca_id_a_validar = update_data.get("marca_celular_id", celular.marca_celular_id)
            if modelo.marca_celular_id != marca_id_a_validar:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El modelo no pertenece a la marca indicada")

        if "local_id" in update_data:
            local = session.get(Local, update_data["local_id"])
            if not local:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local no encontrado")

        for key, value in update_data.items():
            setattr(celular, key, value)

        session.commit()
        session.refresh(celular)
        return {"mensaje": "Celular actualizado exitosamente", "celular": celular}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un celular con ese IMEI")
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.delete("/{celular_id}", status_code=status.HTTP_200_OK)
def eliminar_celular(
    celular_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Celular no encontrado")

    try:
        session.delete(celular)
        session.commit()
        return {"mensaje": "Celular eliminado exitosamente"}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el celular porque tiene ventas asociadas. Actualizá el estado a 'VENDIDO' en su lugar."
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")