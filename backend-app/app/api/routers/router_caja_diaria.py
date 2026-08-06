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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
)

# — tus imports locales —
from app.db.models import (
    EgresoCaja, Local, MovimientoReparacion, PagoVenta, Reparacion, SobranteFaltante, Usuario, Venta,
)
from app.db.session import get_session
from app.api.deps import get_current_user, UsuarioActual
from app.api.funciones.ventas_funciones import get_detalles_by_venta, get_pagos_by_venta
from app.api.funciones.fechas import start_of_day, end_of_day, TZ_AR

router = APIRouter(prefix="/caja-diaria", tags=["Generar caja diaria"])
 
 
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
    Usa el `subtotal` de cada detalle, que ya viene firmado desde
    get_detalles_by_venta: las ventas suman y las devoluciones restan.
    """
    acc = cel = chip = 0
    for v in ventas:
        for det in detalles_by_venta.get(v.venta_id, []):
            monto = det["subtotal"]
            if det["tipo_producto"] == "ACCESORIO":
                acc  += monto
            elif det["tipo_producto"] == "CELULAR":
                cel  += monto
            elif det["tipo_producto"] == "CHIP":
                chip += monto
    return acc, cel, chip
 
 
def _build_pdf(
    local_nombre: str,
    vendedora_nombre: str,
    fecha_label: str,
    ventas: list,
    detalles_by_venta: dict,
    pagos_by_venta: dict,
    egresos: list,
    movimientos_rep: list,  # list of (MovimientoReparacion, Reparacion)
    sobrante: int = 0,
    faltante: int = 0,
) -> bytes:
    from reportlab.lib.units import mm, inch
    from reportlab.platypus import PageBreak
 
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=5*mm, rightMargin=5*mm,
        topMargin=0, bottomMargin=10*mm,
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
    
    I = Image("static/images/logo-pdf-removebg.png")
    I.drawHeight = 0.8 * inch 
    I.drawWidth = 0.8 * inch


    inner_table = Table([
        [Paragraph("<b>CAJA DIARIA</b>",
            ParagraphStyle("tit", parent=styles["Normal"],
                           fontSize=13, fontName="Helvetica-Bold"))],
        [Paragraph(f"<b>Fecha:</b> {fecha_label}", bold)]
    ])

    inner_table.setStyle(TableStyle([
        ("VALIGN",(0,1),(0,1),"BOTTOM"),
        ("BOTTOMPADDING",(0,1),(0,1),0),
    ]))

    def _enc_table() -> Table:
        """Encabezado en fila reutilizable (hoja 1 y 2)."""
        t = Table([[
            I,
            inner_table,
            Paragraph(f"<b>Local:</b> {local_nombre}", bold),
            Paragraph(f"<b>Vendedor/a:</b> {vendedora_nombre}", bold),
        ]
        ], colWidths=[I.drawWidth,W*0.33, W*0.33, W*0.33], rowHeights=[0.5*inch])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0),(0,0),"MIDDLE"),
            ("VALIGN",        (1,0),(1,0),"TOP"),
            ("VALIGN",        (2,0),(-1,-1),"BOTTOM"),
            ("LEFTPADDING",   (0,0),(-1,-1),0),
            ("RIGHTPADDING",  (0,0),(-1,-1),0),
            ("TOPPADDING",    (0,0),(-1,-1),0),
            ("BOTTOMPADDING", (2,0),(-1,-1),5.5),
            ("LINEBELOW",     (0,0),(-1,0), 0.75, colors.black),
        ]))
        return t
 
    story = []
 
    # ══ HOJA 1 ══
 
    # Encabezado
    story.append(_enc_table())
    story.append(Spacer(1, 6))
 
 
    # ── Tabla ventas ──
    story.append(Paragraph("VENTAS", seccion))
 
    #VAMOS A ELIMINAR LA COLUMNA CODIGO
    col_widths = [
        W*0.04,  # ID
        W*0.06,  # tipo venta
        W*0.075,  # tipo prod
        W*0.35,  # nombre
        W*0.08,  # p.lista
        W*0.08,  # p.unit
        W*0.05,  # cant
        W*0.16,  # pagos
        W*0.10,  # total
    ]
    header_row = [Paragraph(t, header_cel) for t in
        ["ID","Tipo","Gen.","Nombre","P.Lista","Cobrado","Cant.","Pagos","Total"]]
 
    data       = [header_row]
    span_cmds  = []
    row_idx    = 1

    _abrev = {"ACCESORIO": "ACC", "CELULAR": "CEL", "CHIP": "CHIP"}

    celulares_en_ventas = []   # (venta_id, nombre, codigo)
    chips_en_ventas = []       # (venta_id, nombre, codigo)
    observaciones_en_ventas = []  # (venta_id, observacion)

    for v_idx, v in enumerate(sorted(ventas, key=lambda x: x.fecha_ingreso)):
        detalles  = detalles_by_venta.get(v.venta_id, [])
        pagos     = pagos_by_venta.get(v.venta_id, [])
        n         = max(len(detalles), 1)
        pagos_str = "\n".join(
            f"{p.medio_de_pago}"
            f": {_fmt_pesos(p.importe)}"
            f"{f' ({p.cuotas} cuotas)' if p.medio_de_pago == 'CREDITO' else ''}"
            for p in pagos
        ) or "-"

        if v.observacion:
            observaciones_en_ventas.append((v.venta_id, v.observacion))

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
                c_prod   = Paragraph(_abrev.get(det["tipo_producto"], det["tipo_producto"]), cell) #type: ignore
                c_nombre = Paragraph(det["nombre_producto"], cell)
                c_lista  = Paragraph(_fmt_pesos(det["precio_lista"]), cell)
                c_unit   = Paragraph(_fmt_pesos(det["precio_unitario"]), cell)
                c_cant   = Paragraph(str(det["cantidad"]), cell)
                if det["tipo_producto"] == "CELULAR":
                    celulares_en_ventas.append((v.venta_id, det["nombre_producto"], det.get("codigo") or "-"))
                elif det["tipo_producto"] == "CHIP":
                    chips_en_ventas.append((v.venta_id, det["nombre_producto"], det.get("codigo") or "-"))
            else:
                c_prod=c_nombre=c_lista=c_unit=c_cant=Paragraph("-",cell)
 
            data.append([c_id,c_tipo,c_prod,c_nombre,c_lista,c_unit,c_cant,c_pagos,c_total])
            row_idx += 1 #en la ultima iteracion(ultimo detalle), row_idx apunta a la proxima fila libre, por eso s y e estan bien calculados
 
        s = row_idx - n
        e = row_idx - 1
        span_cmds.append(("BOX", (0, s), (-1, e), 0.7, colors.black))
        if n > 1:
            for col in [0,1,7,8]:
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

    _subtbl_style = [
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

    if celulares_en_ventas:
        story.append(Paragraph("CELULARES", seccion))
        cel_data = [[Paragraph(t, header_cel) for t in ["ID Venta", "Celular", "IMEI"]]] + [
            [Paragraph(str(vid), cell), Paragraph(nombre, cell), Paragraph(codigo, cell)]
            for vid, nombre, codigo in celulares_en_ventas
        ]
        cel_tbl = Table(cel_data, colWidths=[W*0.10, W*0.55, W*0.35], repeatRows=1)
        cel_tbl.setStyle(TableStyle(_subtbl_style))
        story.append(cel_tbl)
        story.append(Spacer(1, 6))

    if chips_en_ventas:
        story.append(Paragraph("CHIPS", seccion))
        chip_data = [[Paragraph(t, header_cel) for t in ["ID Venta", "Chip", "Nro. Serie"]]] + [
            [Paragraph(str(vid), cell), Paragraph(nombre, cell), Paragraph(codigo, cell)]
            for vid, nombre, codigo in chips_en_ventas
        ]
        chip_tbl = Table(chip_data, colWidths=[W*0.10, W*0.55, W*0.35], repeatRows=1)
        chip_tbl.setStyle(TableStyle(_subtbl_style))
        story.append(chip_tbl)
        story.append(Spacer(1, 6))

    if observaciones_en_ventas:
        story.append(Paragraph("OBSERVACIONES", seccion))
        obs_data = [[Paragraph(t, header_cel) for t in ["ID Venta", "Observación"]]] + [
            [Paragraph(str(vid), cell), Paragraph(obs, cell)]
            for vid, obs in observaciones_en_ventas
        ]
        obs_tbl = Table(obs_data, colWidths=[W*0.10, W*0.90], repeatRows=1)
        obs_tbl.setStyle(TableStyle(_subtbl_style))
        story.append(obs_tbl)
        story.append(Spacer(1, 6))

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

    # ── Reparaciones ──
    story.append(PageBreak())
    story.append(_enc_table())
    story.append(Spacer(1, 6))
    story.append(Paragraph("REPARACIONES", seccion))

    rep_ef = sum(
        mov.pago_parcial_agregado
        for mov, _ in movimientos_rep
        if (mov.tipo_movimiento == "CREACION" or mov.tipo_movimiento == "CAMBIO_ESTADO") and mov.pago_parcial_agregado
    )
    rep_ef += sum(
        mov.monto_entrega_recibido
        for mov, _ in movimientos_rep
        if mov.estado_nuevo == "ENTREGADO" and mov.monto_entrega_recibido
    )
    # Las correcciones de adelanto suman/restan la diferencia de efectivo del día
    rep_ef += sum(
        mov.monto_nuevo - mov.monto_anterior
        for mov, _ in movimientos_rep
        if mov.tipo_movimiento == "CAMBIO_ADELANTO"
        and mov.monto_nuevo is not None and mov.monto_anterior is not None
    )

    if not movimientos_rep:
        story.append(Paragraph("Sin movimientos de reparaciones en el período.", styles["Normal"]))
    else:
        rep_col_widths = [W*0.05, W*0.15, W*0.23, W*0.22, W*0.17, W*0.18]
        rep_header = [Paragraph(t, header_cel) for t in
            ["ID", "Tipo", "Celular", "Cliente", "Movimiento", "Monto cobrado"]]
        rep_data = [rep_header]

        for mov, rep in movimientos_rep:
            if mov.tipo_movimiento == "CREACION":
                tipo_label = "REVISION" if mov.estado_nuevo == "EN_REVISION" else "EN REPARACION"
                mov_label = "Adelanto"
                monto_str = _fmt_pesos(mov.pago_parcial_agregado) if mov.pago_parcial_agregado else "-"
                monto_style = cell_bold
            elif mov.tipo_movimiento == "CAMBIO_ESTADO" and mov.estado_nuevo == "ENTREGADO":
                tipo_label = "ENTREGA"
                mov_label = "Saldo restante"
                monto_str = _fmt_pesos(mov.monto_entrega_recibido) if mov.monto_entrega_recibido else "-"
                monto_style = cell_bold
            elif mov.tipo_movimiento == "CAMBIO_ESTADO" and mov.estado_nuevo == "EN_REPARACION":
                tipo_label = "ACEPTADA"
                mov_label = "Cliente acepta" # total final y restan pagar estan en la reparacion, no son relevantes en este movimiento
                monto_str = _fmt_pesos(mov.pago_parcial_agregado)
                monto_style = cell_bold
            elif mov.tipo_movimiento == "CAMBIO_ESTADO": # PARA DEVOLUCIONES Y GARANTIA
                tipo_label = "CAMBIO ESTADO"
                mov_label = f"{mov.estado_anterior} → {mov.estado_nuevo}"
                monto_str = "-"
                monto_style = cell
            elif mov.tipo_movimiento == "CAMBIO_ADELANTO":
                tipo_label = "MOD. ADELANTO"
                mov_label = f"{_fmt_pesos(mov.monto_anterior)} → {_fmt_pesos(mov.monto_nuevo)}" if mov.monto_anterior is not None else "-"
                monto_str = _fmt_pesos(mov.monto_nuevo - mov.monto_anterior)
                monto_style = cell_bold
            elif mov.tipo_movimiento == "CAMBIO_PRECIO":  # CAMBIO_PRECIO
                tipo_label = "CAMBIO TOTAL REP"
                mov_label = f"{_fmt_pesos(mov.monto_anterior)} → {_fmt_pesos(mov.monto_nuevo)}" if mov.monto_anterior is not None else "-"
                monto_str = "-"
                monto_style = cell
            else: #CANCELACION
                tipo_label = "CANCELACION"
                mov_label = "Se devuelven -> "
                monto_str =f"{_fmt_pesos(mov.monto_a_devolver)}" if mov.monto_a_devolver > 0 else "-" 
                monto_style = cell

            rep_data.append([
                Paragraph(str(rep.reparacion_id), cell),
                Paragraph(tipo_label, cell),
                Paragraph(rep.celular, cell),
                Paragraph(rep.nombre_cliente, cell),
                Paragraph(mov_label, cell),
                Paragraph(monto_str, monto_style),
            ])

        rep_style = [
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
        rep_tbl = Table(rep_data, colWidths=rep_col_widths, repeatRows=1)
        rep_tbl.setStyle(TableStyle(rep_style))
        story.append(rep_tbl)

    story.append(Spacer(1, 4))
    rep_subtotal = Table(
        [[Paragraph("TOTAL REPARACIONES (efectivo)", bold), Paragraph(_fmt_pesos(rep_ef), bold)]],
        colWidths=[W*0.82, W*0.18],
    )
    rep_subtotal.setStyle(TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1),9),
        ("ALIGN",         (1,0),(1,-1),"RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1),2),
        ("BOTTOMPADDING", (0,0),(-1,-1),2),
        ("LEFTPADDING",   (0,0),(-1,-1),4),
        ("RIGHTPADDING",  (0,0),(-1,-1),4),
        ("LINEABOVE",     (0,0),(-1,-1),0.75,colors.black),
    ]))
    story.append(rep_subtotal)

    # ── Egresos ──
    story.append(Spacer(1, 10))
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

    ef_esperado = ef_total - total_egresos   # ef ventas + ef rep - egresos
    final_el    = el_total

    # sobrante suma, faltante resta
    ef_real     = ef_esperado + sobrante - faltante
    total_final = ef_real + final_el

    tf_style  = ParagraphStyle("tf",  parent=bold,   fontSize=10)
    tf2_style = ParagraphStyle("tf2", parent=normal, fontSize=10)

    bal_data = [
        [Paragraph("Total final efectivo esperado", bold),
         Paragraph("(ef. ventas − egresos)", small),
         Paragraph(_fmt_pesos(ef_esperado), normal)],
        [Paragraph("Total final electrónico", bold),
         Paragraph("(neto electrónico)", small),
         Paragraph(_fmt_pesos(final_el), normal)],
    ]
    bal_style = [
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("ALIGN",         (2,0),(2,-1),  "RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
    ]

    # Sobrante / faltante solo si aplica
    if sobrante:
        bal_data.append([
            Paragraph("Sobrante", bold),
            Paragraph("(efectivo)", small),
            Paragraph(_fmt_pesos(sobrante), normal),
        ])
    if faltante:
        bal_data.append([
            Paragraph("Faltante", bold),
            Paragraph("(efectivo)", small),
            Paragraph(f"− {_fmt_pesos(faltante)}", normal),
        ])

    # Total final efectivo real
    ef_real_row = len(bal_data)
    bal_data.append([
        Paragraph("Total final efectivo real", bold),
        Paragraph("(esperado ± sobrante/faltante)", small),
        Paragraph(_fmt_pesos(ef_real), normal),
    ])
    bal_style += [
        ("LINEABOVE", (0, ef_real_row), (-1, ef_real_row), 0.5, colors.black),
    ]

    # Total final
    total_row = len(bal_data)
    bal_data.append([
        Paragraph("TOTAL FINAL", tf_style),
        Paragraph("", small),
        Paragraph(_fmt_pesos(total_final), tf_style),
    ])
    bal_style += [
        ("FONTNAME",  (0, total_row), (-1, total_row), "Helvetica-Bold"),
        ("FONTSIZE",  (0, total_row), (-1, total_row), 10),
        ("LINEABOVE", (0, total_row), (-1, total_row), 1, colors.black),
        ("LINEBELOW", (0, total_row), (-1, total_row), 1, colors.black),
    ]

    bal_tbl = Table(bal_data, colWidths=[W*0.32, W*0.50, W*0.18])
    bal_tbl.setStyle(TableStyle(bal_style))
    story.append(bal_tbl)
    story.append(Spacer(1, 10))

    # Firma vendedora
    firma_table = Table(
        [
            [Paragraph("Firma y aclaración:", small)],
            [Paragraph("", small)],
        ],
        colWidths=[W*0.45],
        rowHeights=[12, 52],
    )
    firma_table.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.black),
    ]))
    story.append(firma_table)
    story.append(Spacer(1, 8))


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
        dt_desde = start_of_day(fecha)
        dt_hasta = end_of_day(fecha)
        fecha_label = fecha.strftime("%d/%m/%Y")
    elif desde and hasta:
        dt_desde = start_of_day(desde)
        dt_hasta = end_of_day(hasta)
        fecha_label = f"{desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}"
    else:
        raise HTTPException(status_code=400, detail="Debe indicar 'fecha' o 'desde' + 'hasta'")
 
    # --- Resolver usuario ---
    usuario_id = usuario_id if usuario_id is not None else usuario.usuario_id

    # --- Validar local y vendedora ---
    local = session.get(Local, local_id)# type: ignore
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
        .order_by(
                Venta.fecha_ingreso.asc(), #type: ignore
                Venta.venta_id.asc(),  #type: ignore desempate estable para que las páginas no se solapen
            )
    ).all()
 
    venta_ids = [v.venta_id for v in ventas]
 
    # --- Pagos ---
    pagos_by_venta = get_pagos_by_venta(session, venta_ids) # type: ignore
 
    # --- Detalles ---
    detalles_by_venta = get_detalles_by_venta(session, venta_ids) # type: ignore
 
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

    # --- Movimientos de reparaciones del rango (join para filtrar por local y usuario) ---
    movimientos_rep = session.exec(
        select(MovimientoReparacion, Reparacion)
        .join(Reparacion, MovimientoReparacion.reparacion_id == Reparacion.reparacion_id)  # type: ignore
        .where(Reparacion.local_id == local_id)
        .where(MovimientoReparacion.usuario_id == usuario_id)
        .where(MovimientoReparacion.fecha >= dt_desde)  # type: ignore
        .where(MovimientoReparacion.fecha <= dt_hasta)  # type: ignore
        .order_by(MovimientoReparacion.fecha)  # type: ignore
    ).all()

    # --- Sobrante / Faltante (solo aplica a consulta de día exacto) ---
    sf_sobrante = sf_faltante = 0
    if fecha:
        sf = session.exec(
            select(SobranteFaltante)
            .where(SobranteFaltante.fecha == fecha)
            .where(SobranteFaltante.local_id == local_id)
            .where(SobranteFaltante.usuario_id == usuario_id)
        ).first()
        if sf:
            sf_sobrante = sf.sobrante
            sf_faltante = sf.faltante

    # --- Generar PDF ---
    pdf_bytes = _build_pdf(
        local_nombre=local.nombre,
        vendedora_nombre=vendedora.nombre,
        fecha_label=fecha_label,
        ventas=list(ventas),
        detalles_by_venta=detalles_by_venta,
        pagos_by_venta=pagos_by_venta,
        egresos=list(egresos),
        movimientos_rep=list(movimientos_rep),
        sobrante=sf_sobrante,
        faltante=sf_faltante,
    )
 
    filename = f"caja_{local.nombre.replace(' ', '_')}_{fecha_label.replace('/', '-')}.pdf"
 
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
 