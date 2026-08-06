from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.db.session import get_session
from app.db.models import (
    PagoVenta, Venta, Local, Usuario,
    MovimientoReparacion, Reparacion, ConfigComision, SobranteFaltante,
    Gasto, EgresoCaja,
)
from app.api.deps import get_current_user, require_admin, UsuarioActual
from app.api.funciones.ventas_funciones import get_detalles_by_venta, get_pagos_by_venta
from app.api.funciones.fechas import start_of_day, end_of_day, TZ_AR
from app.api.funciones.reportes_ventas import iva_incluido

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


# ─────────────────────────────────────────────────────────────────────────────
# ESTILOS Y WRITERS COMPARTIDOS
#
# Los usan tanto el reporte de comisiones (una combinación local+vendedora por
# archivo) como el de facturación (todas las combinaciones en una sola hoja).
# Convención: todo writer devuelve la primera fila LIBRE debajo de lo que
# escribió, así los bloques se encadenan sin calcular offsets a mano.
# ─────────────────────────────────────────────────────────────────────────────

_THIN     = Side(style="thin")
_BORDER   = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTER   = Alignment(horizontal="center", vertical="center")
_RIGHT    = Alignment(horizontal="right",  vertical="center")
_LEFT     = Alignment(horizontal="left",   vertical="center")
_HDR_WRAP = Alignment(horizontal="center", vertical="center", wrap_text=True)

_HDR_FONT       = Font(bold=True, size=10, underline="single")
_BOLD_FONT      = Font(bold=True, size=10)
_TITULO_FONT    = Font(bold=True, size=14)
_SECCION_FONT   = Font(bold=True, size=12)
_SUBTITULO_FONT = Font(bold=True, size=11)
_ITALIC_FONT    = Font(italic=True, size=10)
_NOTA_FONT      = Font(italic=True, size=9, color="888888")

_NUM_FMT = "#,##0"

_ANCHOS_COMISIONES  = [23, 18, 22, 20, 14, 13, 13, 12, 12, 10]
_ANCHOS_FACTURACION = [22, 24, 22, 20, 14, 14, 15, 15, 15, 15, 15, 15]

_FILL_SECCION = PatternFill(fill_type="solid", fgColor="E8EAF6")


def _a_pesos(valor) -> int:
    """Decimal | int | None → int pesos. Único puente Decimal→int del reporte."""
    if valor is None:
        return 0
    if isinstance(valor, int):
        return valor
    return int(Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _cell(ws, row, col, value=None, font=None, alignment=None, border_=None, num_fmt=None):
    c = ws.cell(row=row, column=col, value=value)
    if font:      c.font          = font
    if alignment: c.alignment     = alignment
    if border_:   c.border        = border_
    if num_fmt and isinstance(value, (int, float)):
        c.number_format = num_fmt
    return c


def _hdr_row(ws, row, labels, col_ini=1, wrap=False, alto=28) -> None:
    for i, lbl in enumerate(labels):
        _cell(ws, row, col_ini + i, lbl, font=_HDR_FONT,
              alignment=_HDR_WRAP if wrap else _CENTER, border_=_BORDER)
    ws.row_dimensions[row].height = alto


def _dat_row(ws, row, values, font=None, col_ini=1, num_fmt=None) -> None:
    for i, val in enumerate(values):
        al = _RIGHT if isinstance(val, (int, float)) else _LEFT
        _cell(ws, row, col_ini + i, val, font=font, alignment=al,
              border_=_BORDER, num_fmt=num_fmt)


def _label_row(ws, fila, texto, ancho_cols, font=_SUBTITULO_FONT, fill=None) -> int:
    """Etiqueta de sección mergeada de A a `ancho_cols`. Devuelve la fila siguiente."""
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ancho_cols)
    c = _cell(ws, fila, 1, texto, font=font, alignment=_LEFT)
    if fill:
        for col in range(1, ancho_cols + 1):
            ws.cell(row=fila, column=col).fill = fill
    return fila + 1


def _kv_row(ws, fila, etiqueta, valor, cols_label=3, font=_BOLD_FONT,
            num_fmt=_NUM_FMT, obs=None) -> int:
    """Etiqueta mergeada A:cols_label + valor en la columna siguiente (+ observación)."""
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=cols_label)
    _cell(ws, fila, 1, etiqueta, font=font, alignment=_LEFT, border_=_BORDER)
    for col in range(2, cols_label + 1):
        ws.cell(row=fila, column=col).border = _BORDER
    _cell(ws, fila, cols_label + 1, valor, font=font, alignment=_RIGHT,
          border_=_BORDER, num_fmt=num_fmt)
    if obs:
        _cell(ws, fila, cols_label + 2, obs, font=_NOTA_FONT, alignment=_LEFT)
    return fila + 1


def _aplicar_anchos(ws, anchos: list[int]) -> None:
    for col, width in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(col)].width = width


def _date_of(dt) -> date | None:
    """Fecha AR de un datetime/date. None si no hay fecha (ventas sin fecha_ingreso)."""
    if dt is None:
        return None
    if hasattr(dt, "astimezone"):
        return dt.astimezone(TZ_AR).date()
    if hasattr(dt, "date"):
        return dt.date()
    return dt


