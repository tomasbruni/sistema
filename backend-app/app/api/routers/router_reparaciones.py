from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, SQLModel
from sqlalchemy import exc
from typing import Optional
from datetime import date, datetime
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable

from app.db.session import get_session
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *

from app.api.deps import get_current_user, require_admin, UsuarioActual
from app.api.funciones.fechas import start_of_day, end_of_day, TZ_AR

router = APIRouter(
    prefix="/reparaciones",
    tags=["Reparaciones"],
)

# ── Inputs para transiciones ──────────────────────────────────────────────────

class CambioPrecioInput(SQLModel):
    monto_agregado: int
    observaciones: Optional[str] = None
    fecha: Optional[date] = None
    usuario_id: Optional[int] = None


class TransicionInput(SQLModel):
    observaciones: Optional[str] = None
    fecha: Optional[date] = None
    usuario_id: Optional[int] = None


class CancelarInput(SQLModel):
    observaciones: Optional[str] = None
    fecha: Optional[date] = None
    usuario_id: Optional[int] = None
    monto_a_devolver: Optional[int] = None


class AceptarInput(SQLModel):
    pago_parcial_agregado: int 
    total_final: int
    fecha: Optional[date] = None
    usuario_id: Optional[int] = None
    observaciones: Optional[str] = None

class CambioPagoParcial(SQLModel):
    nuevo_monto: int
    observaciones: Optional[str] = None
    fecha: Optional[date] = None
    usuario_id: Optional[int] = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_or_404(reparacion_id: int, session: Session) -> Reparacion:
    reparacion = session.get(Reparacion, reparacion_id)
    if not reparacion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reparación no encontrada")
    return reparacion

ESTADOS_VALIDOS_CREACION = ["EN_REVISION", "EN_REPARACION"]


