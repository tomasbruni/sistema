"""add server default fecha sobrantes faltantes

Revision ID: 560d2f6cdcb5
Revises: 6b0793048989
Create Date: 2026-04-07 22:27:53.996801

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '560d2f6cdcb5'
down_revision: Union[str, Sequence[str], None] = '6b0793048989'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'sobrantes_faltantes', 'fecha',
        server_default=sa.text('CURRENT_DATE'),
        existing_type=sa.Date(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'sobrantes_faltantes', 'fecha',
        server_default=None,
        existing_type=sa.Date(),
        nullable=False,
    )
