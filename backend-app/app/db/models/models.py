from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func, UniqueConstraint, CheckConstraint   
from enum import Enum


# =====================
# LOCALES
# =====================
class Local(SQLModel, table=True):
    __tablename__ = "locales" #type: ignore

    local_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    direccion: str
    tipo: str = Field(default = "LOCAL")
    activo: bool = Field(default = True)


# =====================
# USUARIOS
# =====================
class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios" #type: ignore

    usuario_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    password: str
    rol: str
    activo: bool = Field(default = True)

# =====================
# PRODUCTOS
# =====================
class Accesorio(SQLModel, table=True):
    __tablename__ = "accesorios" #type: ignore
    __table_args__ = (
        UniqueConstraint(
            "nombre",
            "tipo_id",
            "modelo_id",
            name="uq_accesorio_nombre_tipo_modelo"
        ),
    )

    accesorio_id: Optional[int] = Field(default=None, primary_key=True)
    #si intento meter 2 cosas exactamente iguales, falla aca
    sku: str = Field(
        index=True,
        nullable=False,
        sa_column_kwargs={"unique": True}
    )
    nombre: str
    precio: int
    tipo_id: int = Field(foreign_key="tipos_accesorios.tipo_id")
    subtipo_id: Optional[int] = Field(foreign_key="subtipos_accesorios.subtipo_id")
    modelo_id: Optional[int] = Field(default=None, foreign_key="modelos_celulares.modelo_id")
    marca_id: Optional[int] = Field(foreign_key= "marcas.marca_id")
    activo: bool = Field(default = True)


class TipoAccesorio(SQLModel, table=True):
    __tablename__ = "tipos_accesorios" #type: ignore

    tipo_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index = True, sa_column_kwargs={"unique": True})
    activo: bool = Field(default = True)


class SubtipoAccesorio(SQLModel, table=True):
    __tablename__ = "subtipos_accesorios" #type: ignore

    __table_args__ = (
        UniqueConstraint("tipo_id", "nombre", name="uq_tipo_nombre"),
    )

    subtipo_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    tipo_id: int = Field(foreign_key="tipos_accesorios.tipo_id")
    activo: bool = Field(default = True)


class ModeloCelular(SQLModel, table=True):
    __tablename__ = "modelos_celulares" #type: ignore
    __table_args__ = (
        UniqueConstraint("marca", "modelo"),
    )

    modelo_id: Optional[int] = Field(default=None, primary_key=True)
    marca: str
    modelo: str
    activo: bool = Field(default = True)


class Celular(SQLModel, table=True):
    __tablename__ = "celulares" #type: ignore

    celular_id: Optional[int] = Field(default=None, primary_key=True)
    # FK a modelos en vez de marca, modelo
    modelo_id: int = Field(foreign_key="modelos_celulares.modelo_id")
    imei: str = Field(index=True,sa_column_kwargs={"unique": True})
    precio: int
    local_id: int = Field(foreign_key="locales.local_id")
    proveedor: Optional[int] = Field(foreign_key="proveedores.proveedor_id") #not null por ahora
    estado: str


class Chip(SQLModel, table=True):
    __tablename__ = "chips" #type: ignore

    chip_id: Optional[int] = Field(default=None, primary_key=True)
    compania: str
    numero_serie: str = Field(index=True, sa_column_kwargs={"unique": True})
    precio: int
    local_id: int = Field(foreign_key="locales.local_id")
    estado: str


# =====================
# STOCK (solo accesorios)
# =====================
class TipoMovimiento(str, Enum):
    ENTRADA = "ENTRADA" 
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    VENTA = "VENTA"


class StockAccesorio(SQLModel, table=True):
    __tablename__ = "stock_accesorios" #type: ignore
    __table_args__ = (
        UniqueConstraint("accesorio_id", "local_id"),
        CheckConstraint("cantidad >= 0", name="ck_stock_accesorios_cantidad_no_negativa"),
    )

    stock_id: Optional[int] = Field(default=None, primary_key=True)
    accesorio_id: int = Field(foreign_key="accesorios.accesorio_id")
    local_id: int = Field(foreign_key="locales.local_id")
    cantidad: int


class MovimientoStock(SQLModel, table=True):
    """Historial de movimientos de stock"""
    __tablename__ = "movimientos_stock" #type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    accesorio_id: int = Field(foreign_key="accesorios.accesorio_id", index=True)
    local_id: int = Field(foreign_key="locales.local_id", index=True)
    tipo_movimiento: TipoMovimiento
    venta_id: Optional[int] = Field(foreign_key="ventas.venta_id")
    ingreso_lote_id: Optional[int] = Field(foreign_key="ingresos_lote.ingreso_lote_id")
    transferencia_id: Optional[int] = Field(foreign_key="transferencias.transferencia_id")
    cantidad: int  # Puede ser negativo para salidas
    fecha: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    motivo: Optional[str] = Field(default=None, max_length=255)
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")


