"""corrigir percentuais das naturezas

Revision ID: a31d7e8c4f20
Revises: f20c9d44a1b7
Create Date: 2026-07-19 15:45:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a31d7e8c4f20"
down_revision: Union[str, Sequence[str], None] = "f20c9d44a1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Converte valores importados como 10/-10 para 0.10/-0.10."""
    op.execute(
        """
        UPDATE natureza_modificadores
           SET valor = valor / 100
         WHERE tipo_modificador = 'percentual'
           AND ABS(valor) > 1
        """
    )


def downgrade() -> None:
    """Restaura o formato legado usado pela importação inicial."""
    op.execute(
        """
        UPDATE natureza_modificadores
           SET valor = valor * 100
         WHERE tipo_modificador = 'percentual'
           AND valor IN (0.100, -0.100)
        """
    )
