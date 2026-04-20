from typing import Optional
from sqlmodel import SQLModel
from datetime import datetime
from app.db.models import TipoMovimiento

# =====================
# LOCALES
# =====================
class LocalUpdate(SQLModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    tipo: Optional[str] = None
    activo: Optional[bool] = None


# =====================
# VENDEDORAS
# =====================
class UsuarioUpdate(SQLModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None


# =====================
# VENTAS
# =====================
class VentaUpdate(SQLModel):
    local_id: Optional[int] = None
    vendedora_id: Optional[int] = None
    monto_total: Optional[int] = None
    tipo: Optional[str] = None


# =====================
# PRODUCTOS
# =====================
class AccesorioUpdate(SQLModel):
    nombre: Optional[str] = None
    precio: Optional[int] = None
    tipo_id: Optional[int] = None
    subtipo_id: Optional[int] = None
    modelo_celular_id: Optional[int] = None
    marca_celular_id: Optional[int] = None
    activo: Optional[bool] = None


class TipoAccesorioUpdate(SQLModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = True


class SubtipoAccesorioUpdate(SQLModel):
    nombre: Optional[str] = None
    tipo_id: Optional[int] = None
    activo: Optional[bool] = True


class ModeloCelularUpdate(SQLModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = True


class MarcaCelularUpdate(SQLModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = True
    

class CelularUpdate(SQLModel):
    marca_celular_id: Optional[int] = None
    modelo_celular_id: Optional[int] = None
    precio: Optional[int] = None
    local_id: Optional[int] = None
    estado: Optional[str] = None


class ChipUpdate(SQLModel):
    compania: Optional[str] = None
    precio: Optional[int] = None
    local_id: Optional[int] = None
    estado: Optional[str] = None


# =====================
# STOCK
# =====================
class StockAccesorioUpdate(SQLModel):
    cantidad: Optional[int] = None


class MovimientoStockUpdate(SQLModel):
    accesorio_id: int 
    local_id: int 
    tipo_movimiento: TipoMovimiento
    cantidad: int  # Puede ser negativo para salidas
    fecha: Optional[datetime] 
    motivo: Optional[str] 
    usuario_id: Optional[int]


# =====================
# CONFIG COMISIONES
# =====================
class ConfigComisionUpdate(SQLModel):
    tipo_calculo: Optional[str] = None
    valor: Optional[int] = None


# =====================
# REPARACIONES
# =====================
class ReparacionUpdate(SQLModel):
    numero_orden: Optional[int] = None
    descripcion: Optional[str] = None
    pago_parcial: Optional[int] = None
    pago_reparador: Optional[int] = None
    telefono_cliente: Optional[str] = None
    dni_cliente: Optional[str] = None
    mail_cliente: Optional[str] = None


# =====================
# MARCAS
# =====================
class MarcaUpdate(SQLModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None


# =====================
# PEDIDOS ONLINE
# =====================
class PedidoOnlineAdminNota(SQLModel):
    notas_admin: Optional[str] = None


class PedidoOnlineAprobarBody(SQLModel):
    local_stock_id: int
    notas_admin: Optional[str] = None

