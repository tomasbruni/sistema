"""reparaciones_rename_columns

Revision ID: 0eafadd6ee31
Revises: a1b2c3d4e5f6
Create Date: 2026-04-17 13:07:47.556059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0eafadd6ee31'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # reparaciones: rename adelanto -> pago_parcial (preserva datos)
    op.alter_column('reparaciones', 'adelanto', new_column_name='pago_parcial')
    op.alter_column('reparaciones', 'total', existing_type=sa.INTEGER(), nullable=True)

    # movimientos_reparaciones: rename monto_total_* -> monto_* (preserva datos)
    op.alter_column('movimientos_reparaciones', 'monto_total_anterior', new_column_name='monto_anterior')
    op.alter_column('movimientos_reparaciones', 'monto_total_nuevo', new_column_name='monto_nuevo')

    # movimientos_reparaciones: columnas nuevas
    op.add_column('movimientos_reparaciones', sa.Column('pago_parcial_agregado', sa.Integer(), nullable=True))
    op.add_column('movimientos_reparaciones', sa.Column('monto_a_devolver', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('movimientos_reparaciones', 'monto_a_devolver')
    op.drop_column('movimientos_reparaciones', 'pago_parcial_agregado')

    op.alter_column('movimientos_reparaciones', 'monto_anterior', new_column_name='monto_total_anterior')
    op.alter_column('movimientos_reparaciones', 'monto_nuevo', new_column_name='monto_total_nuevo')

    op.alter_column('reparaciones', 'total', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('reparaciones', 'pago_parcial', new_column_name='adelanto')
