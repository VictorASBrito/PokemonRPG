"""Reconcilia a CHECK do perfil Tester nos bancos PostgreSQL existentes.

Revision ID: b72cf044e6ad
Revises: 3a8e5c71d902

A revisao anterior introduziu Tester no modelo e na migracao normal.
Esta revisao de reparo corrige bancos cuja revisao Alembic tenha sido
marcada ou alterada sem atualizar efetivamente a CHECK de usuarios.
"""

from alembic import op
import sqlalchemy as sa

revision = "b72cf044e6ad"
down_revision = "3a8e5c71d902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # Este reparo é específico de uma constraint legada do PostgreSQL.
        return

    # Nunca apague usuarios ou reclassifique suas contas silenciosamente.
    perfis_inesperados = bind.execute(sa.text("""
        SELECT DISTINCT perfil FROM usuarios
        WHERE perfil NOT IN ('administrador', 'mestre', 'tester', 'jogador')
    """)).scalars().all()
    if perfis_inesperados:
        raise RuntimeError(
            "Existem perfis não reconhecidos em usuarios: "
            + ", ".join(map(str, perfis_inesperados))
        )

    # DROP/ADD são DDL transacional no PostgreSQL: o Alembic reverte
    # ambas as operações se qualquer uma falhar.
    op.execute("ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS ck_usuarios_perfil_valido")
    op.execute("""
        ALTER TABLE usuarios
        ADD CONSTRAINT ck_usuarios_perfil_valido
        CHECK (perfil IN ('administrador', 'mestre', 'tester', 'jogador'))
    """)


def downgrade() -> None:
    # A revisão 3a8e5c71d902 já aceita Tester. Reverter este reparo não
    # deve restaurar a CHECK defeituosa, nem invalidar usuários.
    pass
