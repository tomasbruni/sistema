"""Cálculos de ingresos de un local por período.

Cada cálculo es una función independiente (se puede usar suelta para un reporte
específico) y `resumen_ventas` las combina para un reporte general.

Todas aceptan un período opcional (`fecha_desde` / `fecha_hasta`, en fecha AR) y un
`local_id` opcional (None = todos los locales). Los montos son enteros (pesos),
igual que en el resto del sistema.

Convenciones:
- El período se filtra por `Venta.fecha_ingreso` (los pagos no tienen fecha propia).
- Las devoluciones se guardan con `importe` negativo, así que sumar los pagos ya
  las descuenta; no hay que tratarlas aparte.
- Electrónico = medio de pago distinto de EFECTIVO.
- Los tres netos comparten el mismo scan pagos↔ventas: se calculan juntos en una
  sola query (`netos_ventas`) y los helpers individuales delegan en ella.
"""

from typing import Optional
from datetime import date

from sqlmodel import Session, select, func
from sqlalchemy import case

from app.db.models import PagoVenta, Venta, EgresoCaja
from app.api.funciones.fechas import start_of_day, end_of_day


# ── Filtros / helpers internos ────────────────────────────────────────────────

def _es_efectivo_sql():
    """Predicado SQL 'el pago es en efectivo' (tolerante a espacios / mayúsculas)."""
    return func.upper(func.trim(PagoVenta.medio_de_pago)) == "EFECTIVO"


def _filtro_periodo_local(stmt, columna_fecha, fecha_desde, fecha_hasta, columna_local, local_id):
    if fecha_desde is not None:
        stmt = stmt.where(columna_fecha >= start_of_day(fecha_desde))
    if fecha_hasta is not None:
        stmt = stmt.where(columna_fecha <= end_of_day(fecha_hasta))
    if local_id is not None:
        stmt = stmt.where(columna_local == local_id)
    return stmt


def _iva_incluido(monto: int) -> int:
    """IVA contenido en un importe con IVA incluido (alícuota 21%): monto * 21 / 121."""
    return round(monto * 21 / 121)


# ── Núcleo: los tres netos en una sola query ──────────────────────────────────

def netos_ventas(session: Session, fecha_desde=None, fecha_hasta=None, local_id=None) -> dict:
    """Los tres netos del período en una sola pasada (comparten el scan pagos↔ventas).

    Devuelve {'neto_ventas', 'neto_efectivo', 'neto_electronico'}. Las devoluciones
    (importe negativo) restan solas."""
    efectivo = _es_efectivo_sql()
    stmt = (
        select(
            func.coalesce(func.sum(PagoVenta.importe), 0),
            func.coalesce(func.sum(case((efectivo, PagoVenta.importe), else_=0)), 0),
            func.coalesce(func.sum(case((efectivo, 0), else_=PagoVenta.importe)), 0),
        )
        .join(Venta, PagoVenta.venta_id == Venta.venta_id)  # type: ignore
    )
    stmt = _filtro_periodo_local(stmt, Venta.fecha_ingreso, fecha_desde, fecha_hasta, Venta.local_id, local_id)
    neto, efec, elec = session.exec(stmt).one()
    return {
        "neto_ventas": int(neto),
        "neto_efectivo": int(efec),
        "neto_electronico": int(elec),
    }


# ── Cálculos individuales (delegan en netos_ventas) ───────────────────────────

def neto_ventas(session, fecha_desde=None, fecha_hasta=None, local_id=None) -> int:
    """Suma de todos los pagos del período (las devoluciones, negativas, restan)."""
    return netos_ventas(session, fecha_desde, fecha_hasta, local_id)["neto_ventas"]


def neto_efectivo(session, fecha_desde=None, fecha_hasta=None, local_id=None) -> int:
    """Suma de pagos en efectivo del período (las devoluciones restan)."""
    return netos_ventas(session, fecha_desde, fecha_hasta, local_id)["neto_efectivo"]


def neto_electronico(session, fecha_desde=None, fecha_hasta=None, local_id=None) -> int:
    """Suma de pagos con medio distinto de efectivo del período (las devoluciones restan)."""
    return netos_ventas(session, fecha_desde, fecha_hasta, local_id)["neto_electronico"]


def total_egresos(session, fecha_desde=None, fecha_hasta=None, local_id=None) -> int:
    """Suma de egresos de caja del período. Salen del efectivo."""
    stmt = select(func.coalesce(func.sum(EgresoCaja.monto), 0))
    stmt = _filtro_periodo_local(stmt, EgresoCaja.fecha, fecha_desde, fecha_hasta, EgresoCaja.local_id, local_id)
    return int(session.exec(stmt).one())


def total_ventas(session, fecha_desde=None, fecha_hasta=None, local_id=None) -> int:
    """Neto de ventas menos egresos de caja (los egresos salen del efectivo)."""
    return (
        neto_ventas(session, fecha_desde, fecha_hasta, local_id)
        - total_egresos(session, fecha_desde, fecha_hasta, local_id)
    )


def total_efectivo(session, fecha_desde=None, fecha_hasta=None, local_id=None) -> int:
    """Neto de efectivo menos egresos de caja."""
    return (
        neto_efectivo(session, fecha_desde, fecha_hasta, local_id)
        - total_egresos(session, fecha_desde, fecha_hasta, local_id)
    )


def iva_en_contra(session, fecha_desde=None, fecha_hasta=None, local_id=None) -> int:
    """IVA débito: el IVA contenido en el neto electrónico (IVA incluido, 21/121)."""
    return _iva_incluido(neto_electronico(session, fecha_desde, fecha_hasta, local_id))


# ── Reporte general (todas juntas) ────────────────────────────────────────────

def resumen_ventas(session, fecha_desde=None, fecha_hasta=None, local_id=None) -> dict:
    """Todos los cálculos juntos en 2 queries: los netos (una pasada) y los egresos."""
    netos = netos_ventas(session, fecha_desde, fecha_hasta, local_id)
    egresos = total_egresos(session, fecha_desde, fecha_hasta, local_id)
    return {
        **netos,
        "total_egresos": egresos,
        "total_ventas": netos["neto_ventas"] - egresos,
        "total_efectivo": netos["neto_efectivo"] - egresos,
        "iva_en_contra": _iva_incluido(netos["neto_electronico"]),
    }