# ── GET ───────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[Reparacion])
def listar_reparaciones(
    estado: Optional[str] = None,
    local_id: Optional[int] = None,
    usuario_id: Optional[int] = None,
    dni_cliente: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    statement = select(Reparacion)
    if current_user.rol != "admin":
        statement = statement.where(Reparacion.usuario_id == current_user.usuario_id)
    elif usuario_id is not None:
        statement = statement.where(Reparacion.usuario_id == usuario_id)
    if estado is not None:
        statement = statement.where(Reparacion.estado == estado)
    if local_id is not None:
        statement = statement.where(Reparacion.local_id == local_id)
    if dni_cliente is not None:
        statement = statement.where(Reparacion.dni_cliente.contains(dni_cliente))  # type: ignore
    if fecha_desde is not None:
        statement = statement.where(Reparacion.fecha_ingreso >= start_of_day(fecha_desde))  # type: ignore
    if fecha_hasta is not None:
        statement = statement.where(Reparacion.fecha_ingreso <= end_of_day(fecha_hasta))  # type: ignore
    return session.exec(statement).all()


@router.get("/{reparacion_id}", response_model=Reparacion)
def obtener_reparacion(
    reparacion_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    return _get_or_404(reparacion_id, session)


@router.get("/{reparacion_id}/historial", response_model=list[MovimientoReparacion])
def listar_historial_reparacion(
    reparacion_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    _get_or_404(reparacion_id, session)
    statement = (
        select(MovimientoReparacion)
        .where(MovimientoReparacion.reparacion_id == reparacion_id)
        .order_by(MovimientoReparacion.fecha)  # type: ignore
    )
    return session.exec(statement).all()


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_reparacion(
    data: ReparacionCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    try:
        if data.estado_inicial not in ESTADOS_VALIDOS_CREACION:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Estados validos {ESTADOS_VALIDOS_CREACION}")

        if data.estado_inicial == "EN_REPARACION":
            if data.total is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EN_REPARACION requiere que se especifique el total")
            if data.pago_parcial > data.total:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El pago_parcial no puede superar el total")
        elif data.estado_inicial == "EN_REVISION":
            if data.total is not None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EN_REVISION no debe tener total (se desconoce al momento de la revisión)")

        campos = data.model_dump(exclude={"estado_inicial", "fecha_ingreso", "usuario_id"})
        usuario_id = (
            data.usuario_id
            if current_user.rol == "admin" and data.usuario_id is not None
            else current_user.usuario_id
        )

        nueva = Reparacion(**campos, estado=data.estado_inicial, usuario_id=usuario_id)
        if current_user.rol == "admin" and data.fecha_ingreso is not None:
            nueva.fecha_ingreso = start_of_day(data.fecha_ingreso)

        session.add(nueva)
        session.flush()  # obtener nueva.reparacion_id sin cerrar la transacción

        movimiento = MovimientoReparacion(
            reparacion_id=nueva.reparacion_id, #type: ignore
            tipo_movimiento="CREACION",
            estado_anterior=None,
            estado_nuevo=data.estado_inicial,
            pago_parcial_agregado=nueva.pago_parcial,
            monto_nuevo=nueva.total,
            usuario_id=usuario_id,
        )
        if current_user.rol == "admin" and data.fecha_ingreso is not None:
            movimiento.fecha = start_of_day(data.fecha_ingreso)
        session.add(movimiento)
        session.commit()
        session.refresh(nueva)
        return {"mensaje": "Reparación creada exitosamente", "reparacion": nueva}
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error: {str(e)}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


# ── UPDATE (campos de datos, sin estado) ──────────────────────────────────────

@router.put("/{reparacion_id}")
def actualizar_reparacion(
    reparacion_id: int,
    data: ReparacionUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    try:
        update_data = data.model_dump(exclude_unset=True)
        if current_user.rol != "admin":
            update_data.pop("pagado", None)
            update_data.pop("pago_reparador", None)
        for key, value in update_data.items():
            setattr(reparacion, key, value)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Reparación actualizada exitosamente", "reparacion": reparacion}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error de integridad al actualizar")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


# ── TRANSICIONES ──────────────────────────────────────────────────────────────

@router.post("/{reparacion_id}/cambio-de-precio")
def cambio_de_precio(
    reparacion_id: int,
    data: CambioPrecioInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    try:
        monto_anterior = reparacion.total
        monto_nuevo = monto_anterior + data.monto_agregado #type: ignore
        reparacion.total = monto_nuevo

        usuario_id = (
            data.usuario_id
            if current_user.rol == "admin" and data.usuario_id is not None
            else current_user.usuario_id
        )
        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_PRECIO",
            estado_anterior=reparacion.estado,
            estado_nuevo=reparacion.estado,
            monto_anterior=monto_anterior,
            monto_nuevo=monto_nuevo,
            usuario_id=usuario_id,
            observaciones=data.observaciones,
        )
        if current_user.rol == "admin" and data.fecha is not None:
            movimiento.fecha = start_of_day(data.fecha)
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Precio actualizado exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")
    


@router.post("/{reparacion_id}/cambio-pago-parcial")
def cambio_de_pago_parcial(
    reparacion_id: int,
    data: CambioPagoParcial,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    # SI LA VENDEDORA SE EQUIVOCA, PUEDE MODIFICAR EL PAGO PARCIAL RECIBIDO,
    # PERO GENERA UN MOVIMIENTO DE CAMBIO PARA REPORTE
    reparacion = _get_or_404(reparacion_id, session)
    if data.nuevo_monto < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=f"El monto es menor a 0")
    if (reparacion.total is not None) and data.nuevo_monto > reparacion.total:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail=f"El monto es mayor al total")
 
    try:
        usuario_id = (
            data.usuario_id
            if current_user.rol == "admin" and data.usuario_id is not None
            else current_user.usuario_id
        )
        pago_parcial_anterior = reparacion.pago_parcial
        reparacion.pago_parcial = data.nuevo_monto
        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ADELANTO",
            estado_anterior=reparacion.estado,
            estado_nuevo=reparacion.estado,
            monto_anterior=pago_parcial_anterior,
            monto_nuevo=data.nuevo_monto,
            usuario_id=usuario_id,
            observaciones=data.observaciones,
        )
        if current_user.rol == "admin" and data.fecha is not None:
            movimiento.fecha = start_of_day(data.fecha)
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Pago actualizado exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.post("/{reparacion_id}/entregar")
def entregar(
    reparacion_id: int,
    data: TransicionInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    if reparacion.estado != "EN_REPARACION":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se puede entregar una reparación en estado EN_REPARACION (actual: {reparacion.estado})")
    try:
        estado_anterior = reparacion.estado
        reparacion.estado = "ENTREGADO"

        usuario_id = (
            data.usuario_id
            if current_user.rol == "admin" and data.usuario_id is not None
            else current_user.usuario_id
        )
        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ESTADO",
            estado_anterior=estado_anterior,
            estado_nuevo="ENTREGADO",
            monto_entrega_recibido=reparacion.total - reparacion.pago_parcial, #type: ignore
            usuario_id=usuario_id,
            observaciones=data.observaciones,
        )
        if current_user.rol == "admin" and data.fecha is not None:
            movimiento.fecha = start_of_day(data.fecha)
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Reparación entregada exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.post("/{reparacion_id}/aceptar")
def aceptar(
    reparacion_id: int,
    data: AceptarInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
): 
    reparacion = _get_or_404(reparacion_id, session)
    if reparacion.estado != "EN_REVISION":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se puede aceptar una reparación en estado EN_REVISION (actual: {reparacion.estado})")
    try:
        # SE ACEPTA UNA REPARACION EN REVISION, SE AGREGA AL pago_parcial LA PLATA RECIBIDA,
        # SE ESTABLECE EL TOTAL FINAL
        # pago_parcial SE TOMA COMO PAGO PARCIAL, PUEDE AGREGAR MAS O DEJAR LO QUE YA HABIA PUESTO EN LA REVISION
        reparacion.estado = "EN_REPARACION"
        reparacion.total = data.total_final

        if data.pago_parcial_agregado is None:
            pago_parcial_agregado_final = 0
        else:
            pago_parcial_agregado_final = data.pago_parcial_agregado

        reparacion.pago_parcial += pago_parcial_agregado_final
        if reparacion.pago_parcial > reparacion.total:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail=f"El pago_parcial es mayor al total")
        
        usuario_id = (
            data.usuario_id
            if current_user.rol == "admin" and data.usuario_id is not None
            else current_user.usuario_id
        )

        # MOVIMIENTO REPORTANDO CUANTO DINERO SE RECIBIO, SUMANDOLO A LO QUE YA SE HABIA RECIBIDO DE LA REVISION
        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ESTADO",
            estado_anterior="EN_REVISION",
            estado_nuevo=reparacion.estado,
            pago_parcial_agregado=pago_parcial_agregado_final, #type: ignore
            monto_nuevo=reparacion.total,
            usuario_id=usuario_id,
            observaciones=data.observaciones,
        )

        if current_user.rol == "admin" and data.fecha is not None:
            movimiento.fecha = start_of_day(data.fecha)

        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Reparación entregada exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.post("/{reparacion_id}/cancelar")
