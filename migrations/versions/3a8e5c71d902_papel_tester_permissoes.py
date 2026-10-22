"""Adiciona o perfil tester mantendo administrador/mestre intactos.

Revision ID: 3a8e5c71d902
Revises: e6b19d2a4c73
"""
from alembic import op
import sqlalchemy as sa

revision = "3a8e5c71d902"
down_revision = "e6b19d2a4c73"
branch_labels = None
depends_on = None
NOME = "ck_usuarios_perfil_valido"


def upgrade() -> None:
    op.drop_constraint(op.f(NOME), "usuarios", type_="check")
    op.create_check_constraint(
        op.f(NOME), "usuarios",
        "perfil IN ('administrador', 'mestre', 'tester', 'jogador')",
    )


def downgrade() -> None:
    # Impede excluir o perfil tester enquanto ainda houver usuários nele.
    # Reclassifique-os explicitamente como jogadores antes do downgrade.
    conexao = op.get_bind()
    total = conexao.execute(sa.text("SELECT count(*) FROM usuarios WHERE perfil = 'tester'")).scalar()
    if total:
        raise RuntimeError("Reclassifique os usuários tester como jogador antes do downgrade.")
    op.drop_constraint(op.f(NOME), "usuarios", type_="check")
    op.create_check_constraint(
        op.f(NOME), "usuarios",
        "perfil IN ('administrador', 'mestre', 'jogador')",
    )
