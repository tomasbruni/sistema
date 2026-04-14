from typing import Optional
from sqlmodel import Session, select
from app.db.models import *
from app.api.modelscreate import *


def generar_nombre_accesorio(
    tipo_id: int,
    session: Session,
    subtipo_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    marca_celular_id: Optional[int] = None,
    modelo_celular_id: Optional[int] = None,
) -> str:
    """Genera nombre base descriptivo"""
    partes = []

    tipo = session.get(TipoAccesorio, tipo_id)
    if not tipo:
        return ""
    partes.append(tipo.nombre)

    if subtipo_id:
        subtipo = session.get(SubtipoAccesorio, subtipo_id)
        if subtipo:
            partes.append(subtipo.nombre)

    if modelo_celular_id:
        modelo = session.get(ModeloCelular, modelo_celular_id)
        if modelo:
            marca = session.get(MarcaCelular, modelo.marca_celular_id)
            marca_nombre = marca.nombre if marca else ""
            partes.append(f"{marca_nombre} {modelo.nombre}".strip())
    elif marca_celular_id:
        marca_cel = session.get(MarcaCelular, marca_celular_id)
        if marca_cel:
            partes.append(marca_cel.nombre)
    elif marca_id:
        marca = session.get(Marca, marca_id)
        if marca:
            partes.append(marca.nombre)

    return " ".join(partes)


