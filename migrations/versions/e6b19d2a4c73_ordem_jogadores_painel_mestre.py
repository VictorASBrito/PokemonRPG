"""ordem dos jogadores no painel do mestre

Revision ID: e6b19d2a4c73
Revises: d94c7ab20e51
Create Date: 2026-08-12 21:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6b19d2a4c73"
down_revision: Union[str, Sequence[str], None] = "d94c7ab20e51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("personagens", sa.Column("ordem_painel", sa.Integer(), nullable=True))
    op.create_check_constraint(
        op.f("ck_personagens_ordem_painel_positiva"),
        "personagens",
        "ordem_painel IS NULL OR ordem_painel > 0",
    )
    op.create_index(
        "ix_personagens_campanha_ordem_painel",
        "personagens",
        ["campanha_id", "ordem_painel"],
        unique=False,
    )
    # Preserva uma ordem inicial previsível para cada campanha. O mestre pode
    # reorganizá-la depois pelo próprio painel.
    op.execute(
        """
        WITH ordenados AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY campanha_id
                       ORDER BY LOWER(nome), id
                   ) AS nova_ordem
              FROM personagens
             WHERE ativo = true
        )
        UPDATE personagens AS p
           SET ordem_painel = ordenados.nova_ordem
          FROM ordenados
         WHERE p.id = ordenados.id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_personagens_campanha_ordem_painel", table_name="personagens")
    op.drop_constraint(
        op.f("ck_personagens_ordem_painel_positiva"),
        "personagens",
        type_="check",
    )
    op.drop_column("personagens", "ordem_painel")
