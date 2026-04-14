from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from pydantic import BaseModel

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


class SeedMarcaItem(BaseModel):
    marca: str
    modelos: List[str]


class SeedMarcasRequest(BaseModel):
    data: List[SeedMarcaItem]


@router.post("/seed")
def seed_marcas_y_modelos(
    request: SeedMarcasRequest,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Carga masiva de marcas y modelos de celulares.
    Es idempotente: si la marca/modelo ya existe lo omite.
    """
    marcas_creadas = []
    marcas_existentes = []
    modelos_creados = []
    modelos_existentes = []
    # marca_nombre → marca_celular_id
    marcas_ids: dict[str, int] = {}
    # (marca_nombre, modelo_nombre) → modelo_celular_id
    modelos_ids: dict[tuple[str, str], int] = {}

    for item in request.data:
        marca = session.exec(
            select(MarcaCelular).where(MarcaCelular.nombre == item.marca)
        ).first()

        if marca:
            marcas_existentes.append(item.marca)
        else:
            marca = MarcaCelular(nombre=item.marca)
            session.add(marca)
            session.flush()
            marcas_creadas.append(item.marca)

        marcas_ids[item.marca] = marca.marca_celular_id  # type: ignore

        for nombre_modelo in item.modelos:
            modelo = session.exec(
                select(ModeloCelular).where(
                    ModeloCelular.marca_celular_id == marca.marca_celular_id,
                    ModeloCelular.nombre == nombre_modelo
                )
            ).first()

            if modelo:
                modelos_existentes.append({"marca": item.marca, "modelo": nombre_modelo})
            else:
                modelo = ModeloCelular(nombre=nombre_modelo, marca_celular_id=marca.marca_celular_id) # type: ignore
                session.add(modelo)
                session.flush()
                modelos_creados.append({"marca": item.marca, "modelo": nombre_modelo})

            modelos_ids[(item.marca, nombre_modelo)] = modelo.modelo_celular_id  # type: ignore

    session.commit()

    return {
        "marcas_creadas": marcas_creadas,
        "marcas_existentes": marcas_existentes,
        "modelos_creados": modelos_creados,
        "modelos_existentes": modelos_existentes,
        "marcas_ids": marcas_ids,
        "modelos_ids": {f"{m}|{mod}": id_ for (m, mod), id_ in modelos_ids.items()},
    }


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