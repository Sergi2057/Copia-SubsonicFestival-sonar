"""variantes activas

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-09
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # server_default: las variantes que ya existen quedan activas
    op.add_column('variantes', sa.Column('activa', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    # batch: SQLite (tests) recrea la tabla; PostgreSQL hace un DROP COLUMN normal
    with op.batch_alter_table('variantes') as tabla:
        tabla.drop_column('activa')
