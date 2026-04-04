import io
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, SQLModel, select
from sqlalchemy.orm import aliased

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

LOGO_PATH = str(Path(__file__).resolve().parent.parent.parent.parent / "static" / "images" / "logo-pdf.png")

from app.db.models import Accesorio, Local, MovimientoStock, Transferencia, TipoMovimiento, Usuario
from app.db.session import get_session
from app.api.deps import get_current_user, UsuarioActual


router = APIRouter(prefix="/transferencias", tags=["Transferencias"])


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class ItemTransferenciaResponse(SQLModel):
    sku: str
    nombre: str
    cantidad: int


class TransferenciaDetalleResponse(SQLModel):
    transferencia_id: int
    fecha: Optional[datetime]
    local_origen: Optional[str]
    local_destino: Optional[str]
    nombre_usuario: Optional[str]
    observaciones: Optional[str]
    items: list[ItemTransferenciaResponse]


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _get_items(transferencia_id: int, session: Session) -> list[ItemTransferenciaResponse]:
    """Devuelve los productos de una transferencia usando los movimientos de SALIDA (origen)."""
    rows = session.exec(
        select(MovimientoStock, Accesorio)
        .join(Accesorio, MovimientoStock.accesorio_id == Accesorio.accesorio_id)  # type: ignore
        .where(MovimientoStock.transferencia_id == transferencia_id)
        .where(MovimientoStock.tipo_movimiento == TipoMovimiento.SALIDA)
    ).all()
    return [
        ItemTransferenciaResponse(
            sku=acc.sku,
            nombre=acc.nombre,
            cantidad=abs(mov.cantidad),
        )
        for mov, acc in rows
    ]


# ─── LISTADO ──────────────────────────────────────────────────────────────────

@router.get("/")
def listar_transferencias(
    skip: int = 0,
    limit: int = 20,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    local_origen_id: Optional[int] = None,
    local_destino_id: Optional[int] = None,
    usuario_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    if usuario_id is not None and current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver transferencias de otros usuarios.",
        )

    # No-admin sin filtro de usuario: solo ve las suyas
    filtro_usuario = usuario_id if usuario_id is not None else (
        None if current_user.rol == "admin" else current_user.usuario_id
    )

    LocalOrigen  = aliased(Local)
    LocalDestino = aliased(Local)

    stmt = (
        select(Transferencia, LocalOrigen, LocalDestino, Usuario)
        .join(LocalOrigen,  Transferencia.local_origen_id  == LocalOrigen.local_id)   # type: ignore
        .join(LocalDestino, Transferencia.local_destino_id == LocalDestino.local_id)  # type: ignore
        .outerjoin(Usuario, Transferencia.usuario_id == Usuario.usuario_id)            # type: ignore
        .order_by(Transferencia.fecha.desc())                                          # type: ignore
        .offset(skip)
        .limit(limit)
    )

    if fecha_desde:
        stmt = stmt.where(Transferencia.fecha >= fecha_desde)   # type: ignore
    if fecha_hasta:
        stmt = stmt.where(Transferencia.fecha <= fecha_hasta)   # type: ignore
    if local_origen_id:
        stmt = stmt.where(Transferencia.local_origen_id == local_origen_id)  # type: ignore
    if local_destino_id:
        stmt = stmt.where(Transferencia.local_destino_id == local_destino_id)  # type: ignore
    if filtro_usuario:
        stmt = stmt.where(Transferencia.usuario_id == filtro_usuario)  # type: ignore

    rows = session.exec(stmt).all()

    return [
        {
            "transferencia_id": t.transferencia_id,
            "fecha":            t.fecha,
            "local_origen":     lo.nombre,
            "local_destino":    ld.nombre,
            "nombre_usuario":   u.nombre if u else None,
            "observaciones":    t.observaciones,
        }
        for t, lo, ld, u in rows
    ]


# ─── DETALLE ──────────────────────────────────────────────────────────────────

@router.get("/{transferencia_id}", response_model=TransferenciaDetalleResponse)
def get_detalle_transferencia(
    transferencia_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    t = session.get(Transferencia, transferencia_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")

    if current_user.rol != "admin" and t.usuario_id != current_user.usuario_id:
        raise HTTPException(status_code=403, detail="No tenés permiso para ver esta transferencia")

    lo = session.get(Local,   t.local_origen_id)
    ld = session.get(Local,   t.local_destino_id)
    u  = session.get(Usuario, t.usuario_id) if t.usuario_id else None

    return TransferenciaDetalleResponse(
        transferencia_id=t.transferencia_id,  # type: ignore
        fecha=t.fecha,
        local_origen=lo.nombre  if lo else None,
        local_destino=ld.nombre if ld else None,
        nombre_usuario=u.nombre if u  else None,
        observaciones=t.observaciones,
        items=_get_items(transferencia_id, session),
    )


# ─── PDF ──────────────────────────────────────────────────────────────────────

@router.get("/{transferencia_id}/pdf")
def transferencia_pdf(
    transferencia_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    t = session.get(Transferencia, transferencia_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")

    if current_user.rol != "admin" and t.usuario_id != current_user.usuario_id:
        raise HTTPException(status_code=403, detail="No tenés permiso para ver esta transferencia")

    lo = session.get(Local,   t.local_origen_id)
    ld = session.get(Local,   t.local_destino_id)
    u  = session.get(Usuario, t.usuario_id) if t.usuario_id else None
    items = _get_items(transferencia_id, session)

    fecha_str = t.fecha.strftime("%d/%m/%Y %H:%M") if t.fecha else "-"

    # ── Construcción del PDF ───────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    W = A4[0] - 30*mm

    styles = getSampleStyleSheet()
    normal = ParagraphStyle("n",  parent=styles["Normal"], fontSize=9,  leading=11)
    bold   = ParagraphStyle("b",  parent=normal, fontName="Helvetica-Bold")
    small  = ParagraphStyle("sm", parent=normal, fontSize=8)
    title  = ParagraphStyle("t",  parent=styles["Normal"], fontSize=13,
                             fontName="Helvetica-Bold", spaceAfter=6)
    hcell  = ParagraphStyle("hc", parent=bold,   fontSize=8.5)
    cell   = ParagraphStyle("c",  parent=normal,  fontSize=8.5, leading=10)

    story = []

    # ── Encabezado ─────────────────────────────────────────────────────────────
    story.append(Paragraph(f"REMITO DE TRANSFERENCIA  #{transferencia_id}", title))

    meta = Table(
        [
            [Paragraph("<b>Fecha:</b>",   bold), Paragraph(fecha_str,               normal),
             Paragraph("<b>Usuario:</b>", bold), Paragraph(u.nombre if u else "-",  normal)],
            [Paragraph("<b>Origen:</b>",  bold), Paragraph(lo.nombre if lo else "-", normal),
             Paragraph("<b>Destino:</b>", bold), Paragraph(ld.nombre if ld else "-", normal)],
        ],
        colWidths=[W*0.14, W*0.36, W*0.14, W*0.36],
    )
    meta.setStyle(TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.black),
        ("LINEBELOW",     (0,0),(-1,0),  0.5, colors.black),
        ("LINEBEFORE",    (2,0),(2,-1),  0.5, colors.black),
    ]))
    story.append(meta)
    story.append(Spacer(1, 10*mm))

    # ── Tabla de productos ─────────────────────────────────────────────────────
    header = [Paragraph(t, hcell) for t in ["SKU", "Nombre", "Cantidad"]]
    data   = [header]
    total_unidades = 0
    for item in items:
        data.append([
            Paragraph(item.sku,         cell),
            Paragraph(item.nombre,      cell),
            Paragraph(str(item.cantidad), cell),
        ])
        total_unidades += item.cantidad

    tbl = Table(data, colWidths=[W*0.22, W*0.62, W*0.16], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("GRID",          (0,0),(-1,-1), 0.25, colors.black),
        ("LINEBELOW",     (0,0),(-1,0),  0.75, colors.black),
        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("ALIGN",         (2,0),(2,-1),  "CENTER"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4*mm))

    # ── Total ──────────────────────────────────────────────────────────────────
    tot = Table(
        [[Paragraph(f"Total unidades: <b>{total_unidades}</b>", small)]],
        colWidths=[W],
    )
    tot.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1), "RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
    ]))
    story.append(tot)

    if t.observaciones:
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph(f"<b>Observaciones:</b> {t.observaciones}", small))

    # ── Firmas ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 14*mm))

    firmas = Table(
        [
            [Paragraph("<b>Firma y aclaración del emisor:</b>",   bold),
             Paragraph("<b>Firma y aclaración del receptor:</b>", bold)],
            [Paragraph("_" * 38, normal),
             Paragraph("_" * 38, normal)],
            [Paragraph(lo.nombre if lo else "", small),
             Paragraph(ld.nombre if ld else "", small)],
        ],
        colWidths=[W * 0.5, W * 0.5],
    )
    firmas.setStyle(TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("ALIGN",         (0,1),(-1,2),  "CENTER"),
        ("LINEBEFORE",    (1,0),(1,-1),  0.5, colors.black),
    ]))
    story.append(firmas)

    doc.build(story)

    filename = f"transferencia_{transferencia_id}_{fecha_str.replace('/', '-').replace(' ', '_').replace(':', '')}.pdf"
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )