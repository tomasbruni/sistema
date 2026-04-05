from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import SQLModel, Session, select
from typing import List, Optional
from app.db.session import get_session
from app.db.models import Usuario, MovimientoStock, IngresoLote, Transferencia, Venta, Reparacion
from app.api.modelscreate import UsuarioCreate
from app.api.modelsupdate import UsuarioUpdate
from app.api.deps import require_admin, get_current_user, UsuarioActual
from app.api.routers.router_auth import hashear_password

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
)

class UsuarioResponse(SQLModel):
    usuario_id: int
    nombre: str
    rol: str
    activo: bool

@router.get("/", response_model=list[UsuarioResponse], dependencies=[Depends(get_current_user)])
def listar_usuarios(
    activo: Optional[bool] = True,
    session: Session = Depends(get_session),
):
    query = select(Usuario)
    if activo is not None:
        query = query.where(Usuario.activo == activo)
    return session.exec(query).all()


@router.post("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def crear_usuario(
    usuario: UsuarioCreate,
    session: Session = Depends(get_session)
):
    nuevo = Usuario(
        nombre=usuario.nombre,
        password=hashear_password(usuario.password),
        rol=usuario.rol,
    )
    session.add(nuevo)
    session.commit()
    return {"mensaje": "Usuario creado exitosamente"}


@router.put("/{usuario_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioUpdate,
    session: Session = Depends(get_session)
):
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    update_data = datos.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(usuario, key, value)

    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return {"mensaje": f"Usuario '{usuario.nombre}' actualizado exitosamente"}


@router.delete("/{usuario_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])
def desactivar_usuario(
    usuario_id: int,
    session: Session = Depends(get_session)
):
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if not usuario.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario ya se encuentra inactivo")
    
    usuario.activo = False
    session.add(usuario)
    session.commit()
    return {"mensaje": f"Usuario '{usuario.nombre}' desactivado exitosamente"}