from typing import Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Date, DateTime, func, UniqueConstraint, CheckConstraint
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
            name="uq_accesorio_nombre"
        ),
    )

    accesorio_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    precio: int
    tipo_id: int = Field(foreign_key="tipos_accesorios.tipo_id")
    subtipo_id: Optional[int] = Field(foreign_key="subtipos_accesorios.subtipo_id")
    marca_celular_id: Optional[int] = Field(default=None, foreign_key="marcas_celulares.marca_celular_id")
    modelo_celular_id: Optional[int] = Field(default=None, foreign_key="modelos_celulares.modelo_celular_id")
    marca_id: Optional[int] = Field(foreign_key= "marcas.marca_id")
    activo: bool = Field(default = True)


class ImagenAccesorio(SQLModel, table=True):
    """Imagenes de un accesorio para el ecommerce (1 accesorio -> N imagenes).

    Se guarda solo la URL (la imagen se hostea afuera). `es_principal` marca la
    portada de la product card; `orden` define el orden de la galeria.
    """
    __tablename__ = "imagenes_accesorios" #type: ignore
    __table_args__ = (
        UniqueConstraint("accesorio_id", "url", name="uq_imagen_accesorio_url"),
    )

    imagen_accesorio_id: Optional[int] = Field(default=None, primary_key=True)
    accesorio_id: int = Field(foreign_key="accesorios.accesorio_id", index=True)
    url: str
    # id del asset dentro del proveedor (ej. public_id de Cloudinary); permite
    # borrar/transformar via su API. Null si la URL se cargo a mano.
    public_id: Optional[str] = Field(default=None)
    orden: int = Field(default=0)
    es_principal: bool = Field(default=False)


class TipoAccesorio(SQLModel, table=True):
    __tablename__ = "tipos_accesorios" #type: ignore

    tipo_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index = True, sa_column_kwargs={"unique": True})
    imagen_url: Optional[str] = Field(default=None)
    # public_id del asset en Cloudinary (para borrar/reemplazar). Null si no tiene imagen.
    imagen_public_id: Optional[str] = Field(default=None)
    activo: bool = Field(default = True)


class SubtipoAccesorio(SQLModel, table=True):
    __tablename__ = "subtipos_accesorios" #type: ignore

    __table_args__ = (
        UniqueConstraint("tipo_id", "nombre", name="uq_tipo_nombre"),
    )

    subtipo_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    tipo_id: int = Field(foreign_key="tipos_accesorios.tipo_id")
    imagen_url: Optional[str] = Field(default=None)
    # public_id del asset en Cloudinary (para borrar/reemplazar). Null si no tiene imagen.
    imagen_public_id: Optional[str] = Field(default=None)
    activo: bool = Field(default = True)


class ModeloCelular(SQLModel, table=True):
    __tablename__ = "modelos_celulares" #type: ignore
    __table_args__ = (
        UniqueConstraint("marca_celular_id", "nombre", name="uq_modelo_por_marca"),
    )

    modelo_celular_id: Optional[int] = Field(default=None, primary_key=True)
    marca_celular_id: int = Field(foreign_key="marcas_celulares.marca_celular_id")
    nombre: str = Field(index=True)
    activo: bool = Field(default = True)

class MarcaCelular(SQLModel, table=True):
    __tablename__ = "marcas_celulares" #type: ignore

    marca_celular_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True,sa_column_kwargs={"unique": True})
    activo: bool = Field(default = True)
    

class Celular(SQLModel, table=True):
    __tablename__ = "celulares" #type: ignore

    celular_id: Optional[int] = Field(default=None, primary_key=True)
    # FK a modelos en vez de marca, modelo
    modelo_celular_id: int = Field(foreign_key="modelos_celulares.modelo_celular_id")
    marca_celular_id: int = Field(foreign_key="marcas_celulares.marca_celular_id")
    imei: str = Field(index=True,sa_column_kwargs={"unique": True})
    precio: int
    local_id: int = Field(foreign_key="locales.local_id")
    proveedor: Optional[int] = Field(foreign_key="proveedores.proveedor_id") #not null por ahora
    estado: str


class IngresoLoteChip(SQLModel, table=True):
    __tablename__ = "ingresos_lote_chips" #type: ignore

    ingreso_lote_chip_id: Optional[int] = Field(default=None, primary_key=True)
    fecha: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")
    receptor_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")
    local_id: Optional[int] = Field(default=None, foreign_key="locales.local_id")
    observaciones: Optional[str] = None


