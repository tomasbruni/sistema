import os

import cloudinary
import cloudinary.uploader
import cloudinary.api

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.session import get_session
from app.db.models import Accesorio, ImagenAccesorio, TipoAccesorio, SubtipoAccesorio
from app.api.deps import require_admin, UsuarioActual


class ReordenImagenes(BaseModel):
    # ids de las imagenes en el nuevo orden deseado (portada primero)
    orden: list[int]

# ─── CONFIG ─────────────────────────────────────────────────────────────────
# En produccion (Render) estas variables se cargan desde el panel de Environment.
# Los valores por defecto son solo para pruebas locales: reemplazar por los de tu
# cuenta o, mejor, exportarlos en el shell / venv antes de levantar el server.
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dnuhgzoto")
CLOUDINARY_API_KEY    = os.environ.get("CLOUDINARY_API_KEY", "247847381456239")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "bFACPX6ypRvF46uR491t5Wu2dnk")

cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key    = CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET,
    secure     = True,
)

router = APIRouter(prefix="/cloudinary", tags=["Cloudinary"])


@router.post("/accesorios/{accesorio_id}/imagenes")
def subir_imagenes_accesorio(
    accesorio_id: int,
    files: list[UploadFile],
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
  """Sube una o varias imagenes a Cloudinary y las asocia al accesorio.

  Cada archivo se sube a la carpeta `accesorios/{accesorio_id}` y se guarda una
  fila en `imagenes_accesorios` con la URL segura y el public_id (para poder
  borrarla luego). Si el accesorio no tenia imagenes, la primera queda como
  principal. Se sube todo a Cloudinary primero; recien despues se persiste en
  una sola transaccion.
  """
  if not session.get(Accesorio, accesorio_id):
    raise HTTPException(status_code=404, detail="Accesorio no encontrado")

  # estado actual para calcular orden y si ya hay portada
  existentes = session.exec(
      select(ImagenAccesorio).where(ImagenAccesorio.accesorio_id == accesorio_id)
  ).all()
  ya_hay_principal = any(img.es_principal for img in existentes)
  siguiente_orden = (max((img.orden for img in existentes), default=-1)) + 1

  # 1) subir todo a Cloudinary (llamada de red, sync)
  subidas = []
  for file in files:
    try:
      resultado = cloudinary.uploader.upload(
          file.file,
          folder=f"accesorios/{accesorio_id}",
          resource_type="image",
      )
    except Exception as e:
      raise HTTPException(
          status_code=502,
          detail=f"Error al subir '{file.filename}' a Cloudinary: {e}",
      )
    subidas.append(resultado)

  # 2) persistir las filas en una sola transaccion
  imagenes = []
  for i, resultado in enumerate(subidas):
    imagen = ImagenAccesorio(
        accesorio_id=accesorio_id,
        url=resultado["secure_url"],
        public_id=resultado["public_id"],
        orden=siguiente_orden + i,
        es_principal=(not ya_hay_principal and i == 0),
    )
    session.add(imagen)
    imagenes.append(imagen)

  session.commit()
  for imagen in imagenes:
    session.refresh(imagen)
  return imagenes


@router.put("/accesorios/{accesorio_id}/imagenes/orden")
def reordenar_imagenes_accesorio(
    accesorio_id: int,
    data: ReordenImagenes,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
  """Reordena las imagenes de un accesorio segun la lista de ids recibida.

  `data.orden` debe contener exactamente los ids de todas las imagenes del
  accesorio, en el orden deseado. El `orden` de cada fila se asigna por su
  posicion en la lista (0, 1, 2, ...).
  """
  imagenes = session.exec(
      select(ImagenAccesorio).where(ImagenAccesorio.accesorio_id == accesorio_id)
  ).all()
  if not imagenes:
    raise HTTPException(status_code=404, detail="El accesorio no tiene imagenes")

  ids_actuales = {img.imagen_accesorio_id for img in imagenes}
  if set(data.orden) != ids_actuales or len(data.orden) != len(ids_actuales):
    raise HTTPException(
        status_code=400,
        detail="La lista de orden debe contener exactamente los ids de las imagenes del accesorio",
    )

  por_id = {img.imagen_accesorio_id: img for img in imagenes}
  for posicion, imagen_id in enumerate(data.orden):
    imagen = por_id[imagen_id]
    imagen.orden = posicion
    session.add(imagen)

  session.commit()
  return session.exec(
      select(ImagenAccesorio)
      .where(ImagenAccesorio.accesorio_id == accesorio_id)
      .order_by(ImagenAccesorio.orden, ImagenAccesorio.imagen_accesorio_id) #type: ignore
  ).all()


@router.delete("/accesorios/{accesorio_id}/imagenes/{imagen_id}")
def eliminar_imagen_accesorio(
    accesorio_id: int,
    imagen_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
  """Borra una imagen de Cloudinary (via public_id) y su fila en la DB.

  Si la imagen borrada era la principal y quedan otras, promueve la de menor
  orden a principal para que el accesorio no quede sin portada.
  """
  imagen = session.get(ImagenAccesorio, imagen_id)
  if not imagen or imagen.accesorio_id != accesorio_id:
    raise HTTPException(status_code=404, detail="Imagen no encontrada")

  # borrar el asset en Cloudinary (si tiene public_id; las cargadas a mano no)
  if imagen.public_id:
    try:
      cloudinary.uploader.destroy(imagen.public_id, resource_type="image")
    except Exception as e:
      raise HTTPException(
          status_code=502,
          detail=f"Error al borrar la imagen en Cloudinary: {e}",
      )

  era_principal = imagen.es_principal
  session.delete(imagen)
  session.flush()

  # si perdimos la portada, promover la de menor orden entre las que quedan
  if era_principal:
    reemplazo = session.exec(
        select(ImagenAccesorio)
        .where(ImagenAccesorio.accesorio_id == accesorio_id)
        .order_by(ImagenAccesorio.orden, ImagenAccesorio.imagen_accesorio_id) #type: ignore
    ).first()
    if reemplazo:
      reemplazo.es_principal = True
      session.add(reemplazo)

  session.commit()
  return {"mensaje": "Imagen eliminada", "imagen_accesorio_id": imagen_id}


# ─── IMAGEN DE CATEGORIAS (tipos / subtipos) ─────────────────────────────────
# Cada categoria lleva una unica imagen (el tile de la grilla del ecommerce),
# guardada como columnas en la propia tabla. Subir de nuevo reemplaza la anterior.

@router.post("/tipos/{tipo_id}/imagen")
def subir_imagen_tipo(
    tipo_id: int,
    file: UploadFile,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
  """Sube (o reemplaza) la imagen de un tipo de accesorio.

  Se sube a la carpeta `tipos/{tipo_id}`. Si el tipo ya tenia imagen, el asset
  viejo se borra de Cloudinary despues de subir el nuevo con exito.
  """
  tipo = session.get(TipoAccesorio, tipo_id)
  if not tipo:
    raise HTTPException(status_code=404, detail="Tipo no encontrado")

  try:
    resultado = cloudinary.uploader.upload(
        file.file,
        folder=f"tipos/{tipo_id}",
        resource_type="image",
    )
  except Exception as e:
    raise HTTPException(
        status_code=502,
        detail=f"Error al subir '{file.filename}' a Cloudinary: {e}",
    )

  # borrar el asset anterior (best-effort: no romper si falla)
  public_id_anterior = tipo.imagen_public_id
  if public_id_anterior and public_id_anterior != resultado["public_id"]:
    try:
      cloudinary.uploader.destroy(public_id_anterior, resource_type="image")
    except Exception:
      pass

  tipo.imagen_url = resultado["secure_url"]
  tipo.imagen_public_id = resultado["public_id"]
  session.add(tipo)
  session.commit()
  session.refresh(tipo)
  return tipo


@router.delete("/tipos/{tipo_id}/imagen")
def eliminar_imagen_tipo(
    tipo_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
  """Borra la imagen de un tipo en Cloudinary y limpia las columnas."""
  tipo = session.get(TipoAccesorio, tipo_id)
  if not tipo:
    raise HTTPException(status_code=404, detail="Tipo no encontrado")

  if tipo.imagen_public_id:
    try:
      cloudinary.uploader.destroy(tipo.imagen_public_id, resource_type="image")
    except Exception as e:
      raise HTTPException(
          status_code=502,
          detail=f"Error al borrar la imagen en Cloudinary: {e}",
      )

  tipo.imagen_url = None
  tipo.imagen_public_id = None
  session.add(tipo)
  session.commit()
  return {"mensaje": "Imagen eliminada", "tipo_id": tipo_id}


@router.post("/subtipos/{subtipo_id}/imagen")
def subir_imagen_subtipo(
    subtipo_id: int,
    file: UploadFile,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
  """Sube (o reemplaza) la imagen de un subtipo de accesorio.

  Se sube a la carpeta `subtipos/{subtipo_id}`. Si el subtipo ya tenia imagen,
  el asset viejo se borra de Cloudinary despues de subir el nuevo con exito.
  """
  subtipo = session.get(SubtipoAccesorio, subtipo_id)
  if not subtipo:
    raise HTTPException(status_code=404, detail="Subtipo no encontrado")

  try:
    resultado = cloudinary.uploader.upload(
        file.file,
        folder=f"subtipos/{subtipo_id}",
        resource_type="image",
    )
  except Exception as e:
    raise HTTPException(
        status_code=502,
        detail=f"Error al subir '{file.filename}' a Cloudinary: {e}",
    )

  public_id_anterior = subtipo.imagen_public_id
  if public_id_anterior and public_id_anterior != resultado["public_id"]:
    try:
      cloudinary.uploader.destroy(public_id_anterior, resource_type="image")
    except Exception:
      pass

  subtipo.imagen_url = resultado["secure_url"]
  subtipo.imagen_public_id = resultado["public_id"]
  session.add(subtipo)
  session.commit()
  session.refresh(subtipo)
  return subtipo


@router.delete("/subtipos/{subtipo_id}/imagen")
def eliminar_imagen_subtipo(
    subtipo_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
  """Borra la imagen de un subtipo en Cloudinary y limpia las columnas."""
  subtipo = session.get(SubtipoAccesorio, subtipo_id)
  if not subtipo:
    raise HTTPException(status_code=404, detail="Subtipo no encontrado")

  if subtipo.imagen_public_id:
    try:
      cloudinary.uploader.destroy(subtipo.imagen_public_id, resource_type="image")
    except Exception as e:
      raise HTTPException(
          status_code=502,
          detail=f"Error al borrar la imagen en Cloudinary: {e}",
      )

  subtipo.imagen_url = None
  subtipo.imagen_public_id = None
  session.add(subtipo)
  session.commit()
  return {"mensaje": "Imagen eliminada", "subtipo_id": subtipo_id}
