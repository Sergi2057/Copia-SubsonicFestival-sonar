"""registro de eventos procesados

Revision ID: 9f82a5d31c6e
Revises: 252a6562f75f
Create Date: 2026-11-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f82a5d31c6e"
down_revision: Union[str, Sequence[str], None] = "252a6562f75f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eventos_procesados",
        sa.Column("id_evento", sa.String(length=128), nullable=False),
        sa.Column("tipo", sa.String(length=120), nullable=False),
        sa.Column("procesado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id_evento"),
    )


def downgrade() -> None:
    op.drop_table("eventos_procesados")