"""drop sku column accesorios

Revision ID: a1b2c3d4e5f6
Revises: 8e924056f58f
Create Date: 2026-04-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '8e924056f58f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f('ix_accesorios_sku'), table_name='accesorios')
    op.drop_column('accesorios', 'sku')


def downgrade() -> None:
    op.add_column('accesorios', sa.Column('sku', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
    op.create_index(op.f('ix_accesorios_sku'), 'accesorios', ['sku'], unique=True)
