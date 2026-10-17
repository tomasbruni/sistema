"""facturas_ventas para libro IVA ventas

Revision ID: 03127c32b116
Revises: 6ede02108603
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '03127c32b116'
down_revision: Union[str, Sequence[str], None] = '6ede02108603'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('facturas_ventas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tipo_factura', sa.Enum('A', 'B', name='tipofacturaventa'), nullable=False),
    sa.Column('punto_venta', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('numero_comprobante', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('neto_21', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('iva_21', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('total', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tipo_factura', 'punto_venta', 'numero_comprobante', name='uq_factura_venta_comprobante'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('facturas_ventas')
    sa.Enum(name='tipofacturaventa').drop(op.get_bind(), checkfirst=True)
