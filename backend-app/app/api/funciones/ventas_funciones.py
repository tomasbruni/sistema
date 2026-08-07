from collections import defaultdict
from sqlmodel import Session, select

from app.db.models import (
    Accesorio, Celular, Chip, MarcaCelular, ModeloCelular,
    DetalleVentaAccesorio, DetalleVentaCelular, DetalleVentaChip,
    PagoVenta, Venta,
)


def get_pagos_by_venta(session: Session, venta_ids: list[int]) -> dict[int, list[PagoVenta]]:
    """Devuelve un dict {venta_id: [PagoVenta]} para los venta_ids dados."""
    result: dict[int, list[PagoVenta]] = defaultdict(list)
    if not venta_ids:
        return result
    for p in session.exec(
        select(PagoVenta).where(PagoVenta.venta_id.in_(venta_ids))  # type: ignore
    ).all():
        result[p.venta_id].append(p)
    return result


def get_detalles_by_venta(session: Session, venta_ids: list[int]) -> dict[int, list[dict]]:
    """
    Dado una lista de venta_ids, devuelve un dict {venta_id: [detalles]}
    con todos los campos de cada detalle (accesorios, celulares y chips).

    Cada detalle tiene:
        tipo_producto   : "ACCESORIO" | "CELULAR" | "CHIP"
        nombre_producto : str
        codigo          : str | None  (SKU / IMEI / número de serie)
        precio_lista    : int
        precio_unitario : int   SIEMPRE positivo (es un precio, no un movimiento)
        cantidad        : int   SIEMPRE positiva
        comision_importe: int   ya firmado: negativo en devoluciones
        es_devolucion   : bool
        subtotal        : int   ya firmado: -(precio_unitario * cantidad) en devoluciones

    Regla para los consumidores: **para agregar/sumar usar `subtotal`; para listar
    línea por línea usar `precio_unitario` y `cantidad`.** Las devoluciones se
    guardan con los importes de los detalles en positivo (a diferencia de
    `PagoVenta.importe`, `Venta.monto_total` y `comision_importe`, que sí van
    firmados), así que sumar `precio_unitario * cantidad` cuenta una devolución
    como si fuera una venta. `subtotal` y `es_devolucion` evitan que cada reporte
    tenga que volver a resolver el signo por su cuenta.
    """
    result: dict[int, list[dict]] = defaultdict(list)

    if not venta_ids:
        return result

    # Tipo de cada venta, para firmar los subtotales de las devoluciones
    es_devolucion_by_venta = {
        vid: (tipo or "").strip().upper() == "DEVOLUCION"
        for vid, tipo in session.exec(
            select(Venta.venta_id, Venta.tipo).where(Venta.venta_id.in_(venta_ids))  # type: ignore
        ).all()
    }

    def _firmar(venta_id: int, precio_unitario: int, cantidad: int) -> tuple[bool, int]:
        es_dev   = es_devolucion_by_venta.get(venta_id, False)
        subtotal = precio_unitario * cantidad
        return es_dev, -subtotal if es_dev else subtotal

    # Accesorios
    for det, acc in session.exec(
        select(DetalleVentaAccesorio, Accesorio)
        .join(Accesorio, DetalleVentaAccesorio.accesorio_id == Accesorio.accesorio_id)  # type: ignore
        .where(DetalleVentaAccesorio.venta_id.in_(venta_ids))  # type: ignore
    ).all():
        es_dev, subtotal = _firmar(det.venta_id, det.precio_unitario, det.cantidad)
        result[det.venta_id].append({
            "tipo_producto":    "ACCESORIO",
            "nombre_producto":  acc.nombre,
            "codigo":           str(acc.accesorio_id),
            "precio_lista":     det.precio_lista,
            "precio_unitario":  det.precio_unitario,
            "cantidad":         det.cantidad,
            "comision_importe": det.comision_importe,
            "es_devolucion":    es_dev,
            "subtotal":         subtotal,
        })

    # Celulares
    for det, cel, modelo, marca in session.exec(
        select(DetalleVentaCelular, Celular, ModeloCelular, MarcaCelular)
        .join(Celular,       DetalleVentaCelular.celular_id        == Celular.celular_id)             # type: ignore
        .join(ModeloCelular, Celular.modelo_celular_id             == ModeloCelular.modelo_celular_id)  # type: ignore
        .join(MarcaCelular,  Celular.marca_celular_id              == MarcaCelular.marca_celular_id)   # type: ignore
        .where(DetalleVentaCelular.venta_id.in_(venta_ids))  # type: ignore
    ).all():
        es_dev, subtotal = _firmar(det.venta_id, det.precio_unitario, 1)
        result[det.venta_id].append({
            "tipo_producto":    "CELULAR",
            "nombre_producto":  f"{marca.nombre} {modelo.nombre}",
            "codigo":           cel.imei,
            "precio_lista":     det.precio_lista,
            "precio_unitario":  det.precio_unitario,
            "cantidad":         1,
            "comision_importe": det.comision_importe,
            "es_devolucion":    es_dev,
            "subtotal":         subtotal,
        })

    # Chips
    for det, chip in session.exec(
        select(DetalleVentaChip, Chip)
        .join(Chip, DetalleVentaChip.chip_id == Chip.chip_id)  # type: ignore
        .where(DetalleVentaChip.venta_id.in_(venta_ids))  # type: ignore
    ).all():
        es_dev, subtotal = _firmar(det.venta_id, det.precio_unitario, 1)
        result[det.venta_id].append({
            "tipo_producto":    "CHIP",
            "nombre_producto":  f"Chip {chip.compania}",
            "codigo":           chip.numero_serie,
            "precio_lista":     det.precio_lista,
            "precio_unitario":  det.precio_unitario,
            "cantidad":         1,
            "comision_importe": det.comision_importe,
            "es_devolucion":    es_dev,
            "subtotal":         subtotal,
        })

    return result
