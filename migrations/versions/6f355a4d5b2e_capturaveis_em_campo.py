"""capturáveis em campo

Revision ID: 6f355a4d5b2e
Revises: b72cf044e6ad
Create Date: 2026-10-23 21:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f355a4d5b2e"
down_revision: Union[str, Sequence[str], None] = "b72cf044e6ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pokemons_capturaveis",
        sa.Column("campanha_id", sa.Uuid(), nullable=False),
        sa.Column("forma_pokemon_id", sa.Uuid(), nullable=False),
        sa.Column("encontrado_por_personagem_id", sa.Uuid(), nullable=True),
        sa.Column("natureza_id", sa.Uuid(), nullable=True),
        sa.Column("genero", sa.String(length=40), nullable=True),
        sa.Column("shiny", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ordem", sa.SmallInteger(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["campanha_id"], ["campanhas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["forma_pokemon_id"], ["formas_pokemon.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encontrado_por_personagem_id"], ["personagens.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["natureza_id"], ["naturezas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campanha_id", "ordem", name="campanha_ordem_capturavel"),
    )
    op.create_check_constraint(
        op.f("ck_pokemons_capturaveis_ordem_capturavel_valida"),
        "pokemons_capturaveis",
        "ordem IS NULL OR (ordem >= 1 AND ordem <= 15)",
    )
    op.create_index(op.f("ix_pokemons_capturaveis_campanha_id"), "pokemons_capturaveis", ["campanha_id"], unique=False)
    op.create_index(op.f("ix_pokemons_capturaveis_forma_pokemon_id"), "pokemons_capturaveis", ["forma_pokemon_id"], unique=False)
    op.create_index(op.f("ix_pokemons_capturaveis_encontrado_por_personagem_id"), "pokemons_capturaveis", ["encontrado_por_personagem_id"], unique=False)
    op.create_index(op.f("ix_pokemons_capturaveis_natureza_id"), "pokemons_capturaveis", ["natureza_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pokemons_capturaveis_natureza_id"), table_name="pokemons_capturaveis")
    op.drop_index(op.f("ix_pokemons_capturaveis_encontrado_por_personagem_id"), table_name="pokemons_capturaveis")
    op.drop_index(op.f("ix_pokemons_capturaveis_forma_pokemon_id"), table_name="pokemons_capturaveis")
    op.drop_index(op.f("ix_pokemons_capturaveis_campanha_id"), table_name="pokemons_capturaveis")
    op.drop_constraint(op.f("ck_pokemons_capturaveis_ordem_capturavel_valida"), "pokemons_capturaveis", type_="check")
    op.drop_table("pokemons_capturaveis")