class IngresoLote(SQLModel, table=True):
    __tablename__ = "ingresos_lote" #type: ignore

    ingreso_lote_id: Optional[int] = Field(default=None, primary_key=True)
    fecha: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    receptor_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")
    observaciones: Optional[str]


class Transferencia(SQLModel, table=True):
    __tablename__ = "transferencias" #type: ignore

    transferencia_id: Optional[int] = Field(default=None, primary_key=True)
    local_origen_id: int = Field(foreign_key="locales.local_id")
    local_destino_id: int = Field(foreign_key="locales.local_id")
    fecha: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")
    observaciones: Optional[str]


# =====================
# VENTAS
# =====================
class Venta(SQLModel, table=True):
    __tablename__ = "ventas"  # type: ignore
 
    venta_id: Optional[int] = Field(default=None, primary_key=True)
    local_id: int = Field(foreign_key="locales.local_id")
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    fecha_ingreso: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    monto_total: int  # validado por el backend: sum(precio_unitario * cantidad) de todos los detalles
    tipo: str         # VENTA | DEVOLUCION
 
 
class PagoVenta(SQLModel, table=True):
    __tablename__ = "pagos_ventas"  # type: ignore
 
    pago_id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="ventas.venta_id")
    medio_de_pago: str  # EFECTIVO | DEBITO | CREDITO | QR | TRANSFERENCIA
    importe: int
    cuotas: Optional[int]
 

# =====================
# DETALLES DE VENTAS
# =====================

class DetalleVentaAccesorio(SQLModel, table=True):
    __tablename__ = "detalles_ventas_accesorios"  # type: ignore
 
    detalle_id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="ventas.venta_id")
    accesorio_id: int = Field(foreign_key="accesorios.accesorio_id")
    precio_lista: int # snapshot del precio de lista al momento de la venta
    precio_unitario: int  # snapshot editable, ya refleja cualquier descuento por ítem
    cantidad: int
    comision_importe: int  # calculado por backend: precio_unitario * cantidad * (ConfigComision.valor / 100)
 
 
class DetalleVentaCelular(SQLModel, table=True):
    __tablename__ = "detalles_ventas_celulares"  # type: ignore
 
    detalle_id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="ventas.venta_id")
    celular_id: int = Field(foreign_key="celulares.celular_id")
    imei: str         # snapshot por si el celular se modifica o elimina
    precio_lista: int
    precio_unitario: int
    comision_importe: int  # snapshot del monto fijo de ConfigComision al momento de la venta
 
 
class DetalleVentaChip(SQLModel, table=True):
    __tablename__ = "detalles_ventas_chips"  # type: ignore
 
    detalle_id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="ventas.venta_id")
    chip_id: int = Field(foreign_key="chips.chip_id")
    numero_serie: str  # snapshot por si el chip se modifica o elimina
    precio_lista: int
    precio_unitario: int
    comision_importe: int  # snapshot del monto fijo de ConfigComision al momento de la venta


class ConfigComision(SQLModel, table=True):
    __tablename__ = "config_comisiones"  # type: ignore
    __table_args__ = (
        UniqueConstraint("tipo_producto", name="uq_config_comision_tipo"),
    )

    config_comision_id: Optional[int] = Field(default=None, primary_key=True)
    tipo_producto: str = Field(index=True)  # ACCESORIO | CELULAR | CHIP
    tipo_calculo: str                        # PORCENTAJE | FIJO
    valor: int                               # 3 si es PORCENTAJE, monto si es FIJO

# =====================
# REPARACIONES
# =====================
class Reparacion(SQLModel, table=True):
    __tablename__ = "reparaciones" #type: ignore
    
    reparacion_id: Optional[int] = Field(default=None, primary_key=True)
    local_id: int = Field(foreign_key="locales.local_id")
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    nombre_cliente: str  
    telefono_cliente: str  
    mail_cliente: Optional[str] = None
    estado: str
    descripcion_falla: Optional[str] = None  
    fecha_ingreso: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    costo_reparador: int  
    costo_final: Optional[int] = None

#AUX
class Marca(SQLModel, table=True):
    __tablename__ = "marcas" #type: ignore

    marca_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    activo: bool = Field(default = True)

class Proveedor(SQLModel, table=True):
    __tablename__ = "proveedores" #type: ignore
    
    proveedor_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str 
    activo: bool = Field(default = True)