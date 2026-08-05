from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from typing import Optional
from datetime import date, datetime
from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.db.session import get_session
from app.db.models import (
    PagoVenta, Venta, Local, Usuario,
    MovimientoReparacion, Reparacion, ConfigComision, SobranteFaltante,
)
from app.api.deps import get_current_user, require_admin, UsuarioActual
from app.api.funciones.ventas_funciones import get_detalles_by_venta
from app.api.funciones.fechas import start_of_day, end_of_day, TZ_AR

router = APIRouter(
    prefix="/reportes",
    tags=["REPORTES"],
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
        stmt = stmt.where(Venta.fecha_ingreso >= start_of_day(fecha_desde))  # type: ignore
    if fecha_hasta is not None:
        stmt = stmt.where(Venta.fecha_ingreso <= end_of_day(fecha_hasta))  # type: ignore
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


# ─────────────────────────────────────────────────────────────────────────────
# REPORTE DE COMISIONES
# ─────────────────────────────────────────────────────────────────────────────

def _calcular_comision_config(config: ConfigComision | None, monto: int) -> int:
    if config is None:
        return 0
    if config.tipo_calculo == "PORCENTAJE":
        return round(monto * config.valor / 100)
    return config.valor  # FIJO: monto fijo por unidad/reparación


def _fmt_fecha_ar(dt: datetime | None) -> str:
    if not dt:
        return "-"
    return dt.astimezone(TZ_AR).strftime("%d/%m/%Y %H:%M")


def _build_comisiones_excel(
    local_nombre: str,
    usuario_nombre: str,
    fecha_label: str,
    detalles_acc: list,   # dicts con campos de venta + "fecha"
    detalles_cel: list,
    detalles_chip: list,
    entregas_rep: list,   # list of (MovimientoReparacion, Reparacion)
    config_rep: ConfigComision | None,
    config_acc: ConfigComision | None,
    sf_por_dia: dict,     # {date: (sobrante, faltante)} solo donde alguno > 0
) -> bytes:
    from collections import defaultdict

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Comisiones"  # type: ignore

    # ── Estilos ────────────────────────────────────────────────────────────────
    thin      = Side(style="thin")
    border    = Border(left=thin, right=thin, top=thin, bottom=thin)
    center_al = Alignment(horizontal="center", vertical="center")
    right_al  = Alignment(horizontal="right",  vertical="center")
    left_al   = Alignment(horizontal="left",   vertical="center")

    hdr_font = Font(bold=True, size=10, underline="single")
    bold_tot = Font(bold=True, size=10)

    def _cell(row, col, value=None, font=None, alignment=None, border_=None):
        c = ws.cell(row=row, column=col, value=value)  # type: ignore
        if font:      c.font      = font
        if alignment: c.alignment = alignment
        if border_:   c.border    = border_
        return c

    def _hdr_row(row, labels):
        for col, lbl in enumerate(labels, 1):
            _cell(row, col, lbl, font=hdr_font, alignment=center_al, border_=border)
        ws.row_dimensions[row].height = 28  # type: ignore

    def _dat_row(row, values, font=None):
        for col, val in enumerate(values, 1):
            al = right_al if isinstance(val, (int, float)) else left_al
            _cell(row, col, val, font=font, alignment=al, border_=border)

    # ── Cálculos globales ──────────────────────────────────────────────────────
    com_rep_por_entrega = [
        _calcular_comision_config(config_rep, rep.total)
        for _, rep in entregas_rep
    ] # capaz conviene sumar primero y calcular el porcentaje despues

    total_monto_acc  = sum(d["precio_unitario"] * d["cantidad"] for d in detalles_acc)
    total_monto_cel  = sum(d["precio_unitario"]                  for d in detalles_cel)
    total_monto_chip = sum(d["precio_unitario"]                  for d in detalles_chip)
    total_monto_rep  = sum(rep.total for _, rep in entregas_rep)

    total_com_acc  = sum(d["comision_importe"] for d in detalles_acc)
    total_com_cel  = sum(d["comision_importe"] for d in detalles_cel)
    total_com_chip = sum(d["comision_importe"] for d in detalles_chip)
    total_com_rep  = sum(com_rep_por_entrega)

    total_sob = sum(v[0] for v in sf_por_dia.values())
    total_fal = sum(v[1] for v in sf_por_dia.values())
    total_com_sob  = _calcular_comision_config(config_acc, total_sob)
    total_com_fal  = _calcular_comision_config(config_acc, total_fal)
    total_com      = total_com_acc + total_com_cel + total_com_chip + total_com_rep + total_com_sob - total_com_fal

    # ── Agrupar por día ────────────────────────────────────────────────────────
    def _date_of(dt) -> date:
        if dt is None:
            return date.min
        if hasattr(dt, "astimezone"):
            return dt.astimezone(TZ_AR).date()
        if hasattr(dt, "date"):
            return dt.date()
        return dt

    daily_acc:      dict[date, int] = defaultdict(int)
    daily_cel:      dict[date, int] = defaultdict(int)
    daily_cel_cant: dict[date, int] = defaultdict(int)
    daily_chip:     dict[date, int] = defaultdict(int)
    daily_chip_cant:dict[date, int] = defaultdict(int)

    #aca agrupa por fecha en un diccionario
    for d in detalles_acc:
        daily_acc[_date_of(d["fecha"])] += d["precio_unitario"] * d["cantidad"] # correcto si hay devoluciones se quita
    for d in detalles_cel:
        daily_cel[_date_of(d["fecha"])]      += d["precio_unitario"]
        daily_cel_cant[_date_of(d["fecha"])] += 1
    for d in detalles_chip:
        daily_chip[_date_of(d["fecha"])]      += d["precio_unitario"]
        daily_chip_cant[_date_of(d["fecha"])] += 1

    # Las reparaciones tienen su propia tabla, no entran en la facturación por día
    all_dates = sorted(
        daily_acc.keys() | daily_cel.keys() | daily_chip.keys() | sf_por_dia.keys()
    ) # en las fechas que no hubo actividad no pone nada

    # ══ ENCABEZADO ════════════════════════════════════════════════════════════
    ws.merge_cells("A1:J1")  # type: ignore
    _cell(1, 1, "REPORTE DE COMISIONES",
          font=Font(bold=True, size=14),
          alignment=Alignment(horizontal="center", vertical="center"))
    ws.row_dimensions[1].height = 30  # type: ignore

    ws.merge_cells("A2:J2")  # type: ignore
    _cell(2, 1,
          f"Local: {local_nombre}  |  Vendedor/a: {usuario_nombre}  |  Período: {fecha_label}",
          font=Font(italic=True, size=10),
          alignment=Alignment(horizontal="center"))

    ws.merge_cells("A3:J3")  # type: ignore
    _cell(3, 1, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
          font=Font(italic=True, size=9),
          alignment=Alignment(horizontal="right"))

    # ══ TABLA 1: FACTURACIÓN POR DÍA ════════════════════════════════════════
    FILA_T1_LBL = 5
    ws.merge_cells(f"A{FILA_T1_LBL}:J{FILA_T1_LBL}")  # type: ignore
    _cell(FILA_T1_LBL, 1, "Facturación por día",
          font=Font(bold=True, size=11), alignment=left_al)

    FILA_T1_HDR = FILA_T1_LBL + 1
    _hdr_row(FILA_T1_HDR, [
        "Fecha", "Accesorios", "Celulares", "Cant. Cel.",
        "Chips", "Cant. Chips", "Total día", "Sobrante", "Faltante",
    ])

    fila = FILA_T1_HDR + 1
    for d in all_dates:
        acc      = daily_acc.get(d, 0)
        cel      = daily_cel.get(d, 0)
        cel_cant = daily_cel_cant.get(d, 0)
        chip     = daily_chip.get(d, 0)
        chip_cant= daily_chip_cant.get(d, 0)
        sob, fal = sf_por_dia.get(d, (0, 0))
        _dat_row(fila, [
            d.strftime("%d/%m/%Y"),
            acc       or "",
            cel       or "",
            cel_cant  or "",
            chip      or "",
            chip_cant or "",
            acc + cel + chip or "",
            sob or "",
            fal or "",
        ])
        fila += 1

    # Totales tabla 1
    _dat_row(fila, [
        "TOTAL",
        total_monto_acc  or "",
        total_monto_cel  or "",
        len(detalles_cel)  or "",
        total_monto_chip or "",
        len(detalles_chip) or "",
        total_monto_acc + total_monto_cel + total_monto_chip,
        total_sob or "",
        total_fal or "",
    ], font=bold_tot)
    ws.cell(row=fila, column=1).alignment = center_al  # type: ignore
    fila += 1

    # ══ TABLA 2: REPARACIONES ENTREGADAS ══════════════════════════════════════
    FILA_T2_LBL = fila + 2
    ws.merge_cells(f"A{FILA_T2_LBL}:F{FILA_T2_LBL}")  # type: ignore
    _cell(FILA_T2_LBL, 1, "Reparaciones entregadas",
          font=Font(bold=True, size=11), alignment=left_al)

    FILA_T2_HDR = FILA_T2_LBL + 1
    _hdr_row(FILA_T2_HDR, [
        "Fecha creación", "Fecha entrega", "Cliente", "Equipo", "Total", "Comisión",
    ])

    fila = FILA_T2_HDR + 1
    for (mov, rep), com in zip(entregas_rep, com_rep_por_entrega):
        _dat_row(fila, [
            _fmt_fecha_ar(rep.fecha_ingreso),
            _fmt_fecha_ar(mov.fecha),
            rep.nombre_cliente,
            rep.celular,
            rep.total,
            com,
        ])
        fila += 1

    if not entregas_rep:
        _dat_row(fila, ["Sin reparaciones entregadas en el período", "", "", "", "", ""])
        fila += 1

    _dat_row(fila, ["TOTAL REPARACIONES", "", "", "", total_monto_rep, total_com_rep],
             font=bold_tot)
    ws.cell(row=fila, column=1).alignment = center_al  # type: ignore
    fila += 1

    # ══ TABLA 3: RESUMEN POR CATEGORÍA + COMISIONES ═══════════════════════════
    FILA_T3_LBL = fila + 2
    ws.merge_cells(f"A{FILA_T3_LBL}:D{FILA_T3_LBL}")  # type: ignore
    _cell(FILA_T3_LBL, 1, "Resumen por categoría",
          font=Font(bold=True, size=11), alignment=left_al)

    FILA_T3_HDR = FILA_T3_LBL + 1
    _hdr_row(FILA_T3_HDR, ["Categoría", "Cant.", "Total facturado", "Comisión"])

    resumen = [
        ("Accesorios",              len(detalles_acc),  total_monto_acc,  total_com_acc),
        ("Celulares",               len(detalles_cel),  total_monto_cel,  total_com_cel),
        ("Chips",                   len(detalles_chip), total_monto_chip, total_com_chip),
        ("Reparaciones entregadas", len(entregas_rep),  total_monto_rep,  total_com_rep),
        ("Sobrantes",               len([v for v in sf_por_dia.values() if v[0] > 0]), total_sob, total_com_sob),
        ("Faltantes",               len([v for v in sf_por_dia.values() if v[1] > 0]), total_fal, -total_com_fal),
    ]
    fila = FILA_T3_HDR + 1
    for tipo, cant, monto, com in resumen:
        _dat_row(fila, [tipo, cant, monto, com])
        fila += 1

    grand_total = total_monto_acc + total_monto_cel + total_monto_chip + total_monto_rep
    _dat_row(fila, ["TOTAL", "", grand_total, total_com], font=bold_tot)
    ws.cell(row=fila, column=1).alignment = center_al  # type: ignore

    # ── Anchos de columna ──────────────────────────────────────────────────────
    for col, width in enumerate([23, 18, 22, 20, 14, 13, 13, 12, 12, 10], start=1):
        ws.column_dimensions[get_column_letter(col)].width = width  # type: ignore

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/comisiones/excel")
def reporte_comisiones_excel(
    local_id: int,
    usuario_id: int,
    desde: date,
    hasta: date,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    dt_desde = datetime(desde.year, desde.month, desde.day, 0, 0, 0, tzinfo=TZ_AR)
    dt_hasta = datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59, tzinfo=TZ_AR)

    local    = session.get(Local,   local_id)
    usuario  = session.get(Usuario, usuario_id)
    if not local:
        from fastapi import HTTPException
        raise HTTPException(404, "Local no encontrado")
    if not usuario:
        from fastapi import HTTPException
        raise HTTPException(404, "Usuario no encontrado")

    # ── Ventas del período ────────────────────────────────────────────────────
    ventas = session.exec(
        select(Venta)
        .where(Venta.local_id      == local_id)
        .where(Venta.usuario_id    == usuario_id)
        .where(Venta.fecha_ingreso >= dt_desde)  # type: ignore
        .where(Venta.fecha_ingreso <= dt_hasta)  # type: ignore
    ).all()
    venta_ids     = [v.venta_id for v in ventas]
    fecha_by_venta = {v.venta_id: v.fecha_ingreso for v in ventas}

    raw = get_detalles_by_venta(session, venta_ids) # type: ignore

    detalles_acc  = []
    detalles_cel  = []
    detalles_chip = []
    for vid, dets in raw.items():
        for d in dets:
            entry = {**d, "venta_id": vid, "fecha": fecha_by_venta.get(vid)} # agrega a cada detalle su fecha
            if d["tipo_producto"] == "ACCESORIO":
                detalles_acc.append(entry)
            elif d["tipo_producto"] == "CELULAR":
                detalles_cel.append(entry)
            elif d["tipo_producto"] == "CHIP":
                detalles_chip.append(entry)

    # ── Reparaciones entregadas en el período (comisión al creador) ───────────
    entregas_rep = session.exec(
        select(MovimientoReparacion, Reparacion)
        .join(Reparacion, MovimientoReparacion.reparacion_id == Reparacion.reparacion_id)  # type: ignore
        .where(Reparacion.local_id    == local_id)
        .where(Reparacion.usuario_id  == usuario_id)
        .where(MovimientoReparacion.tipo_movimiento == "CAMBIO_ESTADO")
        .where(MovimientoReparacion.estado_nuevo    == "ENTREGADO")
        .where(MovimientoReparacion.fecha >= dt_desde)  # type: ignore
        .where(MovimientoReparacion.fecha <= dt_hasta)  # type: ignore
        .order_by(MovimientoReparacion.fecha)  # type: ignore
    ).all()

    # ── Config comisión reparaciones y accesorios ─────────────────────────────
    config_rep = session.exec(
        select(ConfigComision).where(ConfigComision.tipo_producto == "REPARACION")
    ).first()
    config_acc = session.exec(
        select(ConfigComision).where(ConfigComision.tipo_producto == "ACCESORIO")
    ).first()

    # ── Sobrantes / faltantes del período para este usuario y local ───────────
    sf_records = session.exec(
        select(SobranteFaltante)
        .where(SobranteFaltante.local_id   == local_id)
        .where(SobranteFaltante.usuario_id == usuario_id)
        .where(SobranteFaltante.fecha      >= desde)  # type: ignore
        .where(SobranteFaltante.fecha      <= hasta)  # type: ignore
        .where(
            (SobranteFaltante.sobrante > 0) | (SobranteFaltante.faltante > 0)  # type: ignore
        )
    ).all()
    sf_por_dia = {r.fecha: (r.sobrante, r.faltante) for r in sf_records}

    fecha_label = f"{desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}"

    xlsx_bytes = _build_comisiones_excel(
        local_nombre=local.nombre,
        usuario_nombre=usuario.nombre,
        fecha_label=fecha_label,
        detalles_acc=detalles_acc,
        detalles_cel=detalles_cel,
        detalles_chip=detalles_chip,
        entregas_rep=list(entregas_rep),
        config_rep=config_rep,
        config_acc=config_acc,
        sf_por_dia=sf_por_dia,
    )

    filename = f"comisiones_{usuario.nombre.replace(' ', '_')}_{desde}_{hasta}.xlsx"
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )