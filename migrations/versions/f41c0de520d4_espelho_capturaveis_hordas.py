"""Ligação única de Capturáveis com Pokémon NPC em horda.

Revision ID: f41c0de520d4
Revises: e31a6cf520d4
"""
from alembic import op
import sqlalchemy as sa

revision = "f41c0de520d4"
down_revision = "e31a6cf520d4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pokemons_npc_campo") as batch:
        batch.add_column(sa.Column("capturavel_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.create_foreign_key(
            "fk_pokemon_npc_capturavel", "pokemons_capturaveis",
            ["capturavel_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_pokemons_npc_campo_capturavel_id", ["capturavel_id"], unique=True)


def downgrade():
    with op.batch_alter_table("pokemons_npc_campo") as batch:
        batch.drop_index("ix_pokemons_npc_campo_capturavel_id")
        batch.drop_constraint("fk_pokemon_npc_capturavel", type_="foreignkey")
        batch.drop_column("capturavel_id")
