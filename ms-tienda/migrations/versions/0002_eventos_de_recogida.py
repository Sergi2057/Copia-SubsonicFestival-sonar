"""eventos de recogida

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('eventos_recogida',
    sa.Column('evento_id', sa.String(length=100), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('evento_id')
    )


def downgrade():
    op.drop_table('eventos_recogida')
