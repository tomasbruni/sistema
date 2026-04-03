import io
from collections import defaultdict
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# — tus imports locales —
from app.db.models import (
    Accesorio, Celular, Chip, DetalleVentaAccesorio, DetalleVentaCelular,
    DetalleVentaChip, EgresoCaja, Local, MarcaCelular, ModeloCelular,
    PagoVenta, Usuario, Venta,
)
from app.db.session import get_session
from app.api.deps import get_current_user, UsuarioActual

router = APIRouter(prefix="/caja-diaria", tags=["Generar caja diaria"])
TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


# ─────────────────────────────────────────────
# Helpers de rango (igual que en egresos)
# ─────────────────────────────────────────────
def _start_of_day(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=TZ_AR)
 
def _end_of_day(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=TZ_AR)
 
 
# ─────────────────────────────────────────────
# Helpers de formato
# ─────────────────────────────────────────────
def _fmt_pesos(n: int) -> str:
    return f"${n:,}".replace(",", ".")
 
def _fmt_fecha(dt: Optional[datetime]) -> str:
    if not dt:
        return "-"
    local_dt = dt.astimezone(TZ_AR)
    return local_dt.strftime("%d/%m/%Y %H:%M")
 
 
# ─────────────────────────────────────────────
# Generador del PDF
# ─────────────────────────────────────────────
 
def _calcular_totales_pagos(ventas: list, pagos_by_venta: dict) -> tuple:
    """
    Devuelve (ef_total, el_total) donde el signo ya está incorporado:
    las ventas aportan positivo y las devoluciones negativo
    (porque sus pagos tienen importe negativo en la BD).
    """
    ef_total = el_total = 0
    for v in ventas:
        for p in pagos_by_venta.get(v.venta_id, []):
            if p.medio_de_pago.upper() == "EFECTIVO":
                ef_total += p.importe
            else:
                el_total += p.importe
    return ef_total, el_total
 
 
def _calcular_totales_por_tipo(ventas: list, detalles_by_venta: dict) -> tuple:
    """
    Devuelve (total_accesorios, total_celulares, total_chips).
    Usa precio_unitario * cantidad de cada detalle; el signo del monto_total
    de la venta determina si es venta o devolución, pero los detalles
    ya reflejan el signo correcto en precio_unitario.
    """
    acc = cel = chip = 0
    for v in ventas:
        signo = -1 if v.tipo == "DEVOLUCION" else 1
        for det in detalles_by_venta.get(v.venta_id, []):
            monto = det["precio_unitario"] * det["cantidad"] * signo
            if det["tipo_producto"] == "ACC":
                acc  += monto
            elif det["tipo_producto"] == "CEL":
                cel  += monto
            elif det["tipo_producto"] == "CHIP":
                chip += monto
    return acc, cel, chip
 
 