def cancelar(
    reparacion_id: int,
    data: CancelarInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    if reparacion.estado not in ESTADOS_VALIDOS_CREACION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se puede entregar una reparación en estado EN_REPARACION o EN_REVISION (actual: {reparacion.estado})")
    try:
        estado_anterior = reparacion.estado
        reparacion.estado = "CANCELADO"

        usuario_id = (
            data.usuario_id
            if current_user.rol == "admin" and data.usuario_id is not None
            else current_user.usuario_id
        )
        if data.monto_a_devolver is None:
            monto_a_devolver_final = 0
        else:
            if data.monto_a_devolver > reparacion.pago_parcial:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="El monto a devolver tiene que ser menor al pago_parcial")
            monto_a_devolver_final = data.monto_a_devolver

        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ESTADO",
            estado_anterior=estado_anterior,
            estado_nuevo="CANCELADO",
            usuario_id=usuario_id,
            observaciones=data.observaciones,
            monto_a_devolver=monto_a_devolver_final
        )
        if current_user.rol == "admin" and data.fecha is not None:
            movimiento.fecha = start_of_day(data.fecha)
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Reparación entregada exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.post("/{reparacion_id}/garantia")
def garantia(
    reparacion_id: int,
    data: TransicionInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    if reparacion.estado != "ENTREGADO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se puede enviar a garantía una reparación en estado ENTREGADO (actual: {reparacion.estado})")
    try:
        estado_anterior = reparacion.estado
        reparacion.estado = "REPARACION_GARANTIA"

        usuario_id = (
            data.usuario_id
            if current_user.rol == "admin" and data.usuario_id is not None
            else current_user.usuario_id
        )
        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ESTADO",
            estado_anterior=estado_anterior,
            estado_nuevo="REPARACION_GARANTIA",
            usuario_id=usuario_id,
            observaciones=data.observaciones,
        )
        if current_user.rol == "admin" and data.fecha is not None:
            movimiento.fecha = start_of_day(data.fecha)
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Reparación enviada a garantía exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


