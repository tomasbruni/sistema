from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session
from pydantic import BaseModel

from typing import Optional, List
from sqlmodel import Session, SQLModel, select, col
from sqlalchemy import exc, func

from app.db.session import get_session
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from app.api.deps import get_current_user, require_admin, UsuarioActual

from zoneinfo import ZoneInfo

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


router = APIRouter(prefix="/ecommerce", 
                   tags=["Ecommerce"])



class ProductoResponse(SQLModel):
    producto_id: int
    tipo_producto: str        # ACCESORIO | CELULAR | CHIP
    nombre_producto: str
    precio_lista: int
    cantidad_disponible: int
    imagenes: List[str] = []  # URLs ordenadas: la primera es la portada


@router.get("/listar-acc", response_model=List[ProductoResponse])
def listar_accesorios_con_stock(
    skip: int = 0,
    limit: int = 100,
    buscar: Optional[str] = "",
    tipo_id: Optional[int] = None,
    subtipo_id: Optional[int] = None,
    marca_celular_id: Optional[int] = None,
    modelo_celular_id: Optional[int] = None,
    solo_disponibles: Optional[bool] = True,
    session: Session = Depends(get_session),
):
  """ Devuelve los accesorios con su correspondiente stock, incluida paginacion.

  El stock total es la suma de las cantidades en los distintos locales (group by).
  Se usa outer join para que un accesorio sin filas en stock_accesorios
  aparezca igual con cantidad 0 (salvo que se pida solo_disponibles).
  """
  cantidad_disponible = func.coalesce(func.sum(StockAccesorio.cantidad), 0)

  statement = (
      select(
          Accesorio.accesorio_id,
          Accesorio.nombre,
          Accesorio.precio,
          cantidad_disponible.label("cantidad_disponible"),
      )
      .outerjoin(StockAccesorio, col(StockAccesorio.accesorio_id) == Accesorio.accesorio_id)
      .where(Accesorio.activo == True)  # noqa: E712
      .group_by(Accesorio.accesorio_id, Accesorio.nombre, Accesorio.precio) #type: ignore
  )

  if buscar:
    statement = statement.where(Accesorio.nombre.ilike(f"%{buscar}%"))  # type: ignore
  if tipo_id is not None:
    statement = statement.where(Accesorio.tipo_id == tipo_id)
  if subtipo_id is not None:
    statement = statement.where(Accesorio.subtipo_id == subtipo_id)
  if marca_celular_id is not None:
    statement = statement.where(Accesorio.marca_celular_id == marca_celular_id)
  if modelo_celular_id is not None:
    statement = statement.where(Accesorio.modelo_celular_id == modelo_celular_id)

  # El filtro sobre el stock sumado va en HAVING, no en WHERE
  if solo_disponibles:
    statement = statement.having(cantidad_disponible > 0)

  statement = (
      statement
      .order_by(Accesorio.nombre)
      .offset(skip)
      .limit(limit)
  )

  filas = session.exec(statement).all()

  # Imagenes en una query aparte para no romper la suma de stock por fan-out
  # (un join a imagenes_accesorios multiplicaria las filas del sum()).
  ids_pagina = [accesorio_id for accesorio_id, *_ in filas]
  imagenes_por_accesorio: dict[int, List[str]] = {}
  if ids_pagina:
    filas_img = session.exec(
        select(ImagenAccesorio.accesorio_id, ImagenAccesorio.url)
        .where(col(ImagenAccesorio.accesorio_id).in_(ids_pagina))
        .order_by(
            col(ImagenAccesorio.es_principal).desc(),
            ImagenAccesorio.orden,
            ImagenAccesorio.imagen_accesorio_id,
        )
    ).all()
    for acc_id, url in filas_img:
      imagenes_por_accesorio.setdefault(acc_id, []).append(url)

  return [
      ProductoResponse(
          producto_id=accesorio_id, #type: ignore
          tipo_producto="ACCESORIO",
          nombre_producto=nombre,
          precio_lista=precio,
          cantidad_disponible=cantidad,
          imagenes=imagenes_por_accesorio.get(accesorio_id, []),
      )
      for accesorio_id, nombre, precio, cantidad in filas
  ]


# =====================
# Categorias para el ecommerce (publico)
# =====================
class SubcategoriaResponse(SQLModel):
    subtipo_id: int
    nombre: str
    imagen_url: Optional[str] = None


class CategoriaResponse(SQLModel):
    tipo_id: int
    nombre: str
    imagen_url: Optional[str] = None
    subtipos: List[SubcategoriaResponse] = []


@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(session: Session = Depends(get_session)):
  """Lista los tipos activos con su imagen y sus subtipos activos anidados.

  Endpoint publico (sin auth) para armar la grilla 'compra por categoria' del
  ecommerce. Los subtipos se traen en una sola query y se agrupan por tipo_id
  para evitar fan-out.
  """
  tipos = session.exec(
      select(TipoAccesorio)
      .where(TipoAccesorio.activo == True)  # noqa: E712
      .order_by(TipoAccesorio.nombre)  # type: ignore
  ).all()

  subtipos = session.exec(
      select(SubtipoAccesorio)
      .where(SubtipoAccesorio.activo == True)  # noqa: E712
      .order_by(SubtipoAccesorio.nombre)  # type: ignore
  ).all()

  subtipos_por_tipo: dict[int, List[SubcategoriaResponse]] = {}
  for st in subtipos:
    subtipos_por_tipo.setdefault(st.tipo_id, []).append(
        SubcategoriaResponse(
            subtipo_id=st.subtipo_id,  # type: ignore
            nombre=st.nombre,
            imagen_url=st.imagen_url,
        )
    )

  return [
      CategoriaResponse(
          tipo_id=tipo.tipo_id,  # type: ignore
          nombre=tipo.nombre,
          imagen_url=tipo.imagen_url,
          subtipos=subtipos_por_tipo.get(tipo.tipo_id, []),  # type: ignore
      )
      for tipo in tipos
  ]







