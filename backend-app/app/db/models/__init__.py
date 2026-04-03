from .models import (
    # Locales
    Local,

    # Usuarios
    Usuario,

    # Ventas
    Venta,
    PagoVenta,
    ConfigComision,
    EgresoCaja,

    # Productos
    Accesorio,
    TipoAccesorio,
    SubtipoAccesorio,
    ModeloCelular,
    MarcaCelular,
    Marca,
    Celular,
    Chip,

    # Stock
    StockAccesorio,
    MovimientoStock,
    TipoMovimiento,
    IngresoLote,
    Transferencia,


    # Detalles de ventas
    DetalleVentaAccesorio,
    DetalleVentaCelular,
    DetalleVentaChip,

    # Reparaciones
    Reparacion,
)

__all__ = [
    "Local",
    "Usuario",
    "Venta",
    "Accesorio",
    "TipoAccesorio",
    "SubtipoAccesorio",
    "ModeloCelular",
    "Marca",
    "Celular",
    "Chip",
    "StockAccesorio",
    "MovimientoStock",
    "TipoMovimiento",
    "DetalleVentaAccesorio",
    "DetalleVentaCelular",
    "DetalleVentaChip",
    "Reparacion",
    "PagoVenta",
    "ConfigComision",
    "IngresoLote",
    "Transferencia",
    "MarcaCelular",
    "EgresoCaja",
]