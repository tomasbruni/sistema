from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from typing import Optional
from sqlmodel import Session, SQLModel, select, col
from sqlalchemy import exc

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *
from app.api.funciones.accesorios_funciones import normalizar_texto, generar_sku_accesorio, generar_nombre_accesorio
from app.api.deps import get_current_user, require_admin, UsuarioActual

router = APIRouter(prefix="/detalles", 
                   tags=["Detalles"])

@router.get("/venta/{venta_id}")
def detalles_de_venta(
    venta_id: int,
    session: SessionDep,
    usuario: UsuarioActual = Depends(get_current_user)
):
    venta = session.get(Venta, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    accesorios = session.exec(
        select(DetalleVentaAccesorio, Accesorio)
        .join(Accesorio, Accesorio.accesorio_id == DetalleVentaAccesorio.accesorio_id) #type: ignore
        .where(DetalleVentaAccesorio.venta_id == venta_id)
    ).all()

    celulares = session.exec(
        select(DetalleVentaCelular, MarcaCelular, ModeloCelular)
        .join(Celular, Celular.celular_id == DetalleVentaCelular.celular_id) #type: ignore
        .join(MarcaCelular, MarcaCelular.marca_celular_id == Celular.marca_celular_id) #type: ignore
        .join(ModeloCelular,ModeloCelular.modelo_celular_id == Celular.modelo_celular_id) #type: ignore
        .where(DetalleVentaCelular.venta_id == venta_id)
    ).all()

    chips = session.exec(
        select(DetalleVentaChip, Chip)
        .join(Chip, Chip.chip_id == DetalleVentaChip.chip_id) #type: ignore
        .where(DetalleVentaChip.venta_id == venta_id)
    ).all()

    return {
        "venta_id": venta_id,
        "accesorios": [
            {
                **detalle.model_dump(),
                "nombre": accesorio.nombre,
            }
            for detalle, accesorio in accesorios
        ],
        "celulares": [
            {
                **detalle.model_dump(),
                "marca": marca.nombre,
                "modelo": modelo.nombre,
            }
            for detalle, marca, modelo in celulares
        ],
        "chips": [
            {
                **detalle.model_dump(),
                "compania": chip.compania,
            }
            for detalle, chip in chips
        ],
    }