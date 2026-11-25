"""esquema inicial de escaleta

Revision ID: 0001
Revises:
Create Date: 2026-11-01

Generada con --autogenerate y revisada a mano:
- JSONB(astext_type=Text()) -> sa.Text(), que el autogenerado no importa.
- Añadidas la extensión btree_gist y la restricción de exclusión ex_slots_sin_solape, que el
  autogenerado no detecta. Solo en PostgreSQL: los tests usan SQLite, que no las tiene.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

DatosJSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade():
    op.create_table('artistas',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=255), nullable=False),
    sa.Column('generos', DatosJSON, nullable=False),
    sa.Column('pais', sa.String(length=100), nullable=True),
    sa.Column('biografia', sa.Text(), nullable=True),
    sa.Column('imagen_url', sa.String(length=500), nullable=True),
    sa.Column('youtube_channel_id', sa.String(length=100), nullable=True),
    sa.Column('redes', DatosJSON, nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_artistas_nombre'), 'artistas', ['nombre'], unique=False)
    op.create_table('escenarios',
    sa.Column('espacio_id', sa.String(length=50), nullable=False),
    sa.Column('evento_id', sa.String(length=100), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('aforo', sa.Integer(), nullable=True),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('espacio_id')
    )
    op.create_index(op.f('ix_escenarios_evento_id'), 'escenarios', ['evento_id'], unique=False)
    op.create_table('eventos',
    sa.Column('evento_id', sa.String(length=100), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('evento_id')
    )
    op.create_table('publicaciones',
    sa.Column('evento_id', sa.String(length=100), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('publicada_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('publicada_por', sa.String(length=128), nullable=False),
    sa.Column('instantanea', DatosJSON, nullable=False),
    sa.PrimaryKeyConstraint('evento_id', 'version')
    )
    op.create_table('slots',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('evento_id', sa.String(length=100), nullable=False),
    sa.Column('espacio_id', sa.String(length=50), nullable=False),
    sa.Column('inicio', sa.DateTime(timezone=True), nullable=False),
    sa.Column('fin', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.CheckConstraint('fin > inicio', name='ck_slot_fin_posterior'),
    sa.ForeignKeyConstraint(['espacio_id'], ['escenarios.espacio_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slots_evento_id'), 'slots', ['evento_id'], unique=False)

    # Dos slots del mismo escenario no pueden solaparse en el tiempo. La garantiza la propia base
    # de datos aunque lleguen dos peticiones a la vez (antes estaba en config/database.py).
    if op.get_context().dialect.name == 'postgresql':
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        op.execute("ALTER TABLE slots ADD CONSTRAINT ex_slots_sin_solape "
                   "EXCLUDE USING gist (espacio_id WITH =, tstzrange(inicio, fin) WITH &&)")

    op.create_table('pases',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('slot_id', sa.Uuid(), nullable=False),
    sa.Column('artista_id', sa.Uuid(), nullable=False),
    sa.Column('formato', sa.String(length=20), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('notas_tecnicas', sa.Text(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['artista_id'], ['artistas.id'], ),
    sa.ForeignKeyConstraint(['slot_id'], ['slots.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slot_id')
    )
    op.create_index(op.f('ix_pases_artista_id'), 'pases', ['artista_id'], unique=False)


def downgrade():
    # La restricción de exclusión se borra con la tabla slots. La extensión btree_gist se deja:
    # no pertenece a ninguna tabla y no estorba.
    op.drop_index(op.f('ix_pases_artista_id'), table_name='pases')
    op.drop_table('pases')
    op.drop_index(op.f('ix_slots_evento_id'), table_name='slots')
    op.drop_table('slots')
    op.drop_table('publicaciones')
    op.drop_table('eventos')
    op.drop_index(op.f('ix_escenarios_evento_id'), table_name='escenarios')
    op.drop_table('escenarios')
    op.drop_index(op.f('ix_artistas_nombre'), table_name='artistas')
    op.drop_table('artistas')
