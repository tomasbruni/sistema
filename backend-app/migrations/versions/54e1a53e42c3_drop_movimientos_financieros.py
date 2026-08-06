"""drop movimientos_financieros

Revision ID: 54e1a53e42c3
Revises: f5c6f1b7c577
Create Date: 2026-08-04 11:58:30.355229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '54e1a53e42c3'
down_revision: Union[str, Sequence[str], None] = 'f5c6f1b7c577'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('movimientos_financieros')
    sa.Enum('INGRESO', 'EGRESO', name='tipomovimientofinanciero').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'movimientos_financieros',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.Enum('INGRESO', 'EGRESO', name='tipomovimientofinanciero'), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
