#cosas q utilizo en todos los routers, por ejemplo la autenticacion
from fastapi import Depends, HTTPException, status
from jwt import decode, InvalidTokenError
from sqlmodel import Session, SQLModel
from typing import Annotated

from app.db.session import get_session
from app.db.models import Usuario
from app.api.routers.router_auth import SECRET_KEY, ALGORITHM, oauth2_scheme
# ojo con devolver el password hasheado

class UsuarioActual(SQLModel):
    usuario_id: int
    rol: str

# ─── DEPENDENCIAS ─────────────────────────────────────────────────────────────
def get_current_user(
    # lee el token desde el header y lo pasa como string
    token: Annotated[str, Depends(oauth2_scheme)],
) -> UsuarioActual:
    credenciales_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        #si no fue emitido por mi lanza InvalidTokenError
        payload    = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        #rol e id viven en el token
        usuario_id = payload.get("sub")
        rol = payload.get("rol")
        if usuario_id is None:
            raise credenciales_exc
    except InvalidTokenError:
        raise credenciales_exc

    # usuario = session.get(Usuario, int(usuario_id))
    # if not usuario:
    #     raise credenciales_exc
    
    return UsuarioActual(
        usuario_id=int(usuario_id),
        rol=rol, #type: ignore
    )


def require_admin(
    current_user: UsuarioActual = Depends(get_current_user),
) -> UsuarioActual:
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return current_user