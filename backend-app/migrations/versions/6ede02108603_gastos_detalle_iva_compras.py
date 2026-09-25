"""gastos con detalle para libro IVA compras + proveedores_fiscales

Recrea la tabla `gastos` (se pierden los datos: hacer backup y recargar a mano).

Revision ID: 6ede02108603
Revises: 51ed49e6961f
Create Date: 2026-09-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '6ede02108603'
down_revision: Union[str, Sequence[str], None] = '51ed49e6961f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


IMPORTES = [
    'neto_105', 'neto_21', 'neto_27',
    'iva_105', 'iva_21', 'iva_27',
    'exento', 'percepcion_iva', 'percepcion_iibb_bsas', 'percepcion_iibb_caba',
    'otros_impuestos', 'no_gravado',
    'aporte_real', 'aporte_blanco', 'aporte_iva', 'aporte_percepcion_iibb',
]


def _drop_gastos() -> None:
    op.drop_table('gastos')
    sa.Enum(name='tipofactura').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='tipogasto').drop(op.get_bind(), checkfirst=True)


def upgrade() -> None:
    """Upgrade schema."""
    _drop_gastos()

    op.create_table('proveedores_fiscales',
    sa.Column('proveedor_fiscal_id', sa.Integer(), nullable=False),
    sa.Column('razon_social', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('cuit', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('proveedor_fiscal_id'),
    )
    op.create_index(op.f('ix_proveedores_fiscales_cuit'), 'proveedores_fiscales', ['cuit'], unique=True)

    op.create_table('gastos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.Enum('REAL', 'FACTURA', name='tipogasto'), nullable=False),
    sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('total', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('periodo', sa.Date(), nullable=True),
    sa.Column('tipo_factura', sa.Enum('A', 'C', name='tipofactura'), nullable=True),
    sa.Column('proveedor_fiscal_id', sa.Integer(), nullable=True),
    sa.Column('punto_venta', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('numero_comprobante', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('comprada', sa.Boolean(), nullable=False),
    sa.Column('porcentaje_real', sa.Integer(), nullable=True),
    *[sa.Column(c, sa.Numeric(precision=14, scale=2), nullable=False) for c in IMPORTES],
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id'], ),
    sa.ForeignKeyConstraint(['proveedor_fiscal_id'], ['proveedores_fiscales.proveedor_fiscal_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('proveedor_fiscal_id', 'tipo_factura', 'punto_venta', 'numero_comprobante',
                        name='uq_gasto_comprobante'),
    sa.CheckConstraint(
        "(tipo = 'REAL' AND periodo IS NULL) OR "
        "(tipo = 'FACTURA' AND periodo IS NOT NULL AND EXTRACT(DAY FROM periodo) = 1)",
        name='ck_gasto_periodo'),
    )


def downgrade() -> None:
    """Downgrade schema: vuelve al esquema anterior de gastos (sin datos)."""
    _drop_gastos()
    op.drop_index(op.f('ix_proveedores_fiscales_cuit'), table_name='proveedores_fiscales')
    op.drop_table('proveedores_fiscales')

    op.create_table('gastos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.Enum('REAL', 'FACTURA', name='tipogasto'), nullable=False),
    sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('total', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('tipo_factura', sa.Enum('A', 'C', name='tipofactura'), nullable=True),
    sa.Column('comprada', sa.Boolean(), nullable=False),
    sa.Column('porcentaje_real', sa.Integer(), nullable=True),
    sa.Column('neto', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('iva', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('aporte_real', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('aporte_blanco', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('aporte_iva', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
