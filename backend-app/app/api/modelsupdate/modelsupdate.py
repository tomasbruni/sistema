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


# =====================
# VENDEDORAS
# =====================
class UsuarioUpdate(SQLModel):
    nombre: Optional[str] = None


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
    modelo_id: Optional[int] = None
    marca_id: Optional[int] = None
    activo: Optional[bool] = None


class TipoAccesorioUpdate(SQLModel):
    nombre: str


class SubtipoAccesorioUpdate(SQLModel):
    nombre: Optional[str] = None
    tipo_id: Optional[int] = None


class ModeloCelularUpdate(SQLModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None


class CelularUpdate(SQLModel):
    modelo_id: Optional[int] = None
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
    estado: Optional[str] = None
    descripcion_falla: Optional[str] = None
    costo_reparador: Optional[int] = None
    costo_final: Optional[int] = None
    telefono_cliente: Optional[str] = None
    mail_cliente: Optional[str] = None


# =====================
# MARCAS
# =====================
class MarcaUpdate(SQLModel):
    nombre: Optional[str] = None
