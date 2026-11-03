from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Optional

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlmodel import Session, SQLModel, select, func

from app.db.session import get_session
from app.db.models import IngresoDinero, Usuario
from app.api.deps import require_admin, UsuarioActual
from app.api.funciones.fechas import TZ_AR
from app.api.funciones.gastos_funciones import dec, texto_o_none


router = APIRouter(prefix="/ingresos-dinero", tags=["Ingresos de dinero"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class IngresoDineroCreate(SQLModel):
    monto: Decimal
    descripcion: str
    fecha: Optional[date] = None   # por defecto, hoy (hora argentina)
    usuario_id: Optional[int] = None


class IngresoDineroUpdate(SQLModel):
    monto: Optional[Decimal] = None
    descripcion: Optional[str] = None
    fecha: Optional[date] = None


class IngresoDineroRead(SQLModel):
    id: int
    monto: Decimal
    descripcion: str
    fecha: date
    usuario_id: int


class IngresoDineroTotales(SQLModel):
    total: Decimal
    cantidad: int


# ── Logica de negocio ─────────────────────────────────────────────────────────

def _normalizar_y_validar(data: dict) -> dict:
    """Valida un estado logico completo del ingreso (sirve para crear y para
    actualizar, mergeando el payload sobre el registro existente)."""
    if data.get("monto") is None:
        raise HTTPException(422, "Falta el 'monto' del ingreso")
    monto = dec(data["monto"])
    if monto <= 0:
        raise HTTPException(422, "El monto tiene que ser mayor a 0")

    descripcion = texto_o_none(data.get("descripcion"))
    if not descripcion:
        raise HTTPException(422, "El ingreso necesita una descripción")

    fecha = data.get("fecha") or datetime.now(TZ_AR).date()

    return {"monto": monto, "descripcion": descripcion, "fecha": fecha}


def _guardar(session: Session, ingreso: IngresoDinero) -> IngresoDineroRead:
    session.add(ingreso)
    session.commit()
    session.refresh(ingreso)
    return IngresoDineroRead(**ingreso.model_dump())


def _aplicar_filtros(query, fecha_desde, fecha_hasta):
    if fecha_desde:
        query = query.where(IngresoDinero.fecha >= fecha_desde)  # type: ignore
    if fecha_hasta:
        query = query.where(IngresoDinero.fecha <= fecha_hasta)  # type: ignore
    return query


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=IngresoDineroRead, status_code=status.HTTP_201_CREATED)
def crear_ingreso_dinero(
    payload: IngresoDineroCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    campos = _normalizar_y_validar(payload.model_dump())

    usuario_id = payload.usuario_id or current_user.usuario_id
    if payload.usuario_id is not None and not session.get(Usuario, payload.usuario_id):
        raise HTTPException(404, "Usuario no existe")

    return _guardar(session, IngresoDinero(**campos, usuario_id=usuario_id))


@router.get("/", response_model=list[IngresoDineroRead])
def listar_ingresos_dinero(
    fecha_desde: Optional[date] = Query(default=None),
    fecha_hasta: Optional[date] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    query = _aplicar_filtros(select(IngresoDinero), fecha_desde, fecha_hasta)
    # Desempate por id: los ingresos del mismo dia no cambian de lugar entre paginas.
    query = query.order_by(IngresoDinero.fecha.desc(), IngresoDinero.id.desc()).offset(offset).limit(limit)  # type: ignore
    return [IngresoDineroRead(**i.model_dump()) for i in session.exec(query).all()]


@router.get("/totales", response_model=IngresoDineroTotales)
def totales_ingresos_dinero(
    fecha_desde: Optional[date] = Query(default=None),
    fecha_hasta: Optional[date] = Query(default=None),
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    query = select(
        func.coalesce(func.sum(IngresoDinero.monto), 0),
        func.count(IngresoDinero.id),  # type: ignore
    )
    query = _aplicar_filtros(query, fecha_desde, fecha_hasta)
    total, cantidad = session.exec(query).one()
    return IngresoDineroTotales(total=Decimal(total), cantidad=cantidad)


@router.get("/excel")
def ingresos_dinero_excel(
    fecha_desde: date = Query(description="Inicio del rango (YYYY-MM-DD)"),
    fecha_hasta: date = Query(description="Fin del rango (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    if fecha_desde > fecha_hasta:
        raise HTTPException(422, "La fecha 'desde' no puede ser posterior a 'hasta'")

    query = _aplicar_filtros(
        select(IngresoDinero, Usuario.nombre).join(Usuario, Usuario.usuario_id == IngresoDinero.usuario_id),  # type: ignore
        fecha_desde, fecha_hasta,
    ).order_by(IngresoDinero.fecha, IngresoDinero.id)  # type: ignore
    filas = list(session.exec(query).all())

    xlsx_bytes = _build_excel(filas, fecha_desde, fecha_hasta)
    nombre = f"ingresos_dinero_{fecha_desde.isoformat()}_{fecha_hasta.isoformat()}.xlsx"
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{ingreso_id}", response_model=IngresoDineroRead)
def obtener_ingreso_dinero(
    ingreso_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    ingreso = session.get(IngresoDinero, ingreso_id)
    if not ingreso:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    return IngresoDineroRead(**ingreso.model_dump())


@router.patch("/{ingreso_id}", response_model=IngresoDineroRead)
def actualizar_ingreso_dinero(
    ingreso_id: int,
    payload: IngresoDineroUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    ingreso = session.get(IngresoDinero, ingreso_id)
    if not ingreso:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")

    estado = ingreso.model_dump()
    estado.update(payload.model_dump(exclude_unset=True))
    for campo, valor in _normalizar_y_validar(estado).items():
        setattr(ingreso, campo, valor)
    return _guardar(session, ingreso)


@router.delete("/{ingreso_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_ingreso_dinero(
    ingreso_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    ingreso = session.get(IngresoDinero, ingreso_id)
    if not ingreso:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    session.delete(ingreso)
    session.commit()


# ── Excel ─────────────────────────────────────────────────────────────────────

_ENCABEZADOS = ["FECHA", "DESCRIPCIÓN", "USUARIO", "MONTO"]
_ANCHOS = [14.5, 45, 18, 16]
_COL_MONTO = 4
_FILA_ENCABEZADO = 3

_ARIAL = "Arial"
_THIN = Side(style="thin")
_BORDE = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_FILL_TITULO = PatternFill("solid", fgColor="E2EFDA")
_FILL_GRIS = PatternFill("solid", fgColor="D9D9D9")
_CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)
_FMT_IMPORTE = "#,##0.00"


def _build_excel(filas: list, fecha_desde: date, fecha_hasta: date) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INGRESOS"  # type: ignore

    ultima_col = len(_ENCABEZADOS)

    # Titulo (A1:D2)
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=ultima_col)
    c = ws.cell(
        row=1, column=1,
        value=f"INGRESOS DE DINERO {fecha_desde.strftime('%d/%m/%Y')} – {fecha_hasta.strftime('%d/%m/%Y')}",
    )
    c.font = Font(name=_ARIAL, size=16, bold=True)
    c.fill = _FILL_TITULO
    c.alignment = _CENTRO

    for col, texto in enumerate(_ENCABEZADOS, start=1):
        c = ws.cell(row=_FILA_ENCABEZADO, column=col, value=texto)
        c.font = Font(name=_ARIAL, size=10, bold=True)
        c.fill = _FILL_GRIS
        c.alignment = _CENTRO
        c.border = _BORDE

    primera = _FILA_ENCABEZADO + 1
    fila = primera
    for ingreso, usuario_nombre in filas:
        valores = [ingreso.fecha, ingreso.descripcion, usuario_nombre, float(ingreso.monto)]
        for col, v in enumerate(valores, start=1):
            c = ws.cell(row=fila, column=col, value=v)
            c.font = Font(name=_ARIAL, size=10)
            c.border = _BORDE
            if col == 1:
                c.number_format = "d/mm/yyyy"
                c.alignment = Alignment(horizontal="center")
            elif col == _COL_MONTO:
                c.number_format = _FMT_IMPORTE
        fila += 1

    # Fila de totales
    ws.cell(row=fila, column=1, value="TOTAL")
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=_COL_MONTO - 1)
    for col in range(1, ultima_col + 1):
        c = ws.cell(row=fila, column=col)
        c.font = Font(name=_ARIAL, size=10, bold=True)
        c.fill = _FILL_GRIS
        c.border = _BORDE
        if col == 1:
            c.alignment = _CENTRO
        if col == _COL_MONTO:
            letra = get_column_letter(col)
            c.value = f"=SUM({letra}{primera}:{letra}{fila - 1})" if fila > primera else 0
            c.number_format = _FMT_IMPORTE

    for col, ancho in enumerate(_ANCHOS, start=1):
        ws.column_dimensions[get_column_letter(col)].width = ancho
    ws.freeze_panes = f"A{primera}"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
