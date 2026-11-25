"""esquema inicial de tienda

Revision ID: 0001
Revises:
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('pedidos',
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('usuario_id', sa.String(length=128), nullable=False),
    sa.Column('importe_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('entrega', sa.String(length=20), nullable=False),
    sa.Column('direccion_envio', sa.Text(), nullable=True),
    sa.Column('evento_id_recogida', sa.String(length=100), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('pago_ref', sa.String(length=100), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pedidos_usuario_id'), 'pedidos', ['usuario_id'], unique=False)
    op.create_table('productos',
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('precio', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('imagen_url', sa.String(length=500), nullable=True),
    sa.Column('evento_id', sa.String(length=100), nullable=True),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('variantes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('producto_id', sa.String(length=50), nullable=False),
    sa.Column('talla', sa.String(length=10), nullable=False),
    sa.Column('stock', sa.Integer(), nullable=False),
    sa.CheckConstraint('stock >= 0', name='ck_variante_stock_no_negativo'),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('producto_id', 'talla', name='uq_variante_producto_talla')
    )
    op.create_table('lineas_pedido',
    sa.Column('pedido_id', sa.String(length=50), nullable=False),
    sa.Column('variante_id', sa.Uuid(), nullable=False),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.Column('precio_unitario', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ),
    sa.ForeignKeyConstraint(['variante_id'], ['variantes.id'], ),
    sa.PrimaryKeyConstraint('pedido_id', 'variante_id')
    )


def downgrade():
    op.drop_table('lineas_pedido')
    op.drop_table('variantes')
    op.drop_table('productos')
    op.drop_index(op.f('ix_pedidos_usuario_id'), table_name='pedidos')
    op.drop_table('pedidos')
