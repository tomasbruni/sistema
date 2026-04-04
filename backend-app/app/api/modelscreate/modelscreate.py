from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.db.models import TipoMovimiento

# =====================
# LOCALES
# =====================
class LocalCreate(SQLModel):
    nombre: str
    direccion: str
    tipo: str
    


# =====================
# VENDEDORAS
# =====================
class UsuarioCreate(SQLModel):
    nombre: str
    password: str
    rol: str

# =====================
# PRODUCTOS
# =====================
class AccesorioCreate(SQLModel):
    nombre: str
    precio: int
    tipo_id: int
    subtipo_id: Optional[int] = None
    marca_celular_id: Optional[int] = None
    modelo_celular_id: Optional[int] = None
    marca_id: Optional[int] = None
    activo: bool = True


class TipoAccesorioCreate(SQLModel):
    nombre: str


class SubtipoAccesorioCreate(SQLModel):
    nombre: str
    tipo_id: int


class ModeloCelularCreate(SQLModel):
    marca_celular_id: int
    nombre: str

class MarcaCelularCreate(SQLModel):
    nombre: str

class MarcaCreate(SQLModel):
    nombre: str


class CelularCreate(SQLModel):
    modelo_celular_id: int
    marca_celular_id: int
    imei: str
    precio: int
    local_id: int
    estado: str


class ChipCreate(SQLModel):
    compania: str
    numero_serie: str
    precio: int
    local_id: int
    estado: str


# =====================
# STOCK
# =====================
class StockAccesorioCreate(SQLModel):
    accesorio_id: int
    local_id: int
    cantidad: int


class TransferenciaStockCreate(SQLModel):
    """Schema para transferir stock entre locales."""
    accesorio_id: int = Field(..., gt=0)
    local_origen_id: int = Field(..., gt=0)
    local_destino_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0)
    motivo: Optional[str] = Field(None, max_length=255)


class ItemTransferencia(SQLModel):
    accesorio_id: int = Field(..., gt=0)
    cantidad_a_transferir: int


class TransferenciaLoteCreate(SQLModel):
    local_origen_id: int = Field(..., gt=0)
    local_destino_id: int = Field(..., gt=0)
    observaciones: Optional[str] = Field(None, max_length=500)  # ← agregar
    productos: List[ItemTransferencia]


class ItemIngreso(SQLModel):
    accesorio_id: int = Field(..., gt=0)
    cantidad_ingreso: int


class IngresoLoteCreate(SQLModel):
    local_id: int = Field(..., gt=0)
    receptor_id: int = Field(..., gt=0)
    observaciones: Optional[str] = Field(None, max_length=500)  # ← agregar
    productos: List[ItemIngreso]


class AjusteStockCreate(SQLModel):
    """Schema para ajuste directo de stock (inventario físico)."""
    accesorio_id: int = Field(..., gt=0)
    local_id: int = Field(..., gt=0)
    cantidad_nueva: int = Field(..., ge=0, description="Nueva cantidad absoluta de stock")
    motivo: str = Field(..., max_length=255, description="Razón del ajuste (ej: inventario físico)")


class MovimientoStockCreate(SQLModel):
    """Schema para crear un movimiento desde el front"""
    accesorio_id: int
    local_id: int
    tipo_movimiento: TipoMovimiento
    cantidad: int
    motivo: Optional[str] = Field(default=None, max_length=255)

# =====================
# COMISIONES
# =====================
class ConfigComisionCreate(SQLModel):
    tipo_producto: str  # ACCESORIO | CELULAR | CHIP
    tipo_calculo: str   # PORCENTAJE | FIJO
    valor: int          # 3 si es PORCENTAJE, monto si es FIJO
 

# =====================
# DETALLES DE VENTAS
# =====================
class DetalleAccesorioCreate(SQLModel):
    accesorio_id: int
    precio_unitario: int  # editable desde UI, snapshot del precio al vender, precio lista es fijo se pone desde el back
    cantidad: int
 
 
class DetalleCelularCreate(SQLModel):
    celular_id: int
    imei: str             # snapshot
    precio_unitario: int
 
 
class DetalleChipCreate(SQLModel):
    chip_id: int
    numero_serie: str     # snapshot
    precio_unitario: int


# =====================
# REPARACIONES
# =====================
class ReparacionCreate(SQLModel):
    local_id: int
    usuario_id: int
    nombre_cliente: str
    telefono_cliente: str
    mail_cliente: Optional[str] = None
    estado: str
    descripcion_falla: Optional[str] = None
    fecha_ingreso: Optional[datetime] = None
    costo_reparador: int
    costo_final: Optional[int] = None

# =====================
# VENTA
# =====================
class PagoVentaCreate(SQLModel):
    medio_de_pago: str  # EFECTIVO | TARJETA | TRANSFERENCIA
    importe: int = Field(..., gt=0)
    cuotas: Optional[int] = 1


# =====================
# PEDIDOS ONLINE
# =====================
class DetallePedidoAccesorioCreate(SQLModel):
    accesorio_id: int
    precio_unitario: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0)


class DetallePedidoCelularCreate(SQLModel):
    celular_id: int
    imei: str  # snapshot


class DetallePedidoChipCreate(SQLModel):
    chip_id: int
    numero_serie: str  # snapshot


class PedidoOnlineCreate(SQLModel):
    modo_entrega: str  # RETIRO_LOCAL | ENVIO
    local_retiro_id: Optional[int] = None   # requerido si modo_entrega=RETIRO_LOCAL
    direccion_envio: Optional[str] = None   # requerida si modo_entrega=ENVIO
    medio_de_pago: str                      # EFECTIVO | MERCADOPAGO
    referencia_pago: Optional[str] = None
    costo_envio: int = Field(default=0, ge=0)
    nombre_cliente: str
    telefono_cliente: str
    mail_cliente: Optional[str] = None
    notas_cliente: Optional[str] = None
    detalles_accesorios: Optional[List[DetallePedidoAccesorioCreate]] = []
    detalles_celulares: Optional[List[DetallePedidoCelularCreate]] = []
    detalles_chips: Optional[List[DetallePedidoChipCreate]] = []


class VentaCreate(SQLModel):
    local_id: int = Field(..., gt=0)
    usuario_id: Optional[int] = None
    tipo: str  # VENTA | DEVOLUCION

    pagos: List[PagoVentaCreate] = Field(..., min_length=1)
 
    detalles_accesorios: Optional[List[DetalleAccesorioCreate]] = []
    detalles_celulares: Optional[List[DetalleCelularCreate]] = []
    detalles_chips: Optional[List[DetalleChipCreate]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "local_id": 1,
                "usuario_id": 1,
                "tipo": "VENTA",
                "pagos": [
                    {"medio_de_pago": "EFECTIVO", "importe": 5000},
                    {"medio_de_pago": "ELECTRONICO",  "importe": 10000}
                ],
                "detalles_accesorios": [
                    {
                        "accesorio_id": 5,
                        "precio_unitario": 5000,
                        "cantidad": 1
                    }
                ],
                "detalles_celulares": [
                    {
                        "celular_id": 3,
                        "imei": "123456789012345",
                        "precio_unitario": 10000
                    }
                ],
                "detalles_chips": []
            }
        }

