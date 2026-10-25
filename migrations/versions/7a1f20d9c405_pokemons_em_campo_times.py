"""Campo compartilhado com até 16 times.

Revision ID: 7a1f20d9c405
Revises: 6f355a4d5b2e
"""
from alembic import op
import sqlalchemy as sa

revision = "7a1f20d9c405"
down_revision = "6f355a4d5b2e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pokemons_em_campo",
        sa.Column("campanha_id", sa.Uuid(), nullable=False),
        sa.Column("pokemon_id", sa.Uuid(), nullable=False),
        sa.Column("time_numero", sa.SmallInteger(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campanha_id"], ["campanhas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pokemon_id"], ["pokemons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pokemon_id", name="pokemon_unico_no_campo"),
        sa.CheckConstraint("time_numero BETWEEN 1 AND 16", name=op.f("ck_pokemons_em_campo_time_valido")),
    )
    op.create_index("ix_pokemons_em_campo_campanha_id", "pokemons_em_campo", ["campanha_id"])
    op.create_index("ix_pokemons_em_campo_pokemon_id", "pokemons_em_campo", ["pokemon_id"])


def downgrade() -> None:
    op.drop_index("ix_pokemons_em_campo_pokemon_id", table_name="pokemons_em_campo")
    op.drop_index("ix_pokemons_em_campo_campanha_id", table_name="pokemons_em_campo")
    op.drop_table("pokemons_em_campo")