@router.post("/{reparacion_id}/entregar-garantia")
def entregar_garantia(
    reparacion_id: int,
    data: TransicionInput,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    reparacion = _get_or_404(reparacion_id, session)
    if reparacion.estado != "REPARACION_GARANTIA":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se puede entregar la garantía de una reparación en estado REPARACION_GARANTIA (actual: {reparacion.estado})")
    try:
        estado_anterior = reparacion.estado
        reparacion.estado = "ENTREGADO_GARANTIA"

        usuario_id = (
            data.usuario_id
            if current_user.rol == "admin" and data.usuario_id is not None
            else current_user.usuario_id
        )
        movimiento = MovimientoReparacion(
            reparacion_id=reparacion_id,
            tipo_movimiento="CAMBIO_ESTADO",
            estado_anterior=estado_anterior,
            estado_nuevo="ENTREGADO_GARANTIA",
            usuario_id=usuario_id,
            observaciones=data.observaciones,
        )
        if current_user.rol == "admin" and data.fecha is not None:
            movimiento.fecha = start_of_day(data.fecha)
        session.add(movimiento)
        session.commit()
        session.refresh(reparacion)
        return {"mensaje": "Garantía entregada exitosamente", "reparacion": reparacion}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _pdf_styles():
    styles = getSampleStyleSheet()
    def style(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)
    return {
        "titulo":   style("titulo",  fontSize=13, fontName="Helvetica-Bold", alignment=1, spaceAfter=2),
        "subtitulo":style("sub",     fontSize=9,  alignment=1, spaceAfter=6),
        "bold9":    style("b9",      fontSize=9,  fontName="Helvetica-Bold"),
        "normal9":  style("n9",      fontSize=9,  leading=12),
        "small8":   style("s8",      fontSize=8,  leading=10),
        "legal":    style("legal",   fontSize=7.5, leading=10, alignment=4),
        "aviso":    style("aviso",   fontSize=9,  fontName="Helvetica-Bold", alignment=1),
        "punteo":   style("punt",    fontSize=9,  leading=13),
    }


def _tabla_style():
    return TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.black),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, colors.HexColor("#AAAAAA")),
    ])


def _bloque_patron(W, s):
    PATRON_IMG = "static/images/pattern-lock-icon.jpg"
    img_size = 28*mm
    patron_img = Image(PATRON_IMG, width=img_size, height=img_size)
    patron_data = [[
        Paragraph("<b>Patrón de desbloqueo:</b>", s["bold9"]),
        patron_img,
        Table(
            [
                [Paragraph("<b>Código de desbloqueo:</b>", s["bold9"])],
                [Paragraph("_" * 38, s["normal9"])],
                [Spacer(1, 3*mm)],
                [Paragraph("<b>(completar a mano)</b>", s["small8"])],
            ],
            colWidths=[W * 0.52],
        ),
    ]]
    tbl = Table(patron_data, colWidths=[W * 0.26, img_size + 4*mm, W * 0.52])
    tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.black),
        ("LINEBEFORE",    (1, 0), (1, -1),  0.5, colors.black),
        ("LINEBEFORE",    (2, 0), (2, -1),  0.5, colors.black),
    ]))
    return tbl


def _bloque_firma(s):
    return [
        Paragraph("___________________________", s["normal9"]),
        Paragraph("Firma y aclaración del cliente", s["small8"]),
    ]


# ── PDF: Certificado de recepción (estado-consciente) ─────────────────────────

