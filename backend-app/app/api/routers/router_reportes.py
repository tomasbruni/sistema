from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from sqlalchemy import func
from typing import Optional
from datetime import date, datetime
from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.db.session import get_session
from app.db.models import PagoVenta, Venta, Local, Usuario

from app.api.deps import get_current_user, require_admin

router = APIRouter(
    prefix="/reportes",
    tags=["REPORTES"],
    dependencies=[Depends(require_admin)],
)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _es_electronico(medio: str) -> bool:
    return medio.strip().upper() != "EFECTIVO"


def _iva_de_pago(importe: int, medio: str) -> int:
    """
    Devuelve el IVA correspondiente a un pago.
    - Efectivo:     IVA = 0.
    - Electrónico:  IVA incluido en el precio → IVA = importe * 21 / 121.

    Las devoluciones se almacenan con importe negativo, por lo que el IVA
    resultante también será negativo y descuenta correctamente del total.
    """
    if not _es_electronico(medio):
        return 0
    return round(importe * 21 / 121)


def _build_query(fecha_desde: Optional[date], fecha_hasta: Optional[date]):
    """Une PagoVenta ↔ Venta ↔ Local ↔ Usuario con filtro de fechas opcional."""
    stmt = (
        select(PagoVenta, Venta, Local, Usuario)
        .join(Venta,   PagoVenta.venta_id == Venta.venta_id)      # type: ignore
        .join(Local,   Venta.local_id     == Local.local_id)      # type: ignore
        .join(Usuario, Venta.usuario_id   == Usuario.usuario_id)  # type: ignore
    )
    if fecha_desde is not None:
        stmt = stmt.where(func.date(Venta.fecha_ingreso) >= fecha_desde)
    if fecha_hasta is not None:
        stmt = stmt.where(func.date(Venta.fecha_ingreso) <= fecha_hasta)
    return stmt.order_by(Venta.fecha_ingreso.asc(), PagoVenta.pago_id.asc())  # type: ignore


# ─── ENDPOINT JSON ────────────────────────────────────────────────────────────

@router.get("/iva")
def reporte_iva_json(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    session: Session = Depends(get_session),
):
    rows = session.exec(_build_query(fecha_desde, fecha_hasta)).all()

    items = []
    total_iva         = 0
    total_electronico = 0
    total_efectivo    = 0

    for pago, venta, local, usuario in rows:
        iva            = _iva_de_pago(pago.importe, pago.medio_de_pago)
        es_devolucion  = venta.tipo.strip().upper() == "DEVOLUCION"
        es_electronico = _es_electronico(pago.medio_de_pago)

        total_iva += iva
        if es_electronico:
            total_electronico += pago.importe
        else:
            total_efectivo += pago.importe

        items.append({
            "pago_id":        pago.pago_id,
            "venta_id":       venta.venta_id,
            "fecha":          venta.fecha_ingreso.isoformat() if venta.fecha_ingreso else None,
            "local":          local.nombre,
            "usuario":        usuario.nombre,
            "tipo_venta":     venta.tipo,
            "medio_de_pago":  pago.medio_de_pago,
            "importe":        pago.importe,
            "iva":            iva,
            "base_imponible": pago.importe - iva if iva else None,
            "es_devolucion":  es_devolucion,
        })

    return {
        "fecha_desde":       fecha_desde,
        "fecha_hasta":       fecha_hasta,
        "total_pagos":       len(items),
        "total_efectivo":    total_efectivo,
        "total_electronico": total_electronico,
        "total_iva":         total_iva,
        "items":             items,
    }


# ─── ENDPOINT EXCEL ───────────────────────────────────────────────────────────

