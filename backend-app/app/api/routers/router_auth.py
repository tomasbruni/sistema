import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import encode, decode, InvalidTokenError
from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.db.session import get_session
from app.db.models import Usuario

router = APIRouter(prefix="/auth", tags=["AUTH"])

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "7be29e1278d3a81d1b3803e26fdc397ff47d141db9314fe364ba7d1d76187ad0")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 8

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def verificar_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

def hashear_password(plain: str) -> str:
    return password_hash.hash(plain)

def crear_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    payload.update({"exp": expire})
    return encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ─── ENDPOINT /token ──────────────────────────────────────────────────────────
@router.post("/token")
def login(
    #lee el form desde el body del request
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session),
):
    usuario = session.exec(
        select(Usuario).where(Usuario.nombre == form.username)
    ).first()

    if not usuario or not verificar_password(form.password, usuario.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )

    token = crear_token(
        {"sub": str(usuario.usuario_id), "rol": usuario.rol},
        timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    )

    return {
      "access_token": token,
      "token_type": "bearer",
      "nombre": usuario.nombre,
      "rol": usuario.rol,
      "usuario_id": usuario.usuario_id,
    }