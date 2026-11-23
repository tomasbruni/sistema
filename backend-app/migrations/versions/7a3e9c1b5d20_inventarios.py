"""inventarios

Revision ID: 7a3e9c1b5d20
Revises: d51f07104906
Create Date: 2026-11-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7a3e9c1b5d20'
down_revision: Union[str, Sequence[str], None] = 'd51f07104906'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('inventarios',
    sa.Column('inventario_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('local_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('observaciones', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('sobrante_estimado', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['local_id'], ['locales.local_id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id'], ),
    sa.PrimaryKeyConstraint('inventario_id')
    )
    op.add_column('movimientos_stock', sa.Column('inventario_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_movimientos_stock_inventario_id'), 'movimientos_stock', ['inventario_id'], unique=False)
    op.create_foreign_key(
        'movimientos_stock_inventario_id_fkey', 'movimientos_stock', 'inventarios',
        ['inventario_id'], ['inventario_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('movimientos_stock_inventario_id_fkey', 'movimientos_stock', type_='foreignkey')
    op.drop_index(op.f('ix_movimientos_stock_inventario_id'), table_name='movimientos_stock')
    op.drop_column('movimientos_stock', 'inventario_id')
    op.drop_table('inventarios')