def _escribir_encabezado_reporte(ws, fila, titulo, subtitulo, ancho_cols) -> int:
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ancho_cols)
    _cell(ws, fila, 1, titulo, font=_TITULO_FONT, alignment=_CENTER)
    ws.row_dimensions[fila].height = 30

    ws.merge_cells(start_row=fila + 1, start_column=1, end_row=fila + 1, end_column=ancho_cols)
    _cell(ws, fila + 1, 1, subtitulo, font=Font(italic=True, size=10),
          alignment=Alignment(horizontal="center"))

    ws.merge_cells(start_row=fila + 2, start_column=1, end_row=fila + 2, end_column=ancho_cols)
    _cell(ws, fila + 2, 1, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
          font=Font(italic=True, size=9), alignment=Alignment(horizontal="right"))

    return fila + 3


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO DE COMISIONES (compartido por ambos reportes)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ResumenComisiones:
    """Montos y comisiones de una combinación local+vendedora en un período."""
    com_rep_por_entrega: list[int] = field(default_factory=list)

    monto_acc: int = 0
    monto_cel: int = 0
    monto_chip: int = 0
    monto_rep: int = 0

    com_acc: int = 0
    com_cel: int = 0
    com_chip: int = 0
    com_rep: int = 0

    cant_acc: int = 0
    cant_cel: int = 0
    cant_chip: int = 0
    cant_rep: int = 0

    total_sob: int = 0
    total_fal: int = 0
    com_sob: int = 0
    com_fal: int = 0
    dias_sob: int = 0
    dias_fal: int = 0

    @property
    def total_comision(self) -> int:
        return (self.com_acc + self.com_cel + self.com_chip + self.com_rep
                + self.com_sob - self.com_fal)

    @property
    def total_facturado(self) -> int:
        return self.monto_acc + self.monto_cel + self.monto_chip + self.monto_rep


def _calcular_resumen_comisiones(
    detalles_acc: list[dict],
    detalles_cel: list[dict],
    detalles_chip: list[dict],
    entregas_rep: list,            # list of (MovimientoReparacion, Reparacion)
    sf_por_dia: dict,              # {date: (sobrante, faltante)}
    config_rep: ConfigComision | None,
    config_acc: ConfigComision | None,
) -> ResumenComisiones:
    com_rep_por_entrega = [
        _calcular_comision_config(config_rep, rep.total or 0)
        for _, rep in entregas_rep
    ]

    total_sob = sum(v[0] for v in sf_por_dia.values())
    total_fal = sum(v[1] for v in sf_por_dia.values())

    # El MONTO va firmado: una devolución resta, igual que su comisión
    # (`subtotal` ya viene con el signo desde get_detalles_by_venta).
    # La CANTIDAD son las unidades vendidas: una devolución cuenta 0. Se cuentan
    # unidades, no líneas de detalle: un accesorio puede venir con cantidad > 1
    # en una sola línea.
    def _cant(detalles) -> int:
        return sum(d["cantidad"] for d in detalles if not d["es_devolucion"])

    return ResumenComisiones(
        com_rep_por_entrega=com_rep_por_entrega,
        monto_acc=sum(d["subtotal"] for d in detalles_acc),
        monto_cel=sum(d["subtotal"] for d in detalles_cel),
        monto_chip=sum(d["subtotal"] for d in detalles_chip),
        monto_rep=sum(rep.total or 0 for _, rep in entregas_rep),
        com_acc=sum(d["comision_importe"] for d in detalles_acc),
        com_cel=sum(d["comision_importe"] for d in detalles_cel),
        com_chip=sum(d["comision_importe"] for d in detalles_chip),
        com_rep=sum(com_rep_por_entrega),
        cant_acc=_cant(detalles_acc),
        cant_cel=_cant(detalles_cel),
        cant_chip=_cant(detalles_chip),
        cant_rep=len(entregas_rep),
        total_sob=total_sob,
        total_fal=total_fal,
        com_sob=_calcular_comision_config(config_acc, total_sob),
        com_fal=_calcular_comision_config(config_acc, total_fal),
        dias_sob=len([v for v in sf_por_dia.values() if v[0] > 0]),
        dias_fal=len([v for v in sf_por_dia.values() if v[1] > 0]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# TABLAS COMPARTIDAS
# ─────────────────────────────────────────────────────────────────────────────

def _escribir_tabla_reparaciones(ws, fila, entregas_rep, r: ResumenComisiones,
                                 ancho_cols=6, num_fmt=None) -> int:
    fila = _label_row(ws, fila, "Reparaciones entregadas", ancho_cols)
    _hdr_row(ws, fila, ["Fecha creación", "Fecha entrega", "Cliente", "Equipo",
                        "Total", "Comisión"], wrap=bool(num_fmt))
    fila += 1

    for (mov, rep), com in zip(entregas_rep, r.com_rep_por_entrega):
        _dat_row(ws, fila, [
            _fmt_fecha_ar(rep.fecha_ingreso),
            _fmt_fecha_ar(mov.fecha),
            rep.nombre_cliente,
            rep.celular,
            rep.total or 0,
            com,
        ], num_fmt=num_fmt)
        fila += 1

    if not entregas_rep:
        _dat_row(ws, fila, ["Sin reparaciones entregadas en el período", "", "", "", "", ""])
        fila += 1

    _dat_row(ws, fila, ["TOTAL REPARACIONES", "", "", "", r.monto_rep, r.com_rep],
             font=_BOLD_FONT, num_fmt=num_fmt)
    ws.cell(row=fila, column=1).alignment = _CENTER
    return fila + 1


def _escribir_tabla_resumen_categorias(ws, fila, r: ResumenComisiones,
                                       ancho_cols=4, num_fmt=None) -> int:
    fila = _label_row(ws, fila, "Resumen por categoría", ancho_cols)
    _hdr_row(ws, fila, ["Categoría", "Cant.", "Total facturado", "Comisión"],
             wrap=bool(num_fmt))
    fila += 1

    for tipo, cant, monto, com in [
        ("Accesorios",              r.cant_acc,  r.monto_acc,  r.com_acc),
        ("Celulares",               r.cant_cel,  r.monto_cel,  r.com_cel),
        ("Chips",                   r.cant_chip, r.monto_chip, r.com_chip),
        ("Reparaciones entregadas", r.cant_rep,  r.monto_rep,  r.com_rep),
        ("Sobrantes",               r.dias_sob,  r.total_sob,  r.com_sob),
        ("Faltantes",               r.dias_fal,  r.total_fal,  -r.com_fal),
    ]:
        _dat_row(ws, fila, [tipo, cant, monto, com], num_fmt=num_fmt)
        fila += 1

    _dat_row(ws, fila, ["TOTAL", "", r.total_facturado, r.total_comision],
             font=_BOLD_FONT, num_fmt=num_fmt)
    ws.cell(row=fila, column=1).alignment = _CENTER
    return fila + 1


def _agrupar_detalles_por_dia(detalles: list[dict]) -> tuple[dict, dict]:
    """(monto por día, cantidad por día) de una lista de detalles con clave 'fecha'.

    El monto va firmado: las devoluciones restan (`subtotal` ya trae el signo).
    La cantidad es "unidades vendidas": una devolución cuenta 0, no resta. Se cuentan
    unidades y no líneas de detalle, porque un accesorio puede venir con cantidad > 1
    en una sola línea (en celulares y chips `cantidad` siempre es 1)."""
    monto: dict = defaultdict(int)
    cant:  dict = defaultdict(int)
    for d in detalles:
        dia = _date_of(d["fecha"])
        monto[dia] += d["subtotal"]
        if not d["es_devolucion"]:
            cant[dia] += d["cantidad"]
    return monto, cant


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
    """Genera el Excel de comisiones de UNA combinación local+vendedora."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Comisiones"  # type: ignore

    r = _calcular_resumen_comisiones(
        detalles_acc, detalles_cel, detalles_chip,
        entregas_rep, sf_por_dia, config_rep, config_acc,
    )

    fila = _escribir_encabezado_reporte(
        ws, 1, "REPORTE DE COMISIONES",
        f"Local: {local_nombre}  |  Vendedor/a: {usuario_nombre}  |  Período: {fecha_label}",
        ancho_cols=10,
    )
    fila = _escribir_tabla_facturacion_comisiones(
        ws, fila + 1, detalles_acc, detalles_cel, detalles_chip, sf_por_dia, r)
    fila = _escribir_tabla_reparaciones(ws, fila + 2, entregas_rep, r)
    fila = _escribir_tabla_resumen_categorias(ws, fila + 2, r)

    _aplicar_anchos(ws, _ANCHOS_COMISIONES)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _escribir_tabla_facturacion_comisiones(
    ws, fila, detalles_acc, detalles_cel, detalles_chip, sf_por_dia,
    r: ResumenComisiones,
) -> int:
    """Tabla 1 del reporte de comisiones: facturación diaria por tipo de producto.

    Es específica de ese reporte: el de facturación usa otras columnas y toma el
    neto de los pagos en vez de los detalles."""
    daily_acc, _              = _agrupar_detalles_por_dia(detalles_acc)
    daily_cel, daily_cel_cant = _agrupar_detalles_por_dia(detalles_cel)
    daily_chip, daily_chip_cant = _agrupar_detalles_por_dia(detalles_chip)

    # Las reparaciones tienen su propia tabla, no entran en la facturación por día.
    # En las fechas sin actividad no se escribe nada.
    all_dates = sorted(
        daily_acc.keys() | daily_cel.keys() | daily_chip.keys() | sf_por_dia.keys(),
        key=lambda d: (d is None, d or date.min),
    )

    fila = _label_row(ws, fila, "Facturación por día", 10)
    _hdr_row(ws, fila, [
        "Fecha", "Accesorios", "Celulares", "Cant. Cel.",
        "Chips", "Cant. Chips", "Total día", "Sobrante", "Faltante",
    ])
    fila += 1

    for d in all_dates:
        acc       = daily_acc.get(d, 0)
        cel       = daily_cel.get(d, 0)
        cel_cant  = daily_cel_cant.get(d, 0)
        chip      = daily_chip.get(d, 0)
        chip_cant = daily_chip_cant.get(d, 0)
        sob, fal  = sf_por_dia.get(d, (0, 0))
        _dat_row(ws, fila, [
            d.strftime("%d/%m/%Y") if d else "Sin fecha",
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

    _dat_row(ws, fila, [
        "TOTAL",
        r.monto_acc  or "",
        r.monto_cel  or "",
        r.cant_cel   or "",
        r.monto_chip or "",
        r.cant_chip  or "",
        r.monto_acc + r.monto_cel + r.monto_chip,
        r.total_sob or "",
        r.total_fal or "",
    ], font=_BOLD_FONT)
    ws.cell(row=fila, column=1).alignment = _CENTER
    return fila + 1


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
        raise HTTPException(404, "Local no encontrado")
    if not usuario:
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

# ═════════════════════════════════════════════════════════════════════════════
# REPORTE DE FACTURACIÓN DEL LOCAL
#
# Un único Excel con todo el negocio de un período: facturación por día de cada
# combinación local+vendedora, comisiones, resumen general, IVA, gastos e
# impuestos, y el balance final.
#
# Convención monetaria: TODO en int pesos. Los `Gasto` guardan Decimal, así que
# se convierten con `_a_pesos` en la capa de carga y nunca después.
# ═════════════════════════════════════════════════════════════════════════════

ALICUOTA_IVA        = 21     # %  — IVA incluido en el precio (21/121)
ALICUOTA_IIBB       = 3      # %  — Ingresos Brutos sobre facturación en blanco
ALICUOTA_GANANCIAS  = 35     # %  — Impuesto a las Ganancias sobre la utilidad en blanco


@dataclass
class DiaFacturacion:
    """Un día de una combinación local+vendedora.

    `neto` sale de los PAGOS (no de los detalles): es la fuente de verdad, y las
    devoluciones (importe negativo) ya restan solas. `electronico` se DERIVA de
    `neto - efectivo`, lo que garantiza por construcción el invariante
    `total_dia == total_efectivo + total_electronico`."""
    fecha: date | None
    accesorios: int = 0      # informativo, de los detalles de venta
    chips: int = 0           # informativo, de los detalles de venta
    neto: int = 0            # Σ PagoVenta.importe del día
    efectivo: int = 0        # Σ pagos con medio EFECTIVO
    sobrante: int = 0
    faltante: int = 0

    @property
    def electronico(self) -> int:
        return self.neto - self.efectivo

    @property
    def total_dia(self) -> int:
        return self.neto + self.sobrante - self.faltante

    @property
    def total_efectivo(self) -> int:
        return self.efectivo + self.sobrante - self.faltante

    @property
    def total_electronico(self) -> int:
        return self.electronico


@dataclass
class BloqueFacturacion:
    """Todo lo que se imprime para una combinación local+vendedora."""
    local_id: int
    local_nombre: str
    usuario_id: int
    usuario_nombre: str
    dias: list[DiaFacturacion] = field(default_factory=list)
    entregas_rep: list = field(default_factory=list)
    resumen: ResumenComisiones = field(default_factory=ResumenComisiones)

    @property
    def total_efectivo(self) -> int:
        return sum(d.total_efectivo for d in self.dias)

    @property
    def total_electronico(self) -> int:
        return sum(d.total_electronico for d in self.dias)

    @property
    def total_general(self) -> int:
        return sum(d.total_dia for d in self.dias)

    @property
    def total_comision(self) -> int:
        return self.resumen.total_comision

    @property
    def margen_reparaciones(self) -> int:
        """Total cobrado menos lo pagado al reparador, de las entregadas en el período."""
        return sum((rep.total or 0) - (rep.pago_reparador or 0)
                   for _, rep in self.entregas_rep)


def _cargar_datos_facturacion(
    session: Session,
    desde: date,
    hasta: date,
    local_id: Optional[int] = None,
) -> tuple[list[BloqueFacturacion], list[Gasto], list[EgresoCaja], dict, dict]:
    """Arma los bloques por combinación local+vendedora con una cantidad fija de
    queries (no crece con la cantidad de combinaciones): se trae todo el período
    de una y se agrupa en Python."""
    dt_desde, dt_hasta = start_of_day(desde), end_of_day(hasta)

    locales_by_id  = {l.local_id: l.nombre for l in session.exec(select(Local)).all()}
    usuarios_by_id = {u.usuario_id: u.nombre for u in session.exec(select(Usuario)).all()}

    # ── Ventas y sus pagos / detalles ─────────────────────────────────────────
    stmt_ventas = (
        select(Venta)
        .where(Venta.fecha_ingreso >= dt_desde)  # type: ignore
        .where(Venta.fecha_ingreso <= dt_hasta)  # type: ignore
    )
    if local_id is not None:
        stmt_ventas = stmt_ventas.where(Venta.local_id == local_id)
    ventas = session.exec(stmt_ventas).all()

    venta_ids      = [v.venta_id for v in ventas]
    fecha_by_venta = {v.venta_id: v.fecha_ingreso for v in ventas}
    combo_by_venta = {v.venta_id: (v.local_id, v.usuario_id) for v in ventas}

    pagos_by_venta    = get_pagos_by_venta(session, venta_ids)      # type: ignore
    detalles_by_venta = get_detalles_by_venta(session, venta_ids)   # type: ignore

    # {(local_id, usuario_id): {fecha: DiaFacturacion}}
    dias_por_combo: dict = defaultdict(dict)

    def _dia(combo, fecha) -> DiaFacturacion:
        return dias_por_combo[combo].setdefault(fecha, DiaFacturacion(fecha=fecha))

    for vid in venta_ids:
        combo = combo_by_venta[vid]
        fecha = _date_of(fecha_by_venta.get(vid))
        dia   = _dia(combo, fecha)
        for pago in pagos_by_venta.get(vid, []):
            dia.neto += pago.importe
            if not _es_electronico(pago.medio_de_pago):
                dia.efectivo += pago.importe

    # Detalles: alimentan las columnas informativas y el cálculo de comisiones
    detalles_por_combo: dict = defaultdict(lambda: {"ACCESORIO": [], "CELULAR": [], "CHIP": []})
    for vid, dets in detalles_by_venta.items():
        combo = combo_by_venta[vid]
        fecha = _date_of(fecha_by_venta.get(vid))
        dia   = _dia(combo, fecha)
        for d in dets:
            tipo = d["tipo_producto"]
            if tipo not in detalles_por_combo[combo]:
                continue
            detalles_por_combo[combo][tipo].append(
                {**d, "venta_id": vid, "fecha": fecha_by_venta.get(vid)}
            )
            if tipo == "ACCESORIO":
                dia.accesorios += d["subtotal"]
            elif tipo == "CHIP":
                dia.chips += d["subtotal"]

    # ── Reparaciones entregadas en el período (comisión al creador) ───────────
    stmt_rep = (
        select(MovimientoReparacion, Reparacion)
        .join(Reparacion, MovimientoReparacion.reparacion_id == Reparacion.reparacion_id)  # type: ignore
        .where(MovimientoReparacion.tipo_movimiento == "CAMBIO_ESTADO")
        .where(MovimientoReparacion.estado_nuevo    == "ENTREGADO")
        .where(MovimientoReparacion.fecha >= dt_desde)  # type: ignore
        .where(MovimientoReparacion.fecha <= dt_hasta)  # type: ignore
        .order_by(MovimientoReparacion.fecha)  # type: ignore
    )
    if local_id is not None:
        stmt_rep = stmt_rep.where(Reparacion.local_id == local_id)

    reps_por_combo: dict = defaultdict(list)
    for mov, rep in session.exec(stmt_rep).all():
        reps_por_combo[(rep.local_id, rep.usuario_id)].append((mov, rep))

    # ── Sobrantes / faltantes ─────────────────────────────────────────────────
    stmt_sf = (
        select(SobranteFaltante)
        .where(SobranteFaltante.fecha >= desde)  # type: ignore
        .where(SobranteFaltante.fecha <= hasta)  # type: ignore
        .where((SobranteFaltante.sobrante > 0) | (SobranteFaltante.faltante > 0))  # type: ignore
    )
    if local_id is not None:
        stmt_sf = stmt_sf.where(SobranteFaltante.local_id == local_id)

    sf_por_combo: dict = defaultdict(dict)
    for sf in session.exec(stmt_sf).all():
        combo = (sf.local_id, sf.usuario_id)
        sf_por_combo[combo][sf.fecha] = (sf.sobrante, sf.faltante)
        dia = _dia(combo, sf.fecha)
        dia.sobrante = sf.sobrante
        dia.faltante = sf.faltante

    # ── Config de comisiones ──────────────────────────────────────────────────
    configs = {c.tipo_producto: c for c in session.exec(select(ConfigComision)).all()}

    # ── Armado de los bloques (solo combinaciones con actividad) ──────────────
    combos = set(dias_por_combo) | set(reps_por_combo) | set(sf_por_combo)
    bloques: list[BloqueFacturacion] = []

    for lid, uid in combos:
        dets = detalles_por_combo.get((lid, uid), {"ACCESORIO": [], "CELULAR": [], "CHIP": []})
        entregas = reps_por_combo.get((lid, uid), [])
        sf_dia   = sf_por_combo.get((lid, uid), {})
        dias     = sorted(
            dias_por_combo.get((lid, uid), {}).values(),
            key=lambda d: (d.fecha is None, d.fecha or date.min),
        )
        bloques.append(BloqueFacturacion(
            local_id=lid,
            local_nombre=locales_by_id.get(lid, f"Local {lid}"),
            usuario_id=uid,
            usuario_nombre=usuarios_by_id.get(uid, f"Usuario {uid}"),
            dias=dias,
            entregas_rep=entregas,
            resumen=_calcular_resumen_comisiones(
                dets["ACCESORIO"], dets["CELULAR"], dets["CHIP"],
                entregas, sf_dia,
                configs.get("REPARACION"), configs.get("ACCESORIO"),
            ),
        ))

    bloques.sort(key=lambda b: (b.local_nombre, b.usuario_nombre))

    # ── Gastos y egresos ──────────────────────────────────────────────────────
    # Gasto NO tiene local_id: es global, no se filtra ni se prorratea por local.
    gastos = session.exec(
        select(Gasto)
        .where(Gasto.fecha >= dt_desde)  # type: ignore
        .where(Gasto.fecha <= dt_hasta)  # type: ignore
        .order_by(Gasto.fecha, Gasto.id)  # type: ignore
    ).all()

    stmt_egr = (
        select(EgresoCaja)
        .where(EgresoCaja.fecha >= dt_desde)  # type: ignore
        .where(EgresoCaja.fecha <= dt_hasta)  # type: ignore
        .order_by(EgresoCaja.fecha)  # type: ignore
    )
    if local_id is not None:
        stmt_egr = stmt_egr.where(EgresoCaja.local_id == local_id)
    egresos = session.exec(stmt_egr).all()

    return bloques, list(gastos), list(egresos), locales_by_id, usuarios_by_id


# ─── WRITERS DEL REPORTE DE FACTURACIÓN ──────────────────────────────────────

def _escribir_tabla_facturacion_dia(ws, fila, dias: list[DiaFacturacion]) -> int:
    fila = _label_row(ws, fila, "Facturación por día", 9)
    _hdr_row(ws, fila, [
        "Fecha", "Accesorios", "Chips", "Neto día", "Sobrante", "Faltante",
        "Total día", "Total efectivo", "Total electrónico",
    ], wrap=True)
    fila += 1

    for d in dias:
        _dat_row(ws, fila, [
            d.fecha.strftime("%d/%m/%Y") if d.fecha else "Sin fecha",
            d.accesorios or "",
            d.chips or "",
            d.neto,                      # se escribe siempre: un día en 0 con faltante es info
            d.sobrante or "",
            d.faltante or "",
            d.total_dia,
            d.total_efectivo,
            d.total_electronico,
        ], num_fmt=_NUM_FMT)
        fila += 1

    if not dias:
        _dat_row(ws, fila, ["Sin ventas en el período", "", "", "", "", "", "", "", ""])
        fila += 1

    _dat_row(ws, fila, [
        "TOTAL",
        sum(d.accesorios for d in dias) or "",
        sum(d.chips for d in dias) or "",
        sum(d.neto for d in dias),
        sum(d.sobrante for d in dias) or "",
        sum(d.faltante for d in dias) or "",
        sum(d.total_dia for d in dias),
        sum(d.total_efectivo for d in dias),
        sum(d.total_electronico for d in dias),
    ], font=_BOLD_FONT, num_fmt=_NUM_FMT)
    ws.cell(row=fila, column=1).alignment = _CENTER
    return fila + 1


def _escribir_bloque_combinacion(ws, fila, b: BloqueFacturacion) -> int:
    fila = _label_row(ws, fila, f"{b.local_nombre.upper()}  —  {b.usuario_nombre.upper()}",
                      12, font=_SECCION_FONT, fill=_FILL_SECCION)
    fila += 1

    fila = _escribir_tabla_facturacion_dia(ws, fila, b.dias)
    fila = _escribir_tabla_reparaciones(ws, fila + 1, b.entregas_rep, b.resumen, num_fmt=_NUM_FMT)
    fila = _escribir_tabla_resumen_categorias(ws, fila + 1, b.resumen, num_fmt=_NUM_FMT)

    fila += 1
    fila = _kv_row(ws, fila, "Total efectivo",   b.total_efectivo)
    fila = _kv_row(ws, fila, "Total electrónico", b.total_electronico)
    fila = _kv_row(ws, fila, "Total comisiones", b.total_comision)
    return fila + 2


def _escribir_resumen_general(ws, fila, bloques: list[BloqueFacturacion]) -> int:
    fila = _label_row(ws, fila, "RESUMEN GENERAL", 12, font=_SECCION_FONT, fill=_FILL_SECCION)
    fila += 1

    _hdr_row(ws, fila, ["LOCAL", "VENDEDORA", "TOTAL", "EF", "EL", "COMISIÓN"], wrap=True)
    fila += 1

    for b in bloques:
        _dat_row(ws, fila, [
            b.local_nombre, b.usuario_nombre,
            b.total_general, b.total_efectivo, b.total_electronico, b.total_comision,
        ], num_fmt=_NUM_FMT)
        fila += 1

    _dat_row(ws, fila, [
        "TOTAL GENERAL", "",
        sum(b.total_general    for b in bloques),
        sum(b.total_efectivo   for b in bloques),
        sum(b.total_electronico for b in bloques),
        sum(b.total_comision   for b in bloques),
    ], font=_BOLD_FONT, num_fmt=_NUM_FMT)
    ws.cell(row=fila, column=1).alignment = _CENTER
    return fila + 1


def _escribir_iva_debito(ws, fila, total_el: int, iva_debito: int) -> int:
    fila = _label_row(ws, fila, "IVA EN CONTRA (DÉBITO FISCAL)", 12,
                      font=_SECCION_FONT, fill=_FILL_SECCION)
    fila += 1
    fila = _kv_row(ws, fila, "Total facturado electrónico (en blanco)", total_el)
    fila = _kv_row(ws, fila, f"IVA en contra ({ALICUOTA_IVA}/121 del electrónico)", iva_debito)
    return fila


def _totales_gastos(gastos: list[Gasto], egresos: list[EgresoCaja],
                    total_comisiones: int) -> dict:
    """Totales de la sección de gastos.

    Se suman los aportes YA redondeados a pesos (no se redondea la suma) para que
    la fila TOTAL del Excel dé exactamente la suma visible de su columna."""
    tot_real    = sum(_a_pesos(g.aporte_real) for g in gastos)
    tot_blanco  = sum(_a_pesos(g.aporte_blanco) for g in gastos)
    tot_iva     = sum(_a_pesos(g.aporte_iva) for g in gastos)
    tot_egresos = sum(e.monto for e in egresos)
    return {
        "gastos_reales_cargados": tot_real,
        "egresos": tot_egresos,
        "comisiones": total_comisiones,
        "gastos_reales": tot_real + tot_egresos + total_comisiones,
        "gastos_blanco": tot_blanco,
        "iva_credito": tot_iva,
    }


def _escribir_seccion_gastos(ws, fila, gastos: list[Gasto], egresos: list[EgresoCaja],
                             locales: dict, usuarios: dict, t: dict,
                             local_filtrado: Optional[str] = None) -> int:
    fila = _label_row(ws, fila, "GASTOS", 12, font=_SECCION_FONT, fill=_FILL_SECCION)
    fila += 1

    if local_filtrado:
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=12)
        _cell(ws, fila, 1,
              f"Atención: los gastos no tienen local, son globales. Se listan TODOS aunque "
              f"el reporte esté filtrado por {local_filtrado}, así que el balance mezcla los "
              f"ingresos de ese local con los gastos de todos.",
              font=_NOTA_FONT, alignment=_LEFT)
        fila += 2

    # ── Tabla de gastos cargados ──────────────────────────────────────────────
    fila = _label_row(ws, fila, "Gastos cargados (montos redondeados a pesos)", 12)
    _hdr_row(ws, fila, [
        "Fecha", "Descripción", "Tipo", "Tipo factura", "Comprada", "% real",
        "Total", "Neto", "IVA", "Aporte real", "Aporte blanco", "Aporte IVA",
    ], wrap=True)
    fila += 1

    for g in gastos:
        ap_real   = _a_pesos(g.aporte_real)
        ap_blanco = _a_pesos(g.aporte_blanco)
        ap_iva    = _a_pesos(g.aporte_iva)

        _dat_row(ws, fila, [
            _fmt_fecha_ar(g.fecha),
            g.descripcion,
            g.tipo.value if hasattr(g.tipo, "value") else str(g.tipo),
            (g.tipo_factura.value if hasattr(g.tipo_factura, "value") else str(g.tipo_factura))
            if g.tipo_factura else "—",
            "Sí" if g.comprada else "No",
            g.porcentaje_real if g.porcentaje_real is not None else "—",
            _a_pesos(g.total),
            _a_pesos(g.neto) if g.neto is not None else "—",
            _a_pesos(g.iva) if g.iva is not None else "—",
            ap_real, ap_blanco, ap_iva,
        ], num_fmt=_NUM_FMT)
        fila += 1

    if not gastos:
        _dat_row(ws, fila, ["Sin gastos cargados en el período"] + [""] * 11)
        fila += 1

    _dat_row(ws, fila, ["TOTAL GASTOS", "", "", "", "", "", "", "", "",
                        t["gastos_reales_cargados"], t["gastos_blanco"], t["iva_credito"]],
             font=_BOLD_FONT, num_fmt=_NUM_FMT)
    ws.cell(row=fila, column=1).alignment = _CENTER
    fila += 2

    # ── Tabla de egresos de caja ──────────────────────────────────────────────
    fila = _label_row(ws, fila, "Egresos de caja (todos en efectivo)", 5)
    _hdr_row(ws, fila, ["Fecha", "Local", "Usuario", "Descripción", "Monto"], wrap=True)
    fila += 1

    for e in egresos:
        _dat_row(ws, fila, [
            _fmt_fecha_ar(e.fecha),
            locales.get(e.local_id, f"Local {e.local_id}"),
            usuarios.get(e.usuario_id, f"Usuario {e.usuario_id}"),
            e.descripcion,
            e.monto,
        ], num_fmt=_NUM_FMT)
        fila += 1

    if not egresos:
        _dat_row(ws, fila, ["Sin egresos de caja en el período", "", "", "", ""])
        fila += 1

    _dat_row(ws, fila, ["TOTAL EGRESOS", "", "", "", t["egresos"]],
             font=_BOLD_FONT, num_fmt=_NUM_FMT)
    ws.cell(row=fila, column=1).alignment = _CENTER
    fila += 2

    # ── Totales de la sección ─────────────────────────────────────────────────
    fila = _kv_row(ws, fila, "Gastos reales cargados (aporte real)", t["gastos_reales_cargados"])
    fila = _kv_row(ws, fila, "Egresos de caja", t["egresos"])
    fila = _kv_row(ws, fila, "Comisiones de vendedoras", t["comisiones"],
                   obs="No cargarlas además como gasto o egreso: se contarían dos veces")
    fila = _kv_row(ws, fila, "TOTAL GASTOS REALES", t["gastos_reales"])
    fila += 1
    fila = _kv_row(ws, fila, "TOTAL GASTOS PARA IMPUESTOS (en blanco)", t["gastos_blanco"])
    fila = _kv_row(ws, fila, "IVA A FAVOR (crédito fiscal)", t["iva_credito"])

    return fila


def _calcular_impuestos_y_balance(bloques: list[BloqueFacturacion], t: dict) -> dict:
    """Impuestos y balance del período. Todo en int pesos.

    Los ingresos en blanco se aproximan por lo facturado en electrónico. Las
    reparaciones entran por su margen (total cobrado − pago al reparador), no por
    su facturación bruta."""
    total_general    = sum(b.total_general    for b in bloques)
    total_efectivo   = sum(b.total_efectivo   for b in bloques)
    total_electronico = sum(b.total_electronico for b in bloques)
    margen_rep       = sum(b.margen_reparaciones for b in bloques)

    iva_debito  = iva_incluido(total_electronico)
    iva_a_pagar = iva_debito - t["iva_credito"]

    iibb = round(total_electronico * ALICUOTA_IIBB / 100)

    base_ganancias = (total_electronico - iva_debito) - t["gastos_blanco"] - iibb
    ganancias = round(base_ganancias * ALICUOTA_GANANCIAS / 100) if base_ganancias > 0 else 0

    ingresos            = total_general + margen_rep
    resultado_operativo = ingresos - t["gastos_reales"]
    total_impuestos     = max(0, iva_a_pagar) + iibb + ganancias

    return {
        **t,
        "total_general": total_general,
        "total_efectivo": total_efectivo,
        "total_electronico": total_electronico,
        "margen_reparaciones": margen_rep,
        "ingresos": ingresos,
        "iva_debito": iva_debito,
        "iva_a_pagar": iva_a_pagar,
        "iibb": iibb,
        "base_ganancias": base_ganancias,
        "ganancias": ganancias,
        "resultado_operativo": resultado_operativo,
        "total_impuestos": total_impuestos,
        "ganancia_final": resultado_operativo - total_impuestos,
    }


def _escribir_impuestos_y_balance(ws, fila, t: dict) -> int:
    fila = _label_row(ws, fila, "IMPUESTOS", 12, font=_SECCION_FONT, fill=_FILL_SECCION)
    fila += 1

    _hdr_row(ws, fila, ["Concepto", "", "", "Monto", "Observación"], wrap=True)
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=3)
    fila += 1

    obs_iva = ("Saldo técnico a favor (no se paga este período)"
               if t["iva_a_pagar"] < 0 else "IVA débito − IVA crédito")
    fila = _kv_row(ws, fila, "IVA a pagar", t["iva_a_pagar"], obs=obs_iva)
    fila = _kv_row(ws, fila, f"Ingresos Brutos ({ALICUOTA_IIBB}% del electrónico)", t["iibb"])

    fila = _kv_row(ws, fila, "Base Ganancias", t["base_ganancias"],
                   obs="(Electrónico − IVA débito) − gastos en blanco − IIBB")
    if t["base_ganancias"] > 0:
        obs_gan = f"{ALICUOTA_GANANCIAS}% de la base"
    elif t["base_ganancias"] < 0:
        obs_gan = f"Base negativa → sin impuesto (quebranto ${abs(t['base_ganancias']):,})"
    else:
        obs_gan = "Base en cero → sin impuesto"
    fila = _kv_row(ws, fila, "Impuesto a las Ganancias", t["ganancias"], obs=obs_gan)

    fila = _kv_row(ws, fila, "TOTAL IMPUESTOS", t["total_impuestos"],
                   obs="El IVA solo suma si da a pagar")
    fila += 2

    # ── Balance final ─────────────────────────────────────────────────────────
    fila = _label_row(ws, fila, "BALANCE FINAL", 12, font=_SECCION_FONT, fill=_FILL_SECCION)
    fila += 1

    fila = _kv_row(ws, fila, "Ventas del período (efectivo + electrónico)", t["total_general"])
    fila = _kv_row(ws, fila, "Margen de reparaciones entregadas", t["margen_reparaciones"],
                   obs="Total cobrado − pago al reparador")
    fila = _kv_row(ws, fila, "TOTAL INGRESOS", t["ingresos"])
    fila += 1
    fila = _kv_row(ws, fila, "Total gastos reales", -t["gastos_reales"],
                   obs="Gastos cargados + egresos de caja + comisiones")
    fila = _kv_row(ws, fila, "RESULTADO OPERATIVO", t["resultado_operativo"])
    fila += 1
    fila = _kv_row(ws, fila, "Total impuestos", -t["total_impuestos"])
    fila = _kv_row(ws, fila, "GANANCIA FINAL", t["ganancia_final"],
                   font=Font(bold=True, size=12))
    return fila


def _build_facturacion_excel(
    bloques: list[BloqueFacturacion],
    gastos: list[Gasto],
    egresos: list[EgresoCaja],
    locales: dict,
    usuarios: dict,
    periodo_label: str,
    local_label: str,
    local_filtrado: Optional[str] = None,
) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Facturación"  # type: ignore

    total_comisiones = sum(b.total_comision for b in bloques)
    t = _calcular_impuestos_y_balance(
        bloques, _totales_gastos(gastos, egresos, total_comisiones))

    fila = _escribir_encabezado_reporte(
        ws, 1, "RESUMEN DE FACTURACIÓN DEL LOCAL",
        f"{local_label}  |  Período: {periodo_label}", ancho_cols=12,
    )
    fila += 1

    for b in bloques:
        fila = _escribir_bloque_combinacion(ws, fila, b)

    if not bloques:
        fila = _label_row(ws, fila, "Sin actividad en el período", 12) + 1

    fila = _escribir_resumen_general(ws, fila, bloques) + 2
    fila = _escribir_iva_debito(ws, fila, t["total_electronico"], t["iva_debito"]) + 2
    fila = _escribir_seccion_gastos(ws, fila, gastos, egresos, locales, usuarios,
                                    t, local_filtrado) + 2
    _escribir_impuestos_y_balance(ws, fila, t)

    _aplicar_anchos(ws, _ANCHOS_FACTURACION)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/facturacion/excel")
def reporte_facturacion_excel(
    desde: date,
    hasta: date,
    local_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    """Resumen de facturación del período: una tabla por combinación local+vendedora
    con actividad, resumen general, IVA, gastos, impuestos y balance final."""
    if desde > hasta:
        raise HTTPException(422, "'desde' no puede ser posterior a 'hasta'")

    local_nombre = None
    if local_id is not None:
        local = session.get(Local, local_id)
        if not local:
            raise HTTPException(404, "Local no encontrado")
        local_nombre = local.nombre

    bloques, gastos, egresos, locales, usuarios = _cargar_datos_facturacion(
        session, desde, hasta, local_id)

    xlsx_bytes = _build_facturacion_excel(
        bloques=bloques,
        gastos=gastos,
        egresos=egresos,
        locales=locales,
        usuarios=usuarios,
        periodo_label=f"{desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}",
        local_label=f"Local: {local_nombre}" if local_nombre else "Todos los locales",
        local_filtrado=local_nombre,
    )

    sufijo   = f"_{local_nombre.replace(' ', '_')}" if local_nombre else ""
    filename = f"facturacion{sufijo}_{desde}_{hasta}.xlsx"
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
