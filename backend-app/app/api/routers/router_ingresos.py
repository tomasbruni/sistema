from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from sqlmodel import Session, SQLModel, select, col, Field
from sqlalchemy import exc
from sqlalchemy.orm import aliased
from datetime import datetime, date
import io

from app.db.session import get_session, SessionDep
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from fastapi.responses import StreamingResponse
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.api.deps import get_current_user, require_admin, UsuarioActual


router = APIRouter(
    prefix="/ingresos",
    tags=["Ingresos"],
    dependencies=[Depends(require_admin)],
)


class MovimientoDetalleResponse(SQLModel):
    nombre_accesorio: str
    cantidad: int


class IngresoLoteDetalleResponse(SQLModel):
    ingreso_lote_id: int
    fecha: Optional[datetime]
    nombre_receptor: Optional[str]
    local: Optional[str]
    movimientos: list[MovimientoDetalleResponse]


@router.get("/")
def listar_ingresos(
    skip: int = 0,
    limit: int = 20,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    local_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    Receptor = aliased(Usuario) # type: ignore

    stmt = (
        select(IngresoLote, Receptor, Local)
        .outerjoin(Receptor, IngresoLote.receptor_id == Receptor.usuario_id) # type: ignore
        .join(Local, IngresoLote.local_id == Local.local_id) # type: ignore
        .order_by(IngresoLote.fecha.desc())# type: ignore
        .offset(skip)
        .limit(limit)
    )

    if fecha_desde:
        stmt = stmt.where(IngresoLote.fecha >= fecha_desde)# type: ignore
    if fecha_hasta:
        stmt = stmt.where(IngresoLote.fecha <= fecha_hasta)# type: ignore
    
    if local_id:
        stmt = stmt.where(IngresoLote.local_id == local_id)# type: ignore

    rows = session.exec(stmt).all()

    resultado = []
    for ingreso, receptor, local in rows:
        resultado.append({
            "ingreso_lote_id": ingreso.ingreso_lote_id,
            "fecha":           ingreso.fecha,
            "observaciones":   ingreso.observaciones,
            "nombre_receptor": receptor.nombre if receptor else None,
            "local": local.nombre
        })

    return resultado

@router.get("/{ingreso_lote_id}", response_model=IngresoLoteDetalleResponse)
def get_movimientos_por_ingreso_lote(
    ingreso_lote_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    # 1. Buscar el ingreso_lote
    ingreso = session.get(IngresoLote, ingreso_lote_id)
    if not ingreso:
        raise HTTPException(status_code=404, detail="Ingreso de lote no encontrado")

    # 2. Nombre del receptor (puede ser null)
    receptor_nombre = None
    if ingreso.receptor_id:
        receptor = session.get(Usuario, ingreso.receptor_id)
        receptor_nombre = receptor.nombre if receptor else None

    local = None
    if ingreso.local_id:
        local = session.get(Local, ingreso.local_id)
        local_nombre = local.nombre if local else None

    # 3. Movimientos asociados al lote
    movimientos = session.exec(
        select(MovimientoStock)
        .where(MovimientoStock.ingreso_lote_id == ingreso_lote_id)
    ).all()

    if not movimientos:
        raise HTTPException(status_code=404, detail="No hay movimientos para este ingreso")

    # 4. Construir detalle por movimiento
    detalle_movimientos = []
    for mov in movimientos:
        accesorio = session.get(Accesorio, mov.accesorio_id)
        detalle_movimientos.append(
            MovimientoDetalleResponse(
                nombre_accesorio=accesorio.nombre if accesorio else f"ID {mov.accesorio_id}",
                cantidad=mov.cantidad,
            )
        )

    return IngresoLoteDetalleResponse(
        ingreso_lote_id=ingreso.ingreso_lote_id, # type: ignore
        fecha=ingreso.fecha,
        nombre_receptor=receptor_nombre,
        movimientos=detalle_movimientos,
        local = local_nombre # type: ignore
    )


@router.get("/{ingreso_lote_id}/pdf")
def ingreso_pdf(
    ingreso_lote_id: int,
    session: Session = Depends(get_session),
):
    # ── Datos del ingreso ──────────────────────────────────────────────────────
    ingreso = session.get(IngresoLote, ingreso_lote_id)
    if not ingreso:
        raise HTTPException(status_code=404, detail="Ingreso de lote no encontrado")

    local = session.get(Local, ingreso.local_id) if ingreso.local_id else None
    receptor = session.get(Usuario, ingreso.receptor_id) if ingreso.receptor_id else None

    movimientos = session.exec(
        select(MovimientoStock)
        .where(MovimientoStock.ingreso_lote_id == ingreso_lote_id)
    ).all()

    filas = []
    total_unidades = 0
    for mov in movimientos:
        acc = session.get(Accesorio, mov.accesorio_id)
        filas.append({
            "sku":      acc.sku    if acc else "-",
            "nombre":   acc.nombre if acc else f"ID {mov.accesorio_id}",
            "cantidad": mov.cantidad,
        })
        total_unidades += mov.cantidad

    # ── PDF ────────────────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    W = A4[0] - 30*mm

    styles  = getSampleStyleSheet()
    normal  = ParagraphStyle("n",  parent=styles["Normal"], fontSize=9,  leading=11)
    bold    = ParagraphStyle("b",  parent=normal, fontName="Helvetica-Bold")
    small   = ParagraphStyle("sm", parent=normal, fontSize=8)
    title   = ParagraphStyle("t",  parent=styles["Normal"], fontSize=13,
                              fontName="Helvetica-Bold", spaceAfter=6)
    hcell   = ParagraphStyle("hc", parent=bold, fontSize=8.5)
    cell    = ParagraphStyle("c",  parent=normal, fontSize=8.5, leading=10)

    fecha_str = (
        ingreso.fecha.strftime("%d/%m/%Y %H:%M")
        if ingreso.fecha else "-"
    )
    local_str    = local.nombre    if local    else "-"
    receptor_str = receptor.nombre if receptor else "-"

    story = []

    # ── Encabezado ─────────────────────────────────────────────────────────────
    story.append(Paragraph(f"REMITO DE INGRESO  #{ingreso_lote_id}", title))

    meta = Table(
        [
            [Paragraph("<b>Fecha:</b>",    bold), Paragraph(fecha_str,    normal),
             Paragraph("<b>Local:</b>",    bold), Paragraph(local_str,    normal)],
            [Paragraph("<b>Receptor:</b>", bold), Paragraph(receptor_str, normal),
             Paragraph("",                bold), Paragraph("",            normal)],
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
    for f in filas:
        data.append([
            Paragraph(f["sku"],        cell),
            Paragraph(f["nombre"],     cell),
            Paragraph(str(f["cantidad"]), cell),
        ])

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

    # ── Total unidades ─────────────────────────────────────────────────────────
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
    story.append(Spacer(1, 14*mm))

    # ── Firma ──────────────────────────────────────────────────────────────────
    firma = Table(
        [
            [Paragraph("Firma y aclaración:", bold),
             Paragraph("_" * 40, normal)],
            [Paragraph("", normal),
             Paragraph("", small)],
        ],
        colWidths=[W*0.12, W*0.88],
    )
    firma.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 1),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("ALIGN",         (1,1),(1,1),   "CENTER"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
    ]))
    story.append(firma)

    if ingreso.observaciones:
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph(f"<b>Observaciones:</b> {ingreso.observaciones}", small))

    doc.build(story)
    pdf_bytes = buffer.getvalue()

    filename = f"ingreso_{ingreso_lote_id}_{fecha_str.replace('/', '-').replace(' ', '_').replace(':', '')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )