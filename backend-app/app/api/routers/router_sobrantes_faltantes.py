from datetime import date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.db.session import get_session
from app.db.models import SobranteFaltante, Usuario
from app.api.modelscreate import SobranteFaltanteUpsert
from app.api.deps import get_current_user, UsuarioActual

router = APIRouter(prefix="/sobrantes-faltantes", tags=["Sobrantes y Faltantes"])

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


@router.put("/", status_code=status.HTTP_200_OK)
def upsert_sobrante_faltante(
    data: SobranteFaltanteUpsert,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    """
    Crea o actualiza el registro de sobrante/faltante para un local y fecha.
    - No-admin: la fecha la pone la DB (CURRENT_DATE); se ignora cualquier fecha del body.
    - Admin: puede enviar una fecha específica.
    Unique constraint: (fecha, local_id).
    """
    # ── Usuario ───────────────────────────────────────────────────────────────
    if current_user.rol == "admin" and data.usuario_id is not None:
        usuario = session.get(Usuario, data.usuario_id)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        usuario_id = data.usuario_id
    else:
        usuario_id = current_user.usuario_id

    # ── Upsert ────────────────────────────────────────────────────────────────
    if current_user.rol == "admin" and data.fecha is not None:
        # Admin con fecha explícita: lookup por esa fecha
        registro = session.exec(
            select(SobranteFaltante)
            .where(SobranteFaltante.fecha == data.fecha)
            .where(SobranteFaltante.local_id == data.local_id)
        ).first()

        if registro:
            registro.sobrante = data.sobrante
            registro.faltante = data.faltante
            registro.usuario_id = usuario_id
        else:
            registro = SobranteFaltante(
                local_id=data.local_id,
                usuario_id=usuario_id,
                fecha=data.fecha,
                sobrante=data.sobrante,
                faltante=data.faltante,
            )
            session.add(registro)
    else:
        # No-admin (o admin sin fecha): lookup por CURRENT_DATE de la DB
        registro = session.exec(
            select(SobranteFaltante)
            .where(SobranteFaltante.fecha == func.current_date())
            .where(SobranteFaltante.local_id == data.local_id)
        ).first()

        if registro:
            registro.sobrante = data.sobrante
            registro.faltante = data.faltante
            registro.usuario_id = usuario_id
        else:
            # No se setea fecha: la DB la llena con server_default (CURRENT_DATE)
            registro = SobranteFaltante(
                local_id=data.local_id,
                usuario_id=usuario_id,
                sobrante=data.sobrante,
                faltante=data.faltante,
            )
            session.add(registro)

    session.commit()
    session.refresh(registro)

    return {
        "id": registro.id,
        "local_id": registro.local_id,
        "usuario_id": registro.usuario_id,
        "fecha": registro.fecha.isoformat(),
        "sobrante": registro.sobrante,
        "faltante": registro.faltante,
    }


@router.get("/")
def get_sobrante_faltante(
    local_id: int = Query(...),
    fecha: date = Query(..., description="Fecha (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    """Obtiene el registro de sobrante/faltante para un local y fecha."""
    registro = session.exec(
        select(SobranteFaltante)
        .where(SobranteFaltante.fecha == fecha)
        .where(SobranteFaltante.local_id == local_id)
    ).first()

    if not registro:
        return {"sobrante": 0, "faltante": 0, "fecha": fecha.isoformat(), "local_id": local_id}

    return {
        "id": registro.id,
        "local_id": registro.local_id,
        "usuario_id": registro.usuario_id,
        "fecha": registro.fecha.isoformat(),
        "sobrante": registro.sobrante,
        "faltante": registro.faltante,
    }