class Chip(SQLModel, table=True):
    __tablename__ = "chips" #type: ignore

    chip_id: Optional[int] = Field(default=None, primary_key=True)
    compania: str
    numero_serie: str = Field(index=True, sa_column_kwargs={"unique": True})
    precio: int
    local_id: int = Field(foreign_key="locales.local_id")
    estado: str
    ingreso_lote_chip_id: Optional[int] = Field(default=None, foreign_key="ingresos_lote_chips.ingreso_lote_chip_id")


# =====================
# STOCK (solo accesorios)
# =====================
class TipoMovimiento(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    VENTA = "VENTA"
    DEVOLUCION = "DEVOLUCION"
    RESERVA = "RESERVA"


class StockAccesorio(SQLModel, table=True):
    __tablename__ = "stock_accesorios" #type: ignore
    __table_args__ = (
        UniqueConstraint("accesorio_id", "local_id"),
        # Se permite cantidad < 0: las ventas pueden dejar el stock en negativo
        # cuando hay error de conteo (producto presente físicamente pero no cargado).
        # El negativo funciona como señal de auditoría para corregir el conteo.
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
    # Snapshots para auditoría: stock_anterior + cantidad == stock_nuevo
    # NULL en movimientos históricos previos a la migración
    stock_anterior: Optional[int] = Field(default=None)
    stock_nuevo: Optional[int] = Field(default=None)
    fecha: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    motivo: Optional[str] = Field(default=None, max_length=255)
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")
    pedido_online_id: Optional[int] = Field(default=None, foreign_key="pedidos_online.pedido_id")


class IngresoLote(SQLModel, table=True):
    __tablename__ = "ingresos_lote" #type: ignore

    ingreso_lote_id: Optional[int] = Field(default=None, primary_key=True)
    fecha: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    receptor_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")
    local_id: Optional[int] = Field(default=None, foreign_key="locales.local_id")
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
    tipo: str         # VENTA | DEVOLUCION | ONLINE
    pedido_online_id: Optional[int] = Field(default=None, foreign_key="pedidos_online.pedido_id")
    observacion: Optional[str] = Field(default=None, max_length=500)  # nota libre de la vendedora (ej: descuentos)
 
 
class PagoVenta(SQLModel, table=True):
    __tablename__ = "pagos_ventas"  # type: ignore
 
    pago_id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="ventas.venta_id")
    medio_de_pago: str  # EFECTIVO | DEBITO | CREDITO | QR | TRANSFERENCIA
    importe: int
    cuotas: Optional[int]


class SobranteFaltante(SQLModel, table=True):
    __tablename__ = "sobrantes_faltantes"  # type: ignore
    __table_args__ = (
        UniqueConstraint("fecha", "local_id", "usuario_id", name="uq_sf_fecha_local"),
    ) #MODIFIQUE

    id: Optional[int] = Field(default=None, primary_key=True)
    local_id: int = Field(foreign_key="locales.local_id")
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    fecha: Optional[date] = Field(default=None, sa_column=Column(Date, server_default=func.current_date(), nullable=False))
    sobrante: int = Field(default=0)
    faltante: int = Field(default=0)


class EgresoCaja(SQLModel, table=True):
    __tablename__ = "egresos_cajas"  # type: ignore

    egreso_caja_id: Optional[int] = Field(default=None, primary_key=True)
    fecha: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    monto: int
    descripcion: str   # "plomero", "cambio chico", etc.
    medio_pago: Optional[str]   # EFECTIVO (casi siempre)
    local_id: int = Field(foreign_key="locales.local_id")
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
 

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
    celular: str
    nombre_cliente: str
    telefono_cliente: str
    dni_cliente: Optional[str] = None
    mail_cliente: Optional[str] = None
    descripcion: Optional[str] = None
    total: Optional[int] = None # SI ES REVISION PUEDE NO SABERSE
    pago_parcial: int # MIGRACION MANUAL EN ALEMBIC POR CAMBIO DE NOMBRE
    pago_reparador: Optional[int] = None
    pagado: bool = Field(default=False)
    estado: str # REVISION | CANCELADO | EN_REPARACION | ENTREGADO
    fecha_ingreso: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    local_id: int = Field(foreign_key="locales.local_id")
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")


class MovimientoReparacion(SQLModel, table=True):
    __tablename__ = "movimientos_reparaciones"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    reparacion_id: int = Field(foreign_key="reparaciones.reparacion_id", index=True)
    tipo_movimiento: str # CAMBIO DE ESTADO (ESTADO) | CAMBIO DE PRECIO (PRECIO)

    # IGUALES SI ES CAMBIO DE PRECIO, DISTINTOS SI ES CAMBIO DE ESTADO
    estado_anterior: Optional[str]
    estado_nuevo: Optional[str]

    # PARA MOVIMIENTOS DE TIPO CAMBIO DE PRECIO (MANUAL EN ALEMBIC POR CAMBIO DE NOMBRE)
    monto_anterior: Optional[int] = None 
    monto_nuevo: Optional[int] = None 

    # PARA TRANSICIONES DE TIPO ENTREGA
    monto_entrega_recibido: Optional[int] = None

    # PARA TRANSICIONES DE TIPO ACEPTAR
    pago_parcial_agregado: Optional[int] = None

    # PARA CANCELACIONES
    monto_a_devolver: Optional[int] = None

    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    fecha: Optional[datetime] = Field(default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    observaciones: Optional[str] = Field(default=None, max_length=500)


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


class CompaniaChip(SQLModel, table=True):
    __tablename__ = "companias_chips" #type: ignore

    compania_chip_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    activo: bool = Field(default = True)


# =====================
# PEDIDOS ONLINE
# =====================
class PedidoOnline(SQLModel, table=True):
    __tablename__ = "pedidos_online"  # type: ignore

    pedido_id: Optional[int] = Field(default=None, primary_key=True)
    estado: str = Field(default="PENDIENTE_APROBACION")  # PENDIENTE_APROBACION | APROBADO | RECHAZADO | ENTREGADO | CANCELADO

    # Entrega
    modo_entrega: str  # RETIRO_LOCAL | ENVIO
    local_retiro_id: Optional[int] = Field(default=None, foreign_key="locales.local_id")
    local_stock_id: Optional[int] = Field(default=None, foreign_key="locales.local_id")
    direccion_envio: Optional[str] = Field(default=None, max_length=500)

    # Cliente
    nombre_cliente: str
    telefono_cliente: str
    mail_cliente: Optional[str] = Field(default=None, max_length=255)
    notas_cliente: Optional[str] = Field(default=None, max_length=1000)

    # Pago
    medio_de_pago: str  # EFECTIVO | MERCADOPAGO
    referencia_pago: Optional[str] = Field(default=None, max_length=255)
    estado_pago: str = Field(default="PENDIENTE")  # PENDIENTE | PAGADO | REEMBOLSADO

    # Montos y auditoría
    total_productos: int  # suma de precio_lista * cantidad de cada ítem
    costo_envio: int = Field(default=0)
    monto_total: int  # total_productos + costo_envio
    notas_admin: Optional[str] = Field(default=None, max_length=1000)
    fecha_creacion: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    fecha_actualizacion: Optional[datetime] = Field(default=None)
    usuario_id_admin: Optional[int] = Field(default=None, foreign_key="usuarios.usuario_id")


class DetallePedidoAccesorio(SQLModel, table=True):
    __tablename__ = "detalles_pedidos_accesorios"  # type: ignore

    detalle_id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidos_online.pedido_id")
    accesorio_id: int = Field(foreign_key="accesorios.accesorio_id")
    precio_lista: int  # snapshot del precio al momento de crear el pedido
    precio_unitario: int  # precio de venta (puede diferir de precio_lista por descuentos)
    cantidad: int


class DetallePedidoCelular(SQLModel, table=True):
    __tablename__ = "detalles_pedidos_celulares"  # type: ignore

    detalle_id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidos_online.pedido_id")
    celular_id: int = Field(foreign_key="celulares.celular_id")
    imei: str  # snapshot
    precio_lista: int  # snapshot del precio al momento de crear el pedido


class DetallePedidoChip(SQLModel, table=True):
    __tablename__ = "detalles_pedidos_chips"  # type: ignore

    detalle_id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidos_online.pedido_id")
    chip_id: int = Field(foreign_key="chips.chip_id")
    numero_serie: str  # snapshot
    precio_lista: int  # snapshot del precio al momento de crear el pedido


# =====================
# MOVIMIENTOS FINANCIEROS
# =====================
class TipoMovimientoFinanciero(str, Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"


class MovimientoFinanciero(SQLModel, table=True):
    __tablename__ = "movimientos_financieros"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    tipo: TipoMovimientoFinanciero
    monto: int
    descripcion: str
    fecha: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")