from typing import Annotated, Optional
import re

from sqlmodel import Session, select, Field

from app.db.models import *
from app.api.modelscreate import *


def normalizar_texto(texto: str, max_length: int = 4) -> str:
    """
    Normaliza texto para SKU: sin acentos, mayúsculas, sin espacios
    """
    if not texto:
        return ""
    
    # Remover acentos
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
        'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
        'ñ': 'n', 'ç': 'c'
    }
    
    texto_lower = texto.lower()
    for orig, repl in replacements.items():
        texto_lower = texto_lower.replace(orig, repl)
    
    # Solo letras y números
    texto_clean = re.sub(r'[^a-z0-9]', '', texto_lower)
    
    return texto_clean[:max_length].upper()



def generar_sku_accesorio(
    tipo_id: int,
    session: Session,
    subtipo_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    modelo_id: Optional[int] = None
) -> str:

    tipo = session.get(TipoAccesorio, tipo_id)
    if not tipo:
        raise ValueError(f"Tipo {tipo_id} no existe")

    tipo_code = normalizar_texto(tipo.nombre, 4)

    spec = "GEN"

    if modelo_id:
        modelo = session.get(ModeloCelular, modelo_id)
        if modelo:
            marca = normalizar_texto(modelo.marca, 2)
            mod = normalizar_texto(modelo.modelo, 3)
            spec = f"{marca}{mod}"

    elif subtipo_id:
        subtipo = session.get(SubtipoAccesorio, subtipo_id)
        if subtipo:
            spec = normalizar_texto(subtipo.nombre, 4)

    elif marca_id:
        marca = session.get(Marca, marca_id)
        if marca:
            spec = normalizar_texto(marca.nombre, 3)

    prefijo = f"{tipo_code}-{spec}"

    statement = (
        select(Accesorio.sku)
        .where(Accesorio.sku.like(f"{prefijo}-%")) #type: ignore
        .order_by(Accesorio.sku.desc()) #type: ignore
        .limit(1)
        .with_for_update()
    )

    ultimo_sku = session.exec(statement).first()

    if ultimo_sku:
        numero = int(ultimo_sku.split("-")[-1]) + 1
    else:
        numero = 1

    return f"{prefijo}-{numero:03d}"


def generar_nombre_accesorio(
    tipo_id: int,
    session: Session,
    subtipo_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    modelo_id: Optional[int] = None
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
    
    if modelo_id:
        modelo = session.get(ModeloCelular, modelo_id)
        if modelo:
            partes.append(f"{modelo.marca} {modelo.modelo}")
    else:
        if marca_id:
            marca = session.get(Marca, marca_id)
            if marca:
                partes.append(marca.nombre)
    
    return " ".join(partes)


# Compilar con parámetros literales (recomendado para debug)
# python3 -m app.api.funciones.accesorios_funciones
# prefijo = 'crobal'
# statement = select(Accesorio).where(
#     Accesorio.sku.like(f"{prefijo}-%")  # type: ignore
# )

# data = Accesorio(nombre = "crobal", tipo_id= 1, subtipo_id=2, activo= True, sku= "vinicius", precio=123) 


# statement = select(Accesorio).where(
#     Accesorio.nombre == data.nombre, #type: ignore
#     Accesorio.tipo_id == data.tipo_id, #type: ignore
#     Accesorio.activo == True # type: ignore
# )

# statement = statement.where(Accesorio.subtipo_id == 5)

# statement = statement.where(Accesorio.marca == None)

# compiled = statement.compile(
#     compile_kwargs={"literal_binds": True}
# )
# print(compiled)