def _build_pdf(
    local_nombre: str,
    vendedora_nombre: str,
    fecha_label: str,
    ventas: list,
    ventas_by_id: dict,
    detalles_by_venta: dict,
    pagos_by_venta: dict,
    egresos: list,
) -> bytes:
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak
 
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=10*mm, rightMargin=10*mm,
        topMargin=10*mm, bottomMargin=10*mm,
    )
    W = A4[0] - 20*mm
 
    styles     = getSampleStyleSheet()
    normal     = ParagraphStyle("n",  parent=styles["Normal"], fontSize=8,  leading=10)
    bold       = ParagraphStyle("b",  parent=normal, fontName="Helvetica-Bold")
    header_cel = ParagraphStyle("hc", parent=bold,   fontSize=7.5)
    cell       = ParagraphStyle("c",  parent=normal,  fontSize=7.5, leading=9)
    cell_bold  = ParagraphStyle("cb", parent=cell,   fontName="Helvetica-Bold")
    seccion    = ParagraphStyle("s",  parent=styles["Normal"], fontSize=10,
                                fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=4)
    small      = ParagraphStyle("sm", parent=normal, fontSize=8)
 
    GRID_COLOR = colors.HexColor("#6B6B6B")
 
    def _enc_table() -> Table:
        """Encabezado en fila reutilizable (hoja 1 y 2)."""
        t = Table([[
            Paragraph("<b>CAJA DIARIA</b>",
                      ParagraphStyle("tit", parent=styles["Normal"],
                                     fontSize=13, fontName="Helvetica-Bold")),
            Paragraph(f"<b>Fecha:</b> {fecha_label}", bold),
            Paragraph(f"<b>Local:</b> {local_nombre}", bold),
            Paragraph(f"<b>Vendedora:</b> {vendedora_nombre}", bold),
        ]], colWidths=[W*0.28, W*0.22, W*0.22, W*0.28])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING",   (0,0),(-1,-1),4),
            ("RIGHTPADDING",  (0,0),(-1,-1),4),
            ("TOPPADDING",    (0,0),(-1,-1),3),
            ("BOTTOMPADDING", (0,0),(-1,-1),3),
            ("LINEBELOW",     (0,0),(-1,0), 0.75, colors.black),
        ]))
        return t
 
    story = []
 
    # ══ HOJA 1 ══
 
    # Encabezado
    story.append(_enc_table())
    story.append(Spacer(1, 6))
 
    # Sobrante / Faltante / Firma
    sf_data = [
        [Paragraph("Sobrante:", small),
         Paragraph("Faltante:", small),
         Paragraph("Firma vendedora:", small)],
        [Paragraph("", small), Paragraph("", small), Paragraph("", small)],
    ]
    sf_table = Table(
        sf_data,
        colWidths=[W*0.25, W*0.25, W*0.50],
        rowHeights=[12, 16]
    )
    #("LINEBEFORE", (col, fila_inicio), (col, fila_fin), ...)
    #("LINEBELOW", (col_inicio, fila), (col_fin, fila), grosor, color)
    sf_table.setStyle(TableStyle([
        ("VALIGN", (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING", (0,0),(-1,-1),2),
        ("RIGHTPADDING", (0,0),(-1,-1),6),
        ("TOPPADDING", (0,0), (-1,0), 1),
        ("BOTTOMPADDING", (0,0), (-1,0), 1),
        ("BOX", (0,0),(-1,-1),0.5, colors.black),
        ("LINEBEFORE", (1,0),(1,1),0.5, colors.black),
        ("LINEBEFORE", (2,0),(2,1),0.5, colors.black),
        ("LINEBELOW", (0,0), (1,0), 0.5, colors.black),
    ]))
    story.append(sf_table)
    story.append(Spacer(1, 8))
 
    # ── Tabla ventas ──
    story.append(Paragraph("VENTAS", seccion))
 
    col_widths = [
        W*0.04,  # ID
        W*0.06,  # tipo venta
        W*0.075,  # tipo prod
        W*0.22,  # nombre
        W*0.13,  # código
        W*0.08,  # p.lista
        W*0.08,  # p.unit
        W*0.04,  # cant
        W*0.16,  # pagos
        W*0.10,  # total
    ]
    header_row = [Paragraph(t, header_cel) for t in
        ["ID","Tipo","Producto","Nombre","Código","P.Lista","P.Unit.","Cant.","Pagos","Total"]]
 
    data       = [header_row]
    span_cmds  = []
    row_idx    = 1
 
    for v_idx, v in enumerate(sorted(ventas, key=lambda x: x.fecha_ingreso)):
        detalles  = detalles_by_venta.get(v.venta_id, [])
        pagos     = pagos_by_venta.get(v.venta_id, [])
        n         = max(len(detalles), 1)
        pagos_str = "\n".join(
            f"{p.medio_de_pago}: {_fmt_pesos(p.importe)}" for p in pagos
        ) or "-"
 
        for d_idx in range(n):
            det = detalles[d_idx] if d_idx < len(detalles) else None
            if d_idx == 0: # la primera fila de la venta(el primer detalle)
                c_id    = Paragraph(str(v.venta_id), cell)
                c_tipo  = Paragraph(v.tipo, cell)
                c_pagos = Paragraph(pagos_str, cell)
                c_total = Paragraph(_fmt_pesos(v.monto_total), cell_bold)
            else:
                c_id = c_tipo = c_pagos = c_total = Paragraph("", cell)
 
            if det:
                c_prod   = Paragraph(det["tipo_producto"], cell)
                c_nombre = Paragraph(det["nombre_producto"], cell)
                c_codigo = Paragraph(det.get("codigo") or "-", cell)
                c_lista  = Paragraph(_fmt_pesos(det["precio_lista"]), cell)
                c_unit   = Paragraph(_fmt_pesos(det["precio_unitario"]), cell)
                c_cant   = Paragraph(str(det["cantidad"]), cell)
            else:
                c_prod=c_nombre=c_codigo=c_lista=c_unit=c_cant=Paragraph("-",cell)
 
            data.append([c_id,c_tipo,c_prod,c_nombre,c_codigo,c_lista,c_unit,c_cant,c_pagos,c_total])
            row_idx += 1 #en la ultima iteracion(ultimo detalle), row_idx apunta a la proxima fila libre, por eso s y e estan bien calculados
 
        s = row_idx - n
        e = row_idx - 1
        span_cmds.append(("BOX", (0, s), (-1, e), 0.7, colors.black))
        if n > 1:
            for col in [0,1,8,9]: # alarga las columnas al largo de las filas de los detalles
                span_cmds.append(("SPAN",(col,s),(col,e)))
 
    t_style = [
        ("FONTSIZE",      (0,0),(-1,-1),7.5),
        ("GRID",          (0,0),(-1,-1),0.25, GRID_COLOR),
        ("LINEBELOW",     (0,0),(-1,0), 0.75, colors.black),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("VALIGN",        (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",   (0,0),(-1,-1),3),
        ("RIGHTPADDING",  (0,0),(-1,-1),3),
        ("TOPPADDING",    (0,0),(-1,-1),2),
        ("BOTTOMPADDING", (0,0),(-1,-1),2),
    ]
    # for ri in range(1, row_idx): no me gusta
    #     if ri % 2 == 0:
    #         t_style.append(("BACKGROUND",(0,ri),(-1,ri),colors.HexColor("#f2f2f2")))
 
    ventas_tbl = Table(data, colWidths=col_widths, repeatRows=1)
    ventas_tbl.setStyle(TableStyle(t_style + span_cmds)) # los comandos generados dinamicamente para cada venta segun sus detalles
    story.append(ventas_tbl)
    story.append(Spacer(1, 8))
 
    # ── Totales ventas ──
    # esto es sum pagos ef ventas - sum pagos ef devoluciones
    # esto es sum pagos el ventas - sum pagos el devoluciones
    ef_total, el_total = _calcular_totales_pagos(ventas, pagos_by_venta)
    neto_ventas        = ef_total + el_total
    total_acc, total_cel, total_chip = _calcular_totales_por_tipo(ventas, detalles_by_venta)
    #las devoluciones en la ui no las discrimina por efectivo y electronico 

    # Ventas brutas y devoluciones para mostrar desglose
    ventas_brutas = sum(v.monto_total for v in ventas if v.tipo != "DEVOLUCION")
    total_devol   = sum(v.monto_total for v in ventas if v.tipo == "DEVOLUCION")  # ya negativo
    # CREO Q LOS MONTOS ESTAN BIEN CALCULADOS
    BW = W / 3
 
    bloque_style = TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1),8),
        ("TOPPADDING",    (0,0),(-1,-1),1),
        ("BOTTOMPADDING", (0,0),(-1,-1),1),
        ("LEFTPADDING",   (0,0),(-1,-1),4),
        ("RIGHTPADDING",  (0,0),(-1,-1),4),
        ("LINEABOVE",     (0,-1),(-1,-1),0.5,colors.black),
        ("FONTNAME",      (0,-1),(-1,-1),"Helvetica-Bold"),
    ])

    bloque_style_sin_lineas = TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1),8),
        ("TOPPADDING",    (0,0),(-1,-1),1),
        ("BOTTOMPADDING", (0,0),(-1,-1),1),
        ("LEFTPADDING",   (0,0),(-1,-1),4),
        ("RIGHTPADDING",  (0,0),(-1,-1),4),
        ("FONTNAME",      (0,-1),(-1,-1),"Helvetica-Bold"),
    ])
 
    # Bloque 1: por medio de pago
    b1 = Table([
        [Paragraph("Total efectivo",    bold), Paragraph(_fmt_pesos(ef_total),     normal)],
        [Paragraph("Total electrónico", bold), Paragraph(_fmt_pesos(el_total),     normal)],
        [Paragraph("Total ventas",      bold), Paragraph(_fmt_pesos(neto_ventas),bold)],
    ], colWidths=[BW*0.6, BW*0.4])
    b1.setStyle(bloque_style)
 
    # Bloque 2: devoluciones
    b2 = Table([
        [Paragraph("Total sin devoluciones",      bold), Paragraph(_fmt_pesos(ventas_brutas),  normal)],
        [Paragraph("",                  bold), Paragraph("",                        normal)],
        [Paragraph("Devoluciones",       bold), Paragraph(_fmt_pesos(total_devol),  bold)],
    ], colWidths=[BW*0.6, BW*0.4])
    b2.setStyle(bloque_style)
 
    # Bloque 3: por tipo de producto
    b3 = Table([
        [Paragraph("Accesorios",  bold), Paragraph(_fmt_pesos(total_acc),  normal)],
        [Paragraph("Celulares",   bold), Paragraph(_fmt_pesos(total_cel),  normal)],
        [Paragraph("Chips",       bold), Paragraph(_fmt_pesos(total_chip), normal)],
    ], colWidths=[BW*0.6, BW*0.4])
    b3.setStyle(bloque_style_sin_lineas)
 
    row3 = Table([[b1, b2, b3]], colWidths=[BW, BW, BW])
    row3.setStyle(TableStyle([
        ("VALIGN",      (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING", (0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("BOX",         (0,0),(-1,-1),0.5,colors.black),
        ("LINEBEFORE",  (1,0),(1,-1),0.5,colors.black),
        ("LINEBEFORE",  (2,0),(2,-1),0.5,colors.black),
    ]))
    story.append(row3)
 
    neto_row = Table([
        [Paragraph("NETO VENTAS",
                   ParagraphStyle("nv",parent=bold,fontSize=10)),
         Paragraph(_fmt_pesos(neto_ventas),
                   ParagraphStyle("nv2",parent=bold,fontSize=10))]
    ], colWidths=[W*0.82, W*0.18])
    neto_row.setStyle(TableStyle([
        ("ALIGN",         (1,0),(1,-1),"RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1),3),
        ("BOTTOMPADDING", (0,0),(-1,-1),3),
        ("LEFTPADDING",   (0,0),(-1,-1),4),
        ("RIGHTPADDING",  (0,0),(-1,-1),4),
        ("LINEABOVE",     (0,0),(-1,-1),1,colors.black),
        ("LINEBELOW",     (0,0),(-1,-1),1,colors.black),
    ]))
    story.append(neto_row)
 
    # ══ HOJA 2: EGRESOS ══
    story.append(PageBreak())
    story.append(_enc_table())
    story.append(Spacer(1, 8))
    story.append(Paragraph("EGRESOS", seccion))
 
    if not egresos:
        story.append(Paragraph("Sin egresos en el período.", styles["Normal"]))
    else:
        eg_col_widths = [W*0.06, W*0.16, W*0.52, W*0.12, W*0.14]
        eg_header     = [Paragraph(t, header_cel) for t in
                         ["ID","Fecha/Hora","Descripción","Medio","Monto"]]
        eg_data       = [eg_header]
 
        for eg in egresos:
            eg_data.append([
                Paragraph(str(eg.egreso_caja_id), cell),
                Paragraph(_fmt_fecha(eg.fecha), cell),
                Paragraph(eg.descripcion, cell),
                Paragraph(eg.medio_pago or "-", cell),
                Paragraph(_fmt_pesos(eg.monto), cell),
            ])
 
        eg_style = [
            ("FONTSIZE",      (0,0),(-1,-1),7.5),
            ("GRID",          (0,0),(-1,-1),0.25,GRID_COLOR),
            ("LINEBELOW",     (0,0),(-1,0), 0.75,colors.black),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("VALIGN",        (0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",   (0,0),(-1,-1),3),
            ("RIGHTPADDING",  (0,0),(-1,-1),3),
            ("TOPPADDING",    (0,0),(-1,-1),2),
            ("BOTTOMPADDING", (0,0),(-1,-1),2),
        ]
        # for i in range(1, len(eg_data)): no me gusta
        #     if i % 2 == 0:
        #         eg_style.append(("BACKGROUND",(0,i),(-1,i),colors.HexColor("#f2f2f2")))
 
        eg_tbl = Table(eg_data, colWidths=eg_col_widths, repeatRows=1)
        eg_tbl.setStyle(TableStyle(eg_style))
        story.append(eg_tbl)
 
    story.append(Spacer(1, 6))
    total_egresos = sum(eg.monto for eg in egresos)
 
    tot_eg = Table(
        [[Paragraph("TOTAL EGRESOS", bold), Paragraph(_fmt_pesos(total_egresos), bold)]],
        colWidths=[W*0.82, W*0.18],
    )
    tot_eg.setStyle(TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1),9),
        ("ALIGN",         (1,0),(1,-1),"RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1),2),
        ("BOTTOMPADDING", (0,0),(-1,-1),2),
        ("LEFTPADDING",   (0,0),(-1,-1),4),
        ("RIGHTPADDING",  (0,0),(-1,-1),4),
        ("LINEABOVE",     (0,0),(-1,-1),0.75,colors.black),
    ]))
    story.append(tot_eg)
    story.append(Spacer(1, 10))
 
    # ── Balance ──
    story.append(HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=4))
    story.append(Paragraph("BALANCE FINAL", seccion))
 
    final_ef = ef_total - total_egresos
    final_el = el_total
 
    bal_data = [
        [Paragraph("Total final efectivo",    bold),
         Paragraph("(neto ef. − egresos)",    small),
         Paragraph(_fmt_pesos(final_ef),      normal)],
        [Paragraph("Total final electrónico", bold),
         Paragraph("(neto el.)",              small),
         Paragraph(_fmt_pesos(final_el),      normal)],
        [Paragraph("TOTAL FINAL",
                   ParagraphStyle("tf",parent=bold,fontSize=10)),
         Paragraph("", small),
         Paragraph(_fmt_pesos(final_ef+final_el),
                   ParagraphStyle("tf2",parent=bold,fontSize=10))],
    ]
    bal_tbl = Table(bal_data, colWidths=[W*0.28, W*0.54, W*0.18])
    bal_tbl.setStyle(TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1),9),
        ("ALIGN",         (2,0),(2,-1),"RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1),2),
        ("BOTTOMPADDING", (0,0),(-1,-1),2),
        ("LEFTPADDING",   (0,0),(-1,-1),4),
        ("RIGHTPADDING",  (0,0),(-1,-1),4),
        ("FONTNAME",      (0,2),(-1,2),"Helvetica-Bold"),
        ("FONTSIZE",      (0,2),(-1,2),10),
        ("LINEABOVE",     (0,2),(-1,2),1,colors.black),
        ("LINEBELOW",     (0,2),(-1,2),1,colors.black),
    ]))
    story.append(bal_tbl)
 
    doc.build(story)
    return buffer.getvalue()
 
 
# ─────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────
@router.get("/pdf")
def caja_diaria_pdf(
    local_id: int = Query(...),
    usuario_id: Optional[int] = Query(None),
    fecha: Optional[date] = Query(None, description="Día exacto (YYYY-MM-DD)"),
    desde: Optional[date] = Query(None, description="Inicio del rango (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fin del rango (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
    usuario: UsuarioActual = Depends(get_current_user),
):
    # --- Resolver rango ---
    if fecha:
        dt_desde = _start_of_day(fecha)
        dt_hasta = _end_of_day(fecha)
        fecha_label = fecha.strftime("%d/%m/%Y")
    elif desde and hasta:
        dt_desde = _start_of_day(desde)
        dt_hasta = _end_of_day(hasta)
        fecha_label = f"{desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}"
    else:
        raise HTTPException(status_code=400, detail="Debe indicar 'fecha' o 'desde' + 'hasta'")
 
    # --- Resolver usuario ---
    usuario_id = usuario_id if usuario_id is not None else usuario.usuario_id

    # --- Validar local y vendedora ---
    local = session.get(Local, local_id)
    if not local:
        raise HTTPException(status_code=404, detail="Local no encontrado")
 
    vendedora = session.get(Usuario, usuario_id)
    if not vendedora:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
 
    # --- Ventas ---
    ventas = session.exec(
        select(Venta)
        .where(Venta.local_id == local_id)
        .where(Venta.usuario_id == usuario_id)
        .where(Venta.fecha_ingreso >= dt_desde)  # type: ignore
        .where(Venta.fecha_ingreso <= dt_hasta)  # type: ignore
    ).all()
 
    venta_ids = [v.venta_id for v in ventas]
 
    # --- Pagos ---
    pagos_by_venta: dict[int, list] = defaultdict(list)
    if venta_ids:
        for p in session.exec(
            select(PagoVenta).where(PagoVenta.venta_id.in_(venta_ids))  # type: ignore
        ).all():
            pagos_by_venta[p.venta_id].append(p)
 
    # --- Detalles ---
    detalles_by_venta: dict[int, list] = defaultdict(list)
 
    if venta_ids:
        # Accesorios
        for detalle, acc in session.exec(
            select(DetalleVentaAccesorio, Accesorio)
            .join(Accesorio, DetalleVentaAccesorio.accesorio_id == Accesorio.accesorio_id)  # type: ignore
            .where(DetalleVentaAccesorio.venta_id.in_(venta_ids))  # type: ignore
        ).all():
            detalles_by_venta[detalle.venta_id].append({
                "tipo_producto": "ACC",
                "nombre_producto": acc.nombre,
                "codigo": acc.sku,
                "precio_lista": detalle.precio_lista,
                "precio_unitario": detalle.precio_unitario,
                "cantidad": detalle.cantidad,
            })
 
        # Celulares
        for detalle, cel, modelo, marca in session.exec(
            select(DetalleVentaCelular, Celular, ModeloCelular, MarcaCelular)
            .join(Celular, DetalleVentaCelular.celular_id == Celular.celular_id)  # type: ignore
            .join(ModeloCelular, Celular.modelo_celular_id == ModeloCelular.modelo_celular_id)  # type: ignore
            .join(MarcaCelular, Celular.marca_celular_id == MarcaCelular.marca_celular_id)  # type: ignore
            .where(DetalleVentaCelular.venta_id.in_(venta_ids))  # type: ignore
        ).all():
            detalles_by_venta[detalle.venta_id].append({
                "tipo_producto": "CEL",
                "nombre_producto": f"{marca.nombre} {modelo.nombre}",
                "codigo": cel.imei,
                "precio_lista": detalle.precio_lista,
                "precio_unitario": detalle.precio_unitario,
                "cantidad": 1,
            })
 
        # Chips
        for detalle, chip in session.exec(
            select(DetalleVentaChip, Chip)
            .join(Chip, DetalleVentaChip.chip_id == Chip.chip_id)  # type: ignore
            .where(DetalleVentaChip.venta_id.in_(venta_ids))  # type: ignore
        ).all():
            detalles_by_venta[detalle.venta_id].append({
                "tipo_producto": "CHIP",
                "nombre_producto": f"Chip {chip.compania}",
                "codigo": chip.numero_serie,
                "precio_lista": detalle.precio_lista,
                "precio_unitario": detalle.precio_unitario,
                "cantidad": 1,
            })
 
    # --- Egresos ---
    eg_query = (
        select(EgresoCaja)
        .where(EgresoCaja.local_id == local_id)
        .where(EgresoCaja.usuario_id == usuario_id)
        .where(EgresoCaja.fecha >= dt_desde)  # type: ignore
        .where(EgresoCaja.fecha <= dt_hasta)  # type: ignore
        .order_by(EgresoCaja.fecha)  # type: ignore
    )
    egresos = session.exec(eg_query).all()
 
    # --- Generar PDF ---
    pdf_bytes = _build_pdf(
        local_nombre=local.nombre,
        vendedora_nombre=vendedora.nombre,
        fecha_label=fecha_label,
        ventas=list(ventas),
        ventas_by_id={v.venta_id: v for v in ventas},
        detalles_by_venta=detalles_by_venta,
        pagos_by_venta=pagos_by_venta,
        egresos=list(egresos),
    )
 
    filename = f"caja_{local.nombre.replace(' ', '_')}_{fecha_label.replace('/', '-')}.pdf"
 
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
 