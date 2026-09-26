from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exc, func, or_
from sqlmodel import Session, SQLModel, select

from app.db.session import get_session
from app.db.models import ProveedorFiscal
from app.api.deps import require_admin, UsuarioActual


router = APIRouter(prefix="/proveedores-fiscales", tags=["Proveedores fiscales (IVA compras)"])

_PESOS_CUIT = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


# ── Schemas ──────────────────────────────────────────────────────────────────

class ProveedorFiscalCreate(SQLModel):
    razon_social: str
    cuit: str
    # El digito verificador se valida, pero hay CUITs mal tipeados en comprobantes
    # reales: con forzar=True se acepta igual (el formato de 11 digitos sigue siendo obligatorio).
    forzar: bool = False


class ProveedorFiscalUpdate(SQLModel):
    razon_social: Optional[str] = None
    cuit: Optional[str] = None
    activo: Optional[bool] = None
    forzar: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalizar_cuit(cuit: str, forzar: bool = False) -> str:
    """Devuelve el CUIT como XX-XXXXXXXX-X. 422 si no tiene 11 digitos, o si el
    digito verificador no cierra y no se pidio forzar."""
    digitos = "".join(ch for ch in cuit if ch.isdigit())
    if len(digitos) != 11:
        raise HTTPException(422, "El CUIT debe tener 11 dígitos")

    if not forzar:
        suma = sum(int(d) * p for d, p in zip(digitos[:10], _PESOS_CUIT))
        verificador = 11 - suma % 11
        verificador = {11: 0, 10: 9}.get(verificador, verificador)
        if verificador != int(digitos[10]):
            raise HTTPException(422, "CUIT_DIGITO_INVALIDO: el dígito verificador no coincide")

    return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}"


def _guardar(session: Session, proveedor: ProveedorFiscal) -> ProveedorFiscal:
    session.add(proveedor)
    try:
        session.commit()
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(400, "Ya existe un proveedor con ese CUIT")
    session.refresh(proveedor)
    return proveedor


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ProveedorFiscal])
def listar_proveedores_fiscales(
    q: Optional[str] = Query(default=None, description="Busca por razón social o CUIT"),
    activo: Optional[bool] = Query(default=True),
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    query = select(ProveedorFiscal)
    if activo is not None:
        query = query.where(ProveedorFiscal.activo == activo)
    if q and q.strip():
        texto = q.strip()
        condiciones = [ProveedorFiscal.razon_social.ilike(f"%{texto}%")]  # type: ignore
        solo_digitos = "".join(ch for ch in texto if ch.isdigit())
        if solo_digitos:
            # El CUIT se guarda con guiones: se compara contra la version sin guiones.
            condiciones.append(func.replace(ProveedorFiscal.cuit, "-", "").contains(solo_digitos))
        query = query.where(or_(*condiciones))
    query = query.order_by(ProveedorFiscal.razon_social).limit(limit)  # type: ignore
    return session.exec(query).all()


@router.post("/", response_model=ProveedorFiscal, status_code=status.HTTP_201_CREATED)
def crear_proveedor_fiscal(
    payload: ProveedorFiscalCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    razon_social = payload.razon_social.strip()
    if not razon_social:
        raise HTTPException(422, "'razon_social' es obligatoria")
    proveedor = ProveedorFiscal(
        razon_social=razon_social.upper(),
        cuit=normalizar_cuit(payload.cuit, payload.forzar),
    )
    return _guardar(session, proveedor)


@router.patch("/{proveedor_fiscal_id}", response_model=ProveedorFiscal)
def actualizar_proveedor_fiscal(
    proveedor_fiscal_id: int,
    payload: ProveedorFiscalUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    proveedor = session.get(ProveedorFiscal, proveedor_fiscal_id)
    if not proveedor:
        raise HTTPException(404, "Proveedor no encontrado")

    if payload.razon_social is not None:
        if not payload.razon_social.strip():
            raise HTTPException(422, "'razon_social' es obligatoria")
        proveedor.razon_social = payload.razon_social.strip().upper()
    if payload.cuit is not None:
        proveedor.cuit = normalizar_cuit(payload.cuit, payload.forzar)
    if payload.activo is not None:
        proveedor.activo = payload.activo
    return _guardar(session, proveedor)