@router.get("/iva/export")
def exportar_reporte_iva(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    session: Session = Depends(get_session),
):
    """
    Exporta el reporte de IVA a Excel.
    Una fila por pago. Devoluciones incluidas (en rojo, IVA = 0).
    Fila de totales al final.
    """
    rows = session.exec(_build_query(fecha_desde, fecha_hasta)).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte IVA"  # type: ignore

    COLOR_HEADER      = "1A1A2E"
    COLOR_DEVOLUCION  = "F8D7DA"
    COLOR_EFECTIVO    = "FFFFFF"
    COLOR_ELECTRONICO = "D4EDDA"
    COLOR_TOTAL       = "FFF3CD"

    header_font  = Font(bold=True, color="FFFFFF", size=10)
    header_fill  = PatternFill(fill_type="solid", fgColor=COLOR_HEADER)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border  = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    center = Alignment(horizontal="center")
    right  = Alignment(horizontal="right")

    # ── Título ────────────────────────────────────────────────────────────────
    rango_str = f"  ({fecha_desde or '...'} → {fecha_hasta or '...'})" if (fecha_desde or fecha_hasta) else ""

    ws.merge_cells("A1:L1")  # type: ignore
    titulo_cell           = ws["A1"] # type: ignore
    titulo_cell.value     = f"Reporte de IVA{rango_str}"
    titulo_cell.font      = Font(bold=True, size=13, color=COLOR_HEADER)
    titulo_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28  # type: ignore

    ws.merge_cells("A2:L2")  # type: ignore
    gen_cell           = ws["A2"] # type: ignore
    gen_cell.value     = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    gen_cell.font      = Font(italic=True, size=9, color="888888")
    gen_cell.alignment = Alignment(horizontal="right")

    # ── Encabezados ───────────────────────────────────────────────────────────
    COLUMNAS = [
        ("Pago ID",        8),
        ("Venta ID",       8),
        ("Fecha",         18),
        ("Local",         18),
        ("Usuario",       14),
        ("Tipo venta",    12),
        ("Medio de pago", 14),
        ("Importe",       14),
        ("Base imponible",15),
        ("IVA 21%",       12),
        ("Computa IVA",   11),
        ("Observación",   22),
    ]

    FILA_HEADER = 4
    for col_idx, (titulo, ancho) in enumerate(COLUMNAS, start=1):
        cell           = ws.cell(row=FILA_HEADER, column=col_idx, value=titulo)  # type: ignore
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align
        cell.border    = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = ancho  # type: ignore

    ws.row_dimensions[FILA_HEADER].height = 32  # type: ignore

    # ── Filas de datos ────────────────────────────────────────────────────────
    total_iva         = 0
    total_electronico = 0
    total_efectivo    = 0
    fila_actual       = FILA_HEADER + 1

    for pago, venta, local, usuario in rows:
        iva            = _iva_de_pago(pago.importe, pago.medio_de_pago)
        es_devolucion  = venta.tipo.strip().upper() == "DEVOLUCION"
        es_electronico = _es_electronico(pago.medio_de_pago)
        base           = pago.importe - iva if iva > 0 else None

        total_iva += iva
        if es_electronico:
            total_electronico += pago.importe
        else:
            total_efectivo += pago.importe

        if es_devolucion:
            obs        = "Devolución — importe negativo"
            fila_color = COLOR_DEVOLUCION
        elif not es_electronico:
            obs        = "Efectivo — exento de IVA"
            fila_color = COLOR_EFECTIVO
        else:
            obs        = ""
            fila_color = COLOR_ELECTRONICO

        fila_fill = PatternFill(fill_type="solid", fgColor=fila_color)
        fecha_str = venta.fecha_ingreso.strftime("%d/%m/%Y %H:%M") if venta.fecha_ingreso else ""

        valores = [
            pago.pago_id,
            venta.venta_id,
            fecha_str,
            local.nombre,
            usuario.nombre,
            venta.tipo,
            pago.medio_de_pago,
            pago.importe,
            base if base is not None else "—",
            iva  if iva  > 0         else "—",
            "Sí" if (es_electronico and not es_devolucion) else "No",
            obs,
        ]

        for col_idx, valor in enumerate(valores, start=1):
            cell           = ws.cell(row=fila_actual, column=col_idx, value=valor)  # type: ignore
            cell.fill      = fila_fill
            cell.border    = thin_border
            if col_idx in (1, 2, 11):
                cell.alignment = center
            elif col_idx in (8, 9, 10):
                cell.alignment = right
            else:
                cell.alignment = Alignment(vertical="center")

        fila_actual += 1

    # ── Fila de totales ───────────────────────────────────────────────────────
    fila_actual += 1
    total_fill = PatternFill(fill_type="solid", fgColor=COLOR_TOTAL)
    total_font = Font(bold=True, size=10)

    def _celda_total(col, valor, alin=None):
        c           = ws.cell(row=fila_actual, column=col, value=valor)  # type: ignore
        c.fill      = total_fill
        c.font      = total_font
        c.border    = thin_border
        c.alignment = alin or center

    _celda_total(1, "TOTALES")
    ws.merge_cells(start_row=fila_actual, start_column=1, end_row=fila_actual, end_column=7)  # type: ignore
    _celda_total(8,  total_efectivo + total_electronico, right)
    _celda_total(9,  total_electronico - total_iva, right)
    _celda_total(10, total_iva, right)
    _celda_total(11, "")
    _celda_total(12, f"Efectivo: ${total_efectivo:,}  |  Electrónico: ${total_electronico:,}")

    # ── Leyenda ───────────────────────────────────────────────────────────────
    fila_leyenda = fila_actual + 2
    ws.cell(row=fila_leyenda, column=1, value="Referencias:").font = Font(bold=True, size=9)  # type: ignore
    for i, (color, texto) in enumerate([
        (COLOR_ELECTRONICO, "Pago electrónico con IVA"),
        (COLOR_EFECTIVO,    "Pago en efectivo (sin IVA)"),
        (COLOR_DEVOLUCION,  "Devolución (importe negativo)"),
    ]):
        ws.cell(row=fila_leyenda + i + 1, column=1).fill   = PatternFill(fill_type="solid", fgColor=color)  # type: ignore
        ws.cell(row=fila_leyenda + i + 1, column=1).border = thin_border  # type: ignore
        ws.cell(row=fila_leyenda + i + 1, column=2, value=texto).font = Font(size=9)  # type: ignore

    # ── Stream ────────────────────────────────────────────────────────────────
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    nombre = "reporte_iva"
    if fecha_desde or fecha_hasta:
        nombre += f"_{fecha_desde or ''}_{fecha_hasta or ''}"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nombre}.xlsx"},
    )