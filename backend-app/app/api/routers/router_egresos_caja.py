from sqlmodel import SQLModel

from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo
 
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
 
from app.db.session import get_session  
from app.db.models import EgresoCaja, Usuario     
from app.api.deps import get_current_user, require_admin, UsuarioActual


router = APIRouter(prefix="/egresos", tags=["Egresos de Caja"])
 
TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")
 
 
# ── Schemas ──────────────────────────────────────────────────────────────────
 
class EgresoCajaCreate(SQLModel):
    monto: int
    descripcion: str
    medio_pago: Optional[str] = "EFECTIVO"
    local_id: int
    usuario_id: Optional[int] = None
 
 
class EgresoCajaUpdate(SQLModel):
    monto: Optional[int] = None
    descripcion: Optional[str] = None
    medio_pago: Optional[str] = "EFECTIVO"
    local_id: Optional[int] = None
    usuario_id: Optional[int] = None
 
 
class EgresoCajaRead(SQLModel):
    egreso_caja_id: int
    fecha: Optional[datetime]
    monto: int
    descripcion: str
    medio_pago: str
    local_id: int
    usuario_id: int
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def _start_of_day(d: date) -> datetime:
    """Medianoche al inicio del día en zona horaria argentina."""
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=TZ_AR)
 
 
def _end_of_day(d: date) -> datetime:
    """Último microsegundo del día en zona horaria argentina."""
    return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=TZ_AR)
 
 
# ── Endpoints ─────────────────────────────────────────────────────────────────
 
@router.post("/", response_model=EgresoCajaRead, status_code=status.HTTP_201_CREATED)
def crear_egreso(
    payload: EgresoCajaCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    # Comprobacion de usuario
    if current_user.rol == 'admin' and payload.usuario_id is not None:
        usuario = session.get(Usuario, payload.usuario_id)
        if not usuario:
            raise HTTPException(404, "Usuario no existe")
        usuarioAsignado = usuario.usuario_id        
    else:
        usuarioAsignado = current_user.usuario_id
    
    egreso = EgresoCaja(
      monto = payload.monto,
      descripcion = payload.descripcion,
      medio_pago  = payload.medio_pago, # type: ignore
      local_id  = payload.local_id,
      usuario_id  = usuarioAsignado # type: ignore
    )
    
    session.add(egreso)
    session.commit()
    session.refresh(egreso)
    return egreso
 
 
@router.get("/", response_model=list[EgresoCajaRead])
def listar_egresos(
    # Filtro por día exacto (tiene precedencia sobre fecha_desde/hasta)
    fecha: Optional[date] = Query(default=None, description="Día exacto (YYYY-MM-DD)"),
    # Filtro por rango
    fecha_desde: Optional[date] = Query(default=None, description="Inicio del rango (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(default=None, description="Fin del rango (YYYY-MM-DD)"),
    # Filtros adicionales
    local_id: Optional[int] = Query(default=None),
    usuario_id: Optional[int] = Query(default=None),
    # Paginación básica
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
    usuario: UsuarioActual = Depends(get_current_user),
):
    query = select(EgresoCaja)
 
    # — Filtro de fecha ——————————————————————————————————————————————————————
    if fecha:
        # Día exacto: convierte a rango con hora en zona AR para que el
        # TIMESTAMPTZ almacenado en Postgres se compare correctamente.
        query = query.where(
            EgresoCaja.fecha >= _start_of_day(fecha), #type: ignore
            EgresoCaja.fecha <= _end_of_day(fecha), #type: ignore
        )
    else:
        if fecha_desde:
            query = query.where(EgresoCaja.fecha >= _start_of_day(fecha_desde)) #type: ignore
        if fecha_hasta:
            query = query.where(EgresoCaja.fecha <= _end_of_day(fecha_hasta)) #type: ignore
 
    # — Filtros simples ———————————————————————————————————————————————————————
    if local_id is not None:
        query = query.where(EgresoCaja.local_id == local_id)
    if usuario_id is not None:
        query = query.where(EgresoCaja.usuario_id == usuario_id)
 
    # — Orden y paginación ————————————————————————————————————————————————————
    query = query.order_by(EgresoCaja.fecha.desc()).offset(offset).limit(limit) #type: ignore
 
    return session.exec(query).all()
 
 
@router.get("/{egreso_caja_id}", response_model=EgresoCajaRead)
def obtener_egreso(
    egreso_caja_id: int,
    session: Session = Depends(get_session),
    usuario: UsuarioActual = Depends(get_current_user),
):
    egreso = session.get(EgresoCaja, egreso_caja_id)
    if not egreso:
        raise HTTPException(status_code=404, detail="Egreso no encontrado")
    return egreso
 
 
@router.patch("/{egreso_caja_id}", response_model=EgresoCajaRead)
def actualizar_egreso(
    egreso_caja_id: int,
    payload: EgresoCajaUpdate,
    session: Session = Depends(get_session),
    usuario: UsuarioActual = Depends(get_current_user),
):
    egreso = session.get(EgresoCaja, egreso_caja_id)
    if not egreso:
        raise HTTPException(status_code=404, detail="Egreso no encontrado")
 
    data = payload.model_dump(exclude_unset=True)
    for campo, valor in data.items():
        setattr(egreso, campo, valor)
 
    session.add(egreso)
    session.commit()
    session.refresh(egreso)
    return egreso
 
 
@router.delete("/{egreso_caja_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_egreso(
    egreso_caja_id: int,
    session: Session = Depends(get_session),
):
    egreso = session.get(EgresoCaja, egreso_caja_id)
    if not egreso:
        raise HTTPException(status_code=404, detail="Egreso no encontrado")
    session.delete(egreso)
    session.commit()
 