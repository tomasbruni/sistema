from typing import Annotated, Optional
from fastapi import HTTPException, status
from sqlmodel import Session, select, Field

from app.db.models import *
from app.api.modelscreate import *

# ME PARECE Q NO LA VOY A USAR
# arreglar race conditions
def registrar_movimiento_stock(
    session: Session,
    movimiento: MovimientoStockCreate,
    validar_stock: bool = True  # Para SALIDA/VENTA
) -> dict:
    """
    Función interna para registrar movimientos de stock.
    
    IMPORTANTE: Esta función NO hace commit(). 
    El caller debe hacer commit() para permitir transacciones atómicas.
    
    Args:
        session: Sesión de SQLModel (compartida con la transacción padre)
        accesorio_id: ID del accesorio
        local_id: ID del local
        tipo_movimiento: ENTRADA, SALIDA, AJUSTE, VENTA
        cantidad: Cantidad (para AJUSTE es el total nuevo, para otros es la diferencia)
        motivo: Descripción del movimiento
        usuario_id: Usuario que realiza el movimiento
        validar_stock: Si es False, permite stock negativo (para casos especiales)
    
    Returns:
        dict con información del movimiento
    
    Raises:
        HTTPException: Si hay errores de validación
    """
    # Validar tipo de movimiento
    tipos_validos = ['ENTRADA', 'SALIDA', 'AJUSTE', 'VENTA']
    if movimiento.tipo_movimiento not in tipos_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de movimiento debe ser uno de: {tipos_validos}"
        )
    
    # Verificar que el accesorio existe
    accesorio = session.get(Accesorio, movimiento.accesorio_id)
    if not accesorio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accesorio con ID {movimiento.accesorio_id} no encontrado"
        )
    
    # Verificar que el local existe
    local = session.get(Local, movimiento.local_id)
    if not local:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Local con ID {movimiento.local_id} no encontrado"
        )
    
    # Obtener o crear el stock
    stock_query = select(StockAccesorio).where(
            StockAccesorio.accesorio_id == movimiento.accesorio_id,
            StockAccesorio.local_id == movimiento.local_id
    )
    stock = session.exec(stock_query).first()
    
    #si no hay stock del accesorio, lo agrega
    if not stock:
        stock = StockAccesorio(
            accesorio_id=movimiento.accesorio_id,
            local_id=movimiento.local_id,
            cantidad=0
        )
        session.add(stock)
    
    # Guardar cantidad original
    cantidad_original = stock.cantidad
    
    # Aplicar el movimiento
    if movimiento.tipo_movimiento == 'ENTRADA':
        stock.cantidad += movimiento.cantidad
    
    elif movimiento.tipo_movimiento in ['SALIDA', 'VENTA']:
        if validar_stock and stock.cantidad < movimiento.cantidad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente. Disponible: {stock.cantidad}, Solicitado: {movimiento.cantidad}"
            )
        stock.cantidad -= movimiento.cantidad
    
    elif movimiento.tipo_movimiento == 'AJUSTE':
        stock.cantidad = movimiento.cantidad
    
    # Crear el registro del movimiento
    nuevo_movimiento = MovimientoStock(
        **movimiento.model_dump()
    )
    
    session.add(nuevo_movimiento)
    
    # NO hacemos commit aquí - el caller lo hará
    # Esto permite transacciones atómicas
    
    return {
        "movimiento_id": nuevo_movimiento.id,  # Puede ser None antes del commit
        "stock_anterior": cantidad_original,
        "stock_actual": stock.cantidad,
        "diferencia": stock.cantidad - cantidad_original
    }