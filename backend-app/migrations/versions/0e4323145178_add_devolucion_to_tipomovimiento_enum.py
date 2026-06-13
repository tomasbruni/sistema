"""add DEVOLUCION to tipomovimiento enum

Revision ID: 0e4323145178
Revises: ccf043d7c6aa
Create Date: 2026-06-12 11:10:12.584775

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0e4323145178'
down_revision: Union[str, Sequence[str], None] = 'ccf043d7c6aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agrega el valor DEVOLUCION al enum nativo `tipomovimiento`.
    # Esta migración debe ir SOLA: Postgres no permite usar un valor de enum
    # recién agregado dentro de la misma transacción donde se agrega.
    op.execute("ALTER TYPE tipomovimiento ADD VALUE IF NOT EXISTS 'DEVOLUCION' AFTER 'VENTA'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres no soporta quitar un valor de un enum sin recrear el tipo
    # (y reasignar todas las columnas que lo usan). Se deja como no-op:
    # el valor DEVOLUCION es inofensivo si queda presente.
    pass