@router.get("/{reparacion_id}/certificado-recepcion")
def certificado_recepcion(
    reparacion_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    rep = _get_or_404(reparacion_id, session)
    local   = session.get(Local,   rep.local_id)
    usuario = session.get(Usuario, rep.usuario_id)

    es_revision = rep.estado == "EN_REVISION"

    fecha_str   = rep.fecha_ingreso.astimezone(TZ_AR).strftime("%d/%m/%Y") if rep.fecha_ingreso else "-"
    local_str   = local.nombre   if local   else "-"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=14*mm, bottomMargin=14*mm)
    W = A4[0] - 36*mm
    s = _pdf_styles()

    def fila(label, valor):
        return [Paragraph(f"<b>{label}</b>", s["bold9"]), Paragraph(valor or "-", s["normal9"])]

    story = []

    titulo_texto = "PLANILLA DE RECEPCIÓN — REVISIÓN TÉCNICA" if es_revision else "PLANILLA DE RECEPCIÓN — REPARACIÓN"
    story.append(Paragraph(titulo_texto, s["titulo"]))
    story.append(Paragraph(f"N° {reparacion_id:04d}  —  {local_str}  —  {fecha_str}", s["subtitulo"]))
    story.append(HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=5))

    tbl_cliente = Table([
        fila("Cliente:",   rep.nombre_cliente),
        fila("Teléfono:",  rep.telefono_cliente),
        fila("DNI:",       rep.dni_cliente or "-"),
        fila("Mail:",      rep.mail_cliente or "-"),
    ], colWidths=[W * 0.22, W * 0.78])
    tbl_cliente.setStyle(_tabla_style())
    story.append(tbl_cliente)
    story.append(Spacer(1, 4*mm))

    if es_revision:
        equipo_rows = [
            fila("Equipo:",          rep.celular),
            fila("Descripción:",     rep.descripcion or "-"),
            fila("Costo revisión:",  f"${rep.pago_parcial:,}"),
        ]
    else:
        saldo = (rep.total or 0) - rep.pago_parcial
        equipo_rows = [
            fila("Equipo:",      rep.celular),
            fila("Descripción:", rep.descripcion or "-"),
            fila("Total:",       f"${rep.total:,}"),
            fila("Adelanto:",    f"${rep.pago_parcial:,}"),
            fila("Restan pagar:",       f"${saldo:,}"),
        ]

    tbl_equipo = Table(equipo_rows, colWidths=[W * 0.22, W * 0.78])
    tbl_equipo.setStyle(_tabla_style())
    story.append(tbl_equipo)
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("EL CELULAR SE RECIBE SIN ACCESORIOS NI SIM CARD DEL CLIENTE", s["aviso"]))
    story.append(Spacer(1, 5*mm))
    story.append(_bloque_patron(W, s))
    story.append(Spacer(1, 5*mm))

    if es_revision:
        texto_legal = (
            "El equipo se recibe exclusivamente para diagnóstico técnico. El costo de revisión abonado cubre "
            "la evaluación del equipo. Una vez realizado el diagnóstico, se informará al cliente el presupuesto "
            "de reparación. Si el cliente acepta el presupuesto, el costo de revisión será descontado del total. "
            "Transcurridos los <b>90 días corridos</b> a partir del ingreso sin que el cliente retire el equipo, "
            "éste acepta que no podrá exigir al comercio su devolución. La firma de la presente planilla implica "
            "para el cliente su expresa <b>declaración jurada</b> de que el equipo es de su exclusiva pertenencia "
            "y fue adquirido de modo lícito, exhibiendo en este acto su DNI original."
        )
    else:
        texto_legal = (
            "El plazo de reparación aproximado es de <b>4 días hábiles</b> contados a partir de la fecha de la "
            "presente planilla y, a fin de retirar su equipo, el cliente deberá apersonarse en el local comercial "
            "con la copia de la misma. La garantía que se le otorgará al cliente será, sin excepción, de "
            "<b>30 días corridos</b> a partir del retiro de su equipo celular. Transcurridos los <b>90 días "
            "corridos</b> a partir de la entrega del equipo sin que el cliente lo haya retirado, éste acepta que "
            "no le podrá exigir al comercio la devolución del mismo, entendiéndose que —acaecido dicho plazo— "
            "ha hecho abandono voluntario de la cosa. La presente garantía <b>no abarca</b> la reparación de "
            "celulares que estuvieren mojados. Finalmente, la firma de la presente planilla implica para el "
            "cliente su expresa <b>declaración jurada</b> de que el equipo a ser reparado es de su exclusiva "
            "pertenencia y que fue adquirido de modo lícito, exhibiendo en este acto su DNI original."
        )

    story.append(Paragraph(texto_legal, s["legal"]))
    story.append(Spacer(1, 8*mm))
    story.extend(_bloque_firma(s))

    doc.build(story)
    filename = f"recepcion_{reparacion_id:04d}.pdf"
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── PDF: Certificado de garantía ──────────────────────────────────────────────

