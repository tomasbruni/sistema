from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from sqlalchemy import exc
from typing import List, Optional
from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from app.db.session import get_session
from app.db.models import Chip, Local, DetalleVentaChip
from app.api.modelscreate import ChipCreate
from app.api.modelsupdate import ChipUpdate
from app.api.deps import get_current_user, require_admin, UsuarioActual


router = APIRouter(
    prefix="/chips",
    tags=["Chips"],
)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _aplicar_filtros(query, local_id, estado, compania, buscar):
    """Aplica los filtros comunes a una query de Chip."""
    if local_id:
        query = query.where(Chip.local_id == local_id)
    if estado:
        query = query.where(Chip.estado == estado)
    if compania:
        query = query.where(Chip.compania.ilike(f"%{compania}%"))  # type: ignore
    if buscar:
        query = query.where(Chip.numero_serie.ilike(f"%{buscar}%"))  # type: ignore
    return query


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.get("/export")
def exportar_chips(
    session: Session = Depends(get_session),
    local_id: Optional[int] = None,
    estado: Optional[str] = None,
    compania: Optional[str] = None,
    buscar: Optional[str] = None,
    limit: int = 10000,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Exportar chips a Excel respetando los filtros activos."""

    # Traer chips y locales en un solo join
    statement = (
        select(Chip, Local)
        .join(Local, Chip.local_id == Local.local_id)  # type: ignore
    )
    statement = _aplicar_filtros(statement, local_id, estado, compania, buscar)
    rows = session.exec(statement.limit(limit)).all()

    # ── Construir el libro ────────────────────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Chips" #type: ignore

    # Estilos de cabecera
    header_font    = Font(bold=True, color="FFFFFF")
    header_fill    = PatternFill("solid", fgColor="1A1A2E")
    header_align   = Alignment(horizontal="center", vertical="center")

    headers = ["ID", "N° de serie", "Compañía", "Precio", "Local", "Estado"]
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h) #type: ignore
        cell.font    = header_font
        cell.fill    = header_fill
        cell.alignment = header_align

    # Filas de datos
    for row_idx, (chip, local) in enumerate(rows, start=2):
        ws.cell(row=row_idx, column=1, value=chip.chip_id) #type: ignore
        ws.cell(row=row_idx, column=2, value=chip.numero_serie) #type: ignore
        ws.cell(row=row_idx, column=3, value=chip.compania) #type: ignore
        ws.cell(row=row_idx, column=4, value=chip.precio) #type: ignore
        ws.cell(row=row_idx, column=5, value=local.nombre) #type: ignore
        ws.cell(row=row_idx, column=6, value=chip.estado) #type: ignore

    # Ancho de columnas
    anchos = [8, 22, 16, 12, 20, 14]
    for col_idx, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = ancho #type: ignore

    # ── Serializar y devolver ─────────────────────────────────────────────────
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=chips.xlsx"},
    )


@router.get("/", response_model=List[Chip])
def listar_chips(
    session: Session = Depends(get_session),
    local_id: Optional[int] = None,
    estado: Optional[str] = None,
    compania: Optional[str] = None,
    buscar: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Listar chips con filtros opcionales. buscar filtra por número de serie."""
    query = select(Chip)
    query = _aplicar_filtros(query, local_id, estado, compania, buscar)
    return session.exec(query.offset(skip).limit(limit)).all()


@router.get("/{chip_id}")
def obtener_chip(
    chip_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Obtener un chip específico por ID."""
    chip = session.get(Chip, chip_id)
    if not chip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chip no encontrado")
    return chip

# deprecado
@router.get("/numero-serie/{numero_serie}")
def buscar_por_numero_serie(
    numero_serie: str,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Buscar chip por número de serie exacto."""
    chip = session.exec(
        select(Chip).where(Chip.numero_serie == numero_serie)
    ).first()
    if not chip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chip no encontrado")
    return chip


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_chip(
    chip_in: ChipCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Crear un nuevo chip."""
    chip = Chip(**chip_in.model_dump())
    session.add(chip)
    session.commit()
    session.refresh(chip)
    return chip


@router.put("/{chip_id}")
def actualizar_chip(
    chip_id: int,
    chip_in: ChipUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Actualizar un chip."""
    chip = session.get(Chip, chip_id)
    if not chip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chip no encontrado")
    for field, value in chip_in.model_dump(exclude_unset=True).items():
        setattr(chip, field, value)
    session.add(chip)
    session.commit()
    session.refresh(chip)
    return chip


@router.delete("/{chip_id}")
def eliminar_chip(
    chip_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Elimina un chip físicamente.
    Si el chip tiene ventas asociadas (detalles_ventas_chips),
    la operación es rechazada — en ese caso actualizá el estado a 'VENDIDO' en su lugar.
    """
    chip = session.get(Chip, chip_id)
    if not chip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chip no encontrado")

    try:
        session.delete(chip)
        session.commit()
        return {"ok": True, "mensaje": "Chip eliminado exitosamente"}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se puede eliminar el chip porque tiene ventas asociadas. "
                "Actualizá el estado a 'VENDIDO' en su lugar."
            )
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )