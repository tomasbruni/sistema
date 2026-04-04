"""entregar pedido: venta online, precio_unitario en detalles pedido

Revision ID: b4c5d6e7f8a9
Revises: 7a7b7280f3cd
Create Date: 2026-04-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = '4cd3470f5cb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # FK de ventas → pedidos_online (nullable, solo para ventas tipo ONLINE)
    op.add_column('ventas', sa.Column('pedido_online_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_ventas_pedido_online_id',
        'ventas', 'pedidos_online',
        ['pedido_online_id'], ['pedido_id']
    )

    # precio_unitario en detalles_pedidos_accesorios (precio de venta, puede diferir de precio_lista)
    op.add_column('detalles_pedidos_accesorios',
        sa.Column('precio_unitario', sa.Integer(), nullable=False, server_default='0'))

    # precio_lista snapshot en detalles_pedidos_celulares y chips
    op.add_column('detalles_pedidos_celulares',
        sa.Column('precio_lista', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('detalles_pedidos_chips',
        sa.Column('precio_lista', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('detalles_pedidos_chips', 'precio_lista')
    op.drop_column('detalles_pedidos_celulares', 'precio_lista')
    op.drop_column('detalles_pedidos_accesorios', 'precio_unitario')
    op.drop_constraint('fk_ventas_pedido_online_id', 'ventas', type_='foreignkey')
    op.drop_column('ventas', 'pedido_online_id')
