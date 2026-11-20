"""Overlay de forma temporária e permissão de Mega no treinador.

Revision ID: c42e10040001
Revises: b93e21c031a2
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = "c42e10040001"
down_revision = "b93e21c031a2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "personagens",
        sa.Column("mega_habilitada", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )
    op.add_column(
        "pokemons",
        sa.Column("forma_temporaria_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pokemons",
        sa.Column("tipo_transformacao", sa.String(length=20), nullable=True),
    )
    op.create_foreign_key(
        "fk_pokemons_forma_temporaria", "pokemons", "formas_pokemon",
        ["forma_temporaria_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_pokemons_forma_temporaria_id", "pokemons", ["forma_temporaria_id"])
    op.create_check_constraint(
        "transformacao_temporaria_coerente", "pokemons",
        "(forma_temporaria_id IS NULL AND tipo_transformacao IS NULL) OR "
        "(forma_temporaria_id IS NOT NULL AND tipo_transformacao IN ('mega', 'alternativa'))",
    )


def downgrade():
    bind = op.get_bind()
    ativas = bind.execute(sa.text(
        "SELECT COUNT(*) FROM pokemons WHERE forma_temporaria_id IS NOT NULL"
    )).scalar_one()
    liberacoes = bind.execute(sa.text(
        "SELECT COUNT(*) FROM personagens WHERE mega_habilitada = true"
    )).scalar_one()
    if ativas or liberacoes:
        raise RuntimeError(
            "Existem transformações ou permissões Mega ativas. "
            "Faça backup e reverta essas decisões conscientemente antes de downgrade."
        )
    op.drop_constraint("transformacao_temporaria_coerente", "pokemons", type_="check")
    op.drop_index("ix_pokemons_forma_temporaria_id", table_name="pokemons")
    op.drop_constraint("fk_pokemons_forma_temporaria", "pokemons", type_="foreignkey")
    op.drop_column("pokemons", "tipo_transformacao")
    op.drop_column("pokemons", "forma_temporaria_id")
    op.drop_column("personagens", "mega_habilitada")
