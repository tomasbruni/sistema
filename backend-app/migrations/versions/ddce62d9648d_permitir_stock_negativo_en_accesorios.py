"""permitir stock negativo en accesorios

Revision ID: ddce62d9648d
Revises: 0e4323145178
Create Date: 2026-06-13 20:34:55.654403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ddce62d9648d'
down_revision: Union[str, Sequence[str], None] = '0e4323145178'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Se elimina el CheckConstraint cantidad >= 0 para permitir que las ventas
    # dejen el stock en negativo ante errores de conteo (producto presente
    # físicamente pero no cargado). El negativo es señal de auditoría.
    op.drop_constraint(
        'ck_stock_accesorios_cantidad_no_negativa',
        'stock_accesorios',
        type_='check',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_check_constraint(
        'ck_stock_accesorios_cantidad_no_negativa',
        'stock_accesorios',
        'cantidad >= 0',
    )