@router.get("/{reparacion_id}/certificado-garantia")
def certificado_garantia(
    reparacion_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    rep = _get_or_404(reparacion_id, session)
    local   = session.get(Local,   rep.local_id)
    usuario = session.get(Usuario, rep.usuario_id)

    # Buscar la fecha de entrega según estado
    estado_entrega = None
    if rep.estado == "ENTREGADO":
        estado_entrega = "ENTREGADO"
    elif rep.estado == "ENTREGADO_GARANTIA":
        estado_entrega = "ENTREGADO_GARANTIA"

    fecha_entrega = None
    if estado_entrega:
        mov = session.exec(
            select(MovimientoReparacion)
            .where(MovimientoReparacion.reparacion_id == reparacion_id)
            .where(MovimientoReparacion.estado_nuevo == estado_entrega)
            .order_by(MovimientoReparacion.fecha.desc())  # type: ignore
        ).first()
        if mov and mov.fecha:
            fecha_entrega = mov.fecha

    fecha_str = (
        fecha_entrega.astimezone(TZ_AR).strftime("%d/%m/%Y")
        if fecha_entrega else
        rep.fecha_ingreso.astimezone(TZ_AR).strftime("%d/%m/%Y")
        if rep.fecha_ingreso else "-"
    )
    local_str   = local.nombre   if local   else "-"
    usuario_str = usuario.nombre if usuario else "-"

    # ── Estilos ────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm,
    )
    W = A4[0] - 36*mm

    styles = getSampleStyleSheet()
    def style(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    titulo  = style("titulo", fontSize=13, fontName="Helvetica-Bold", alignment=1, spaceAfter=2)
    subtit  = style("sub",    fontSize=9,  alignment=1, spaceAfter=6)
    bold9   = style("b9",     fontSize=9,  fontName="Helvetica-Bold")
    normal9 = style("n9",     fontSize=9,  leading=12)
    small8  = style("s8",     fontSize=8,  leading=10)
    aviso   = style("aviso",  fontSize=9,  fontName="Helvetica-Bold")
    punteo  = style("punt",   fontSize=9,  leading=13)

    story = []

    # ── Encabezado ─────────────────────────────────────────────────────────────
    story.append(Paragraph("CERTIFICADO DE GARANTÍA", titulo))
    story.append(Paragraph(f"N° {reparacion_id:04d}  —  {local_str}  —  {fecha_str}", subtit))
    story.append(HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=5))

    # ── Datos del cliente y equipo ─────────────────────────────────────────────
    def fila(label, valor):
        return [Paragraph(f"<b>{label}</b>", bold9), Paragraph(valor or "-", normal9)]

    tabla_style = TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.black),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, colors.HexColor("#AAAAAA")),
    ])

    tbl_cliente = Table([
        fila("Cliente:",      rep.nombre_cliente),
        fila("Teléfono:",     rep.telefono_cliente),
        fila("DNI:",          rep.dni_cliente or "-"),
        fila("Atendido por:", usuario_str),
    ], colWidths=[W * 0.22, W * 0.78])
    tbl_cliente.setStyle(tabla_style)
    story.append(tbl_cliente)
    story.append(Spacer(1, 4*mm))

    tbl_equipo = Table([
        fila("Equipo:",   rep.celular),
        fila("Total:",    f"${rep.total:,}"),
        fila("Adelanto:", f"${rep.pago_parcial:,}"),
        fila("Restan pagar:",    f"${(rep.total or 0) - rep.pago_parcial:,}"),
    ], colWidths=[W * 0.22, W * 0.78])
    tbl_equipo.setStyle(tabla_style)
    story.append(tbl_equipo)
    story.append(Spacer(1, 6*mm))

    # ── Aviso garantía ─────────────────────────────────────────────────────────
    story.append(Paragraph(
        "IMPORTANTE: SR/A. CLIENTE: La presente garantía se extiende, sin excepción, "
        "por un plazo máximo de <b>30 días corridos</b> contados a partir de la fecha "
        "del presente certificado.-",
        aviso,
    ))
    story.append(Spacer(1, 6*mm))

    # ── Reparación realizada y observaciones ───────────────────────────────────
    dots = "\u00a0" * 2 + ("." * 110)
    story.append(Paragraph("<b>REPARACIÓN REALIZADA Y OBSERVACIONES:</b>", bold9))
    story.append(Spacer(1, 2*mm))
    for _ in range(5):
        story.append(Paragraph(dots, punteo))
    story.append(Spacer(1, 8*mm))

    # ── Fecha de retiro ────────────────────────────────────────────────────────
    story.append(Paragraph(
        "EQUIPO RETIRADO DE CONFORMIDAD EN FECHA: ………… / ………… / …………",
        bold9,
    ))
    story.append(Paragraph("(fecha de puño y letra por el cliente)", small8))
    story.append(Spacer(1, 8*mm))

    # ── Firma, aclaración y DNI ────────────────────────────────────────────────
    story.append(Paragraph(
        "FIRMA Y ACLARACIÓN DEL CLIENTE: " + "_" * 52,
        normal9,
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()

    filename = f"garantia_{reparacion_id:04d}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── PDF: Certificado de cancelación ──────────────────────────────────────────

@router.get("/{reparacion_id}/certificado-cancelacion")
def certificado_cancelacion(
    reparacion_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user),
):
    rep = _get_or_404(reparacion_id, session)
    if rep.estado != "CANCELADO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se puede generar el certificado de cancelación para reparaciones en estado CANCELADO")

    local   = session.get(Local,   rep.local_id)
    usuario = session.get(Usuario, rep.usuario_id)

    mov_cancelacion = session.exec(
        select(MovimientoReparacion)
        .where(MovimientoReparacion.reparacion_id == reparacion_id)
        .where(MovimientoReparacion.estado_nuevo == "CANCELADO")
        .order_by(MovimientoReparacion.fecha.desc())  # type: ignore
    ).first()

    monto_a_devolver = mov_cancelacion.monto_a_devolver if mov_cancelacion else 0
    fecha_cancelacion = (
        mov_cancelacion.fecha.astimezone(TZ_AR).strftime("%d/%m/%Y")
        if mov_cancelacion and mov_cancelacion.fecha else "-"
    )

    fecha_ingreso_str = rep.fecha_ingreso.astimezone(TZ_AR).strftime("%d/%m/%Y") if rep.fecha_ingreso else "-"
    local_str = local.nombre if local else "-"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=14*mm, bottomMargin=14*mm)
    W = A4[0] - 36*mm
    s = _pdf_styles()

    def fila(label, valor):
        return [Paragraph(f"<b>{label}</b>", s["bold9"]), Paragraph(valor or "-", s["normal9"])]

    story = []

    story.append(Paragraph("CERTIFICADO DE CANCELACIÓN DE REPARACIÓN", s["titulo"]))
    story.append(Paragraph(f"N° {reparacion_id:04d}  —  {local_str}  —  {fecha_cancelacion}", s["subtitulo"]))
    story.append(HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=5))

    tbl_cliente = Table([
        fila("Cliente:",        rep.nombre_cliente),
        fila("Teléfono:",       rep.telefono_cliente),
        fila("DNI:",            rep.dni_cliente or "-"),
        fila("Fecha ingreso:",  fecha_ingreso_str),
    ], colWidths=[W * 0.25, W * 0.75])
    tbl_cliente.setStyle(_tabla_style())
    story.append(tbl_cliente)
    story.append(Spacer(1, 4*mm))

    tbl_equipo = Table([
        fila("Equipo:",          rep.celular),
        fila("Descripción:",     rep.descripcion or "-"),
        fila("Pagado por cliente:", f"${rep.pago_parcial:,}"),
        fila("Monto a devolver:", f"${monto_a_devolver:,}"),
        fila("Retención local:", f"${rep.pago_parcial - (monto_a_devolver or 0):,}"),
    ], colWidths=[W * 0.25, W * 0.75])
    tbl_equipo.setStyle(_tabla_style())
    story.append(tbl_equipo)
    story.append(Spacer(1, 6*mm))

    if mov_cancelacion and mov_cancelacion.observaciones:
        story.append(Paragraph(f"<b>Motivo de cancelación:</b> {mov_cancelacion.observaciones}", s["normal9"]))
        story.append(Spacer(1, 5*mm))

    texto_legal = (
        f"El/La abajo firmante declara haber recibido de conformidad la suma de "
        f"<b>${monto_a_devolver:,}</b> en concepto de devolución parcial del monto abonado "
        f"por la reparación del equipo detallado, y presta su conformidad con la cancelación "
        f"del servicio. Se deja constancia que el equipo fue retirado en buen estado."
    )
    story.append(Paragraph(texto_legal, s["legal"]))
    story.append(Spacer(1, 10*mm))

    story.extend(_bloque_firma(s))

    doc.build(story)
    filename = f"cancelacion_{reparacion_id:04d}.pdf"
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
