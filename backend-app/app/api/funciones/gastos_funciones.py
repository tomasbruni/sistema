from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import calendar
import re

from fastapi import HTTPException
from sqlalchemy import and_, or_

from app.db.models import Gasto, TipoGasto
from app.api.funciones.fechas import start_of_day, end_of_day


CERO = Decimal("0.00")
DOS_DECIMALES = Decimal("0.01")


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


# ── Helpers de comprobantes (libros IVA compras y ventas) ────────────────────

def dec(v) -> Decimal:
    return CERO if v is None else Decimal(v).quantize(DOS_DECIMALES, ROUND_HALF_UP)


def texto_o_none(v) -> Optional[str]:
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def normalizar_comprobante(v) -> Optional[str]:
    """Punto de venta / numero de comprobante en una forma unica, para que el control
    de duplicados y el Excel vean el mismo valor: sin ceros a la izquierda en cada
    tramo numerico separado por guion ("00005" -> "5", "07008-00041244" -> "7008-41244").
    Si algun tramo no es puramente numerico, queda como vino (solo sin espacios)."""
    texto = texto_o_none(v)
    if texto is None:
        return None
    tramos = [t.strip() for t in texto.split("-")]
    if all(re.fullmatch(r"[0-9]+", t) for t in tramos):
        return "-".join(str(int(t)) for t in tramos)
    return texto


def rango_mes(periodo: str) -> tuple[date, date]:
    """'YYYY-MM' -> (primer dia, ultimo dia) del mes. 422 si el formato es invalido."""
    m = re.fullmatch(r"(\d{4})-(\d{2})", periodo)
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise HTTPException(422, "'periodo' debe tener formato YYYY-MM")
    anio, mes = int(m.group(1)), int(m.group(2))
    return date(anio, mes, 1), date(anio, mes, calendar.monthrange(anio, mes)[1])
