"""NPCs e hordas temporários no Campo.

Revision ID: c84f2b1a7d90
Revises: 7a1f20d9c405
"""
from alembic import op
import sqlalchemy as sa

revision = "c84f2b1a7d90"
down_revision = "7a1f20d9c405"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "grupos_npc_campo",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("campanha_id", sa.Uuid(as_uuid=True), sa.ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("time_numero", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("tipo IN ('npc', 'horda')", name="ck_grupos_npc_campo_tipo_valido"),
        sa.CheckConstraint("time_numero BETWEEN 1 AND 16", name="ck_grupos_npc_campo_time_valido"),
    )
    op.create_index("ix_grupos_npc_campo_campanha_id", "grupos_npc_campo", ["campanha_id"])
    op.create_table(
        "pokemons_npc_campo",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("grupo_id", sa.Uuid(as_uuid=True), sa.ForeignKey("grupos_npc_campo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("forma_pokemon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("formas_pokemon.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nivel", sa.SmallInteger(), nullable=False),
        sa.Column("pv_maximo", sa.Integer(), nullable=False),
        sa.Column("pv_atual", sa.Integer(), nullable=False),
        sa.Column("shiny", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint("nivel BETWEEN 1 AND 100", name="ck_pokemons_npc_campo_nivel_valido"),
        sa.CheckConstraint("pv_maximo >= 1", name="ck_pokemons_npc_campo_pv_maximo_valido"),
        sa.CheckConstraint("pv_atual BETWEEN 0 AND pv_maximo", name="ck_pokemons_npc_campo_pv_atual_valido"),
    )
    op.create_index("ix_pokemons_npc_campo_grupo_id", "pokemons_npc_campo", ["grupo_id"])
    op.create_index("ix_pokemons_npc_campo_forma_pokemon_id", "pokemons_npc_campo", ["forma_pokemon_id"])


def downgrade():
    op.drop_index("ix_pokemons_npc_campo_forma_pokemon_id", table_name="pokemons_npc_campo")
    op.drop_index("ix_pokemons_npc_campo_grupo_id", table_name="pokemons_npc_campo")
    op.drop_table("pokemons_npc_campo")
    op.drop_index("ix_grupos_npc_campo_campanha_id", table_name="grupos_npc_campo")
    op.drop_table("grupos_npc_campo")
