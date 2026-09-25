from datetime import date
from typing import Optional

from sqlalchemy import and_, or_

from app.db.models import Gasto, TipoGasto
from app.api.funciones.fechas import start_of_day, end_of_day


def primer_dia_mes(d: date) -> date:
    return d.replace(day=1)


def condicion_rango_gastos(desde: Optional[date], hasta: Optional[date]):
    """Condicion para traer los gastos de un rango de fechas.

    - REAL: por `fecha`.
    - FACTURA: por `periodo` de imputacion, no por fecha de emision. Entra si el mes
      del periodo se superpone con el rango (periodo es siempre el dia 1 del mes).
    Un extremo en None no se aplica."""
    cond_real = [Gasto.tipo == TipoGasto.REAL]
    cond_factura = [Gasto.tipo == TipoGasto.FACTURA]
    if desde:
        cond_real.append(Gasto.fecha >= start_of_day(desde))          # type: ignore
        cond_factura.append(Gasto.periodo >= primer_dia_mes(desde))   # type: ignore
    if hasta:
        cond_real.append(Gasto.fecha <= end_of_day(hasta))            # type: ignore
        cond_factura.append(Gasto.periodo <= hasta)                   # type: ignore
    return or_(and_(*cond_real), and_(*cond_factura))
