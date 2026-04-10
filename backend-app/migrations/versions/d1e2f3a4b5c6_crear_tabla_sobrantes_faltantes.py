"""crear tabla sobrantes_faltantes

Revision ID: d1e2f3a4b5c6
Revises: fb169b6c3eee
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'fb169b6c3eee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sobrantes_faltantes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('local_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
        sa.Column('sobrante', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('faltante', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['local_id'], ['locales.local_id'], ),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fecha', 'local_id', name='uq_sf_fecha_local'),
    )


def downgrade() -> None:
    op.drop_table('sobrantes_faltantes')
