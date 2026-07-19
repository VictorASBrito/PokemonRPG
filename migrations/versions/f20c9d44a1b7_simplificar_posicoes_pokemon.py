"""simplificar restrição de posições dos Pokémon

Revision ID: f20c9d44a1b7
Revises: 7c4b1f91a2d3
Create Date: 2026-07-19 14:30:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f20c9d44a1b7"
down_revision: Union[str, Sequence[str], None] = "7c4b1f91a2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "personagem_localizacao_posicao"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "pokemons", type_="unique")
    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "pokemons",
        ["personagem_id", "localizacao", "posicao"],
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "pokemons", type_="unique")
    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "pokemons",
        ["personagem_id", "localizacao", "posicao"],
        deferrable=True,
        initially="DEFERRED",
    )
