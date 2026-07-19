"""permitir PV negativo do personagem

Revision ID: 7c4b1f91a2d3
Revises: 10e0d7901486
Create Date: 2026-07-19 06:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c4b1f91a2d3"
down_revision: Union[str, Sequence[str], None] = "10e0d7901486"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "ck_personagens_pv_atual_nao_negativo"


def upgrade() -> None:
    # op.f() informa ao Alembic que este já é o nome final da constraint.
    # Sem isso, a naming convention adiciona novamente o prefixo da tabela.
    op.drop_constraint(
        op.f(CONSTRAINT_NAME),
        "personagens",
        type_="check",
    )


def downgrade() -> None:
    op.create_check_constraint(
        op.f(CONSTRAINT_NAME),
        "personagens",
        sa.text("pv_atual >= 0"),
    )
