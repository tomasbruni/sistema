"""
Inventario físico de accesorios.

Flujo:
1. Se baja la planilla desde /stock/export-por-exclusion (ID | Accesorio | Sistema | Fisico).
2. POST /inventarios/reporte  -> Excel de discrepancias valorizado (no toca la base).
3. POST /inventarios          -> aplica la planilla: un movimiento AJUSTE por producto con
                                 diferencia, agrupado bajo un registro Inventario.

El ajuste es delta = Fisico - Sistema (del Excel), sumado al stock actual: así se
conservan las ventas/transferencias registradas entre el conteo y la carga.
"""
from datetime import date, datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import exc
from sqlmodel import Session, SQLModel, func, select

from app.api.deps import UsuarioActual, require_admin
from app.api.funciones.fechas import TZ_AR, end_of_day, start_of_day
from app.api.funciones.inventario import (
    build_registro_excel,
    build_reporte_excel,
    calcular_discrepancias,
    parsear_planilla,
)
from app.api.funciones.movimientos_stock import aplicar_movimiento_stock
from app.db.models import (
    Accesorio,
    Inventario,
    Local,
    MovimientoStock,
    StockAccesorio,
    TipoMovimiento,
    Usuario,
)
from app.db.session import get_session


router = APIRouter(
    prefix="/inventarios",
    tags=["INVENTARIOS"],
    dependencies=[Depends(require_admin)],
)

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ── Schemas ──────────────────────────────────────────────────────────────────

class InventarioResumen(SQLModel):
    inventario_id: int
    fecha: Optional[datetime] = None
    local_id: int
    local_nombre: Optional[str] = None
    usuario_id: Optional[int] = None
    usuario_nombre: Optional[str] = None
    observaciones: Optional[str] = None
    sobrante_estimado: int
    cantidad_ajustes: int


class AjusteInventario(SQLModel):
    movimiento_id: int
    accesorio_id: int
    accesorio_nombre: str
    stock_anterior: Optional[int] = None
    cantidad: int
    stock_nuevo: Optional[int] = None


class InventarioDetalle(InventarioResumen):
    ajustes: list[AjusteInventario]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _xlsx_response(contenido: bytes, nombre: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(contenido),
        media_type=_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


def _fecha_ar(fecha: Optional[datetime]) -> str:
    if fecha is None:
        return ""
    return fecha.astimezone(TZ_AR).strftime("%d/%m/%Y %H:%M")


def _query_resumen():
    cantidad = (
        select(func.count(MovimientoStock.id))  # type: ignore
        .where(MovimientoStock.inventario_id == Inventario.inventario_id)
        .correlate(Inventario)
        .scalar_subquery()
    )
    return (
        select(Inventario, Local.nombre, Usuario.nombre, cantidad)  # type: ignore
        .join(Local, Inventario.local_id == Local.local_id)  # type: ignore
        .outerjoin(Usuario, Inventario.usuario_id == Usuario.usuario_id)  # type: ignore
    )


def _a_resumen(inv: Inventario, local_nombre, usuario_nombre, cantidad) -> InventarioResumen:
    return InventarioResumen(
        inventario_id=inv.inventario_id,  # type: ignore
        fecha=inv.fecha,
        local_id=inv.local_id,
        local_nombre=local_nombre,
        usuario_id=inv.usuario_id,
        usuario_nombre=usuario_nombre,
        observaciones=inv.observaciones,
        sobrante_estimado=inv.sobrante_estimado,
        cantidad_ajustes=cantidad or 0,
    )


def _obtener_detalle(session: Session, inventario_id: int) -> InventarioDetalle:
    row = session.exec(
        _query_resumen().where(Inventario.inventario_id == inventario_id)
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Inventario {inventario_id} no encontrado")

    movimientos = session.exec(
        select(MovimientoStock, Accesorio.nombre)  # type: ignore
        .join(Accesorio, MovimientoStock.accesorio_id == Accesorio.accesorio_id)  # type: ignore
        .where(MovimientoStock.inventario_id == inventario_id)
        .order_by(Accesorio.nombre)  # type: ignore
    ).all()

    resumen = _a_resumen(*row)
    return InventarioDetalle(
        **resumen.model_dump(),
        ajustes=[
            AjusteInventario(
                movimiento_id=mov.id,  # type: ignore
                accesorio_id=mov.accesorio_id,
                accesorio_nombre=nombre,
                stock_anterior=mov.stock_anterior,
                cantidad=mov.cantidad,
                stock_nuevo=mov.stock_nuevo,
            )
            for mov, nombre in movimientos
        ],
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/reporte")
async def reporte_inventario(
    archivo: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Analiza la planilla completa y devuelve el Excel de discrepancias. No modifica nada."""
    filas = parsear_planilla(await archivo.read())
    resultado = calcular_discrepancias(session, filas)

    meta = [
        ("Archivo:", archivo.filename or ""),
        ("Fecha de generación:", datetime.now(TZ_AR).strftime("%d/%m/%Y %H:%M")),
    ]
    contenido = build_reporte_excel(resultado, meta)
    hoy = date.today().strftime("%Y%m%d")
    return _xlsx_response(contenido, f"reporte_inventario_{hoy}.xlsx")


@router.post("", status_code=status.HTTP_201_CREATED)
async def aplicar_inventario(
    archivo: UploadFile = File(...),
    local_id: int = Form(...),
    observaciones: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    """
    Aplica la planilla completa al stock del local: un movimiento AJUSTE por cada
    producto con Fisico != Sistema (Fisico vacío = 0), con cantidad = Fisico - Sistema.
    Todo en una transacción; ante cualquier error no se aplica nada.
    """
    local = session.get(Local, local_id)
    if not local:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Local {local_id} no encontrado")

    filas = parsear_planilla(await archivo.read())
    resultado = calcular_discrepancias(session, filas)

    try:
        # Todas las filas de stock del Excel en una sola query, con lock.
        # El ORDER BY fija el orden de los locks y evita deadlocks con ventas concurrentes.
        # Una venta trae los productos [C, A] y bloquea C primero.
        # El inventario bloquea A, B, C en orden ascendente. Toma A y queda esperando C.
        # La venta pide A, que tiene el inventario.
        # Los dos se esperan entre sí. Esto pasa porque ventas no toma ningun orden pero es muy improbable
        ids = [f.accesorio_id for f in filas]
        stocks = {
            s.accesorio_id: s
            for s in session.exec(
                select(StockAccesorio)
                .where(StockAccesorio.local_id == local_id)
                .where(StockAccesorio.accesorio_id.in_(ids))  # type: ignore
                .order_by(StockAccesorio.accesorio_id)  # type: ignore
                .with_for_update()
            ).all()
        }

        sin_stock = [f"Fila {f.fila_excel}: ID {f.accesorio_id}" for f in filas if f.accesorio_id not in stocks]
        if sin_stock:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Estos productos no tienen stock registrado en {local.nombre}. "
                "¿Elegiste el local correcto?\n" + "\n".join(sin_stock),
            )

        inventario = Inventario(
            local_id=local_id,
            usuario_id=current_user.usuario_id,
            observaciones=(observaciones or "").strip() or None,
            sobrante_estimado=resultado.sobrante_estimado_total,
        )  # type: ignore
        session.add(inventario)
        session.flush()  # obtenemos inventario_id

        for d in resultado.discrepancias:
            aplicar_movimiento_stock(
                session, stocks[d.accesorio_id],
                tipo_movimiento=TipoMovimiento.AJUSTE,
                cantidad=d.diferencia,
                motivo=f"Inventario #{inventario.inventario_id} (Excel: {d.sistema} → {d.fisico})",
                usuario_id=current_user.usuario_id,
                inventario_id=inventario.inventario_id,
                permitir_negativo=True,
            )

        session.commit()
        session.refresh(inventario)

        return {
            "mensaje": "Inventario aplicado",
            "inventario_id": inventario.inventario_id,
            "fecha": inventario.fecha,
            "local_id": local_id,
            "local_nombre": local.nombre,
            "productos_contados": resultado.productos_contados,
            "sin_diferencias": resultado.sin_diferencias,
            "cantidad_ajustes": len(resultado.discrepancias),
            "faltan": sum(d.faltan for d in resultado.discrepancias),
            "sobran": sum(d.sobran for d in resultado.discrepancias),
            "sobrante_estimado": inventario.sobrante_estimado,
        }

    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error de integridad: {e.orig}")
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error inesperado: {str(e)}")


@router.get("", response_model=list[InventarioResumen])
def listar_inventarios(
    local_id: Optional[int] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    session: Session = Depends(get_session),
):
    stmt = _query_resumen()
    if local_id is not None:
        stmt = stmt.where(Inventario.local_id == local_id)
    if fecha_desde is not None:
        stmt = stmt.where(Inventario.fecha >= start_of_day(fecha_desde))  # type: ignore
    if fecha_hasta is not None:
        stmt = stmt.where(Inventario.fecha <= end_of_day(fecha_hasta))  # type: ignore
    stmt = stmt.order_by(Inventario.fecha.desc())  # type: ignore
    return [_a_resumen(*row) for row in session.exec(stmt).all()]


@router.get("/{inventario_id}", response_model=InventarioDetalle)
def obtener_inventario(
    inventario_id: int,
    session: Session = Depends(get_session),
):
    return _obtener_detalle(session, inventario_id)


@router.get("/{inventario_id}/excel")
def descargar_inventario_excel(
    inventario_id: int,
    session: Session = Depends(get_session),
):
    """Registro del inventario aplicado: todos sus movimientos AJUSTE."""
    det = _obtener_detalle(session, inventario_id)
    meta: list[tuple[str, object]] = [
        ("Inventario:", f"#{det.inventario_id}"),
        ("Fecha:", _fecha_ar(det.fecha)),
        ("Local:", det.local_nombre or ""),
        ("Usuario:", det.usuario_nombre or ""),
    ]
    if det.observaciones:
        meta.append(("Observaciones:", det.observaciones))
    meta += [
        ("Ajustes:", det.cantidad_ajustes),
        ("Sobrante estimado:", det.sobrante_estimado),
    ]
    contenido = build_registro_excel(
        [(a.accesorio_id, a.accesorio_nombre, a.stock_anterior, a.cantidad, a.stock_nuevo) for a in det.ajustes],
        meta,
    )
    return _xlsx_response(contenido, f"inventario_{det.inventario_id}.xlsx")
