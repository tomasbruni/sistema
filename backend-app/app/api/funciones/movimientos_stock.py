from typing import Optional
from fastapi import HTTPException, status
from sqlmodel import Session

from app.db.models import MovimientoStock, StockAccesorio, TipoMovimiento


def aplicar_movimiento_stock(
    session: Session,
    stock: StockAccesorio,
    *,
    tipo_movimiento: TipoMovimiento,
    cantidad: int,
    usuario_id: Optional[int] = None,
    motivo: Optional[str] = None,
    venta_id: Optional[int] = None,
    ingreso_lote_id: Optional[int] = None,
    transferencia_id: Optional[int] = None,
    pedido_online_id: Optional[int] = None,
) -> MovimientoStock:
    """
    Aplica un delta sobre una fila de stock y registra el MovimientoStock
    con los snapshots stock_anterior / stock_nuevo.

    IMPORTANTE:
    - `stock` debe haberse obtenido con .with_for_update() (o ser una fila
      recién creada en esta transacción); si no, los snapshots pueden quedar
      inconsistentes bajo concurrencia.
    - `cantidad` es el delta con signo: positivo suma, negativo resta.
    - NO hace commit; el caller maneja la transacción.
    """
    stock_anterior = stock.cantidad
    stock_nuevo = stock_anterior + cantidad

    # Red de seguridad: los callers validan antes con mensajes específicos
    if stock_nuevo < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente. Disponible: {stock_anterior}, movimiento: {cantidad}"
        )

    stock.cantidad = stock_nuevo

    movimiento = MovimientoStock(
        accesorio_id=stock.accesorio_id,
        local_id=stock.local_id,
        tipo_movimiento=tipo_movimiento,
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_nuevo=stock_nuevo,
        motivo=motivo,
        usuario_id=usuario_id,
        venta_id=venta_id,
        ingreso_lote_id=ingreso_lote_id,
        transferencia_id=transferencia_id,
        pedido_online_id=pedido_online_id,
    )  # type: ignore
    session.add(movimiento)

    return movimiento
