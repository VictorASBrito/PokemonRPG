"""catálogo de itens e inventário administrável

Revision ID: d94c7ab20e51
Revises: a31d7e8c4f20
Create Date: 2026-07-20 02:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d94c7ab20e51"
down_revision: Union[str, Sequence[str], None] = "a31d7e8c4f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "itens",
        sa.Column("preco", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "itens",
        sa.Column("consumivel", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "itens",
        sa.Column("equipavel", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "itens",
        sa.Column("uso_em_batalha", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_itens_preco_nao_negativo"),
        "itens",
        "preco >= 0",
    )
    # Preserva os itens que já estavam carregados por Pokémon antes desta
    # etapa. Eles passam a ser considerados equipáveis sem exigir reimportação.
    op.execute(
        """
        UPDATE itens
           SET equipavel = true
         WHERE id IN (
               SELECT DISTINCT item_equipado_id
                 FROM pokemons
                WHERE item_equipado_id IS NOT NULL
         )
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_itens_preco_nao_negativo"),
        "itens",
        type_="check",
    )
    op.drop_column("itens", "uso_em_batalha")
    op.drop_column("itens", "equipavel")
    op.drop_column("itens", "consumivel")
    op.drop_column("itens", "preco")
