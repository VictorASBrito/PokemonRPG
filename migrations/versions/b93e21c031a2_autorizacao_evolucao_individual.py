"""Autorização individual de evolução por Pokémon e relação.

Revision ID: b93e21c031a2
Revises: a14d4e4044a1
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = "b93e21c031a2"
down_revision = "a14d4e4044a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "autorizacoes_evolucao_pokemon",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("pokemon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("pokemons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relacao_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evolucoes_pokemon.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("forma_origem_id", sa.Uuid(as_uuid=True), sa.ForeignKey("formas_pokemon.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("autorizado_por_id", sa.Uuid(as_uuid=True), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("justificativa", sa.Text(), nullable=False),
        sa.Column("autorizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revogado_por_id", sa.Uuid(as_uuid=True), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("motivo_revogacao", sa.Text(), nullable=True),
        sa.UniqueConstraint("pokemon_id", "relacao_id", name="autorizacao_pokemon_relacao"),
    )
    op.create_index("ix_autorizacoes_evolucao_pokemon_pokemon_id", "autorizacoes_evolucao_pokemon", ["pokemon_id"])
    op.create_index("ix_autorizacoes_evolucao_pokemon_relacao_id", "autorizacoes_evolucao_pokemon", ["relacao_id"])
    op.create_index("ix_autorizacoes_evolucao_pokemon_ativo", "autorizacoes_evolucao_pokemon", ["pokemon_id", "ativo"])


def downgrade():
    # Nunca descartar autorizações reais e seu histórico por engano.
    bind = op.get_bind()
    total = bind.execute(
        sa.text("SELECT COUNT(*) FROM autorizacoes_evolucao_pokemon")
    ).scalar_one()
    if total:
        raise RuntimeError(
            "Há autorizações evolutivas registradas. "
            "Exporte e revise os dados antes de desfazer esta migration."
        )
    op.drop_index("ix_autorizacoes_evolucao_pokemon_ativo", table_name="autorizacoes_evolucao_pokemon")
    op.drop_index("ix_autorizacoes_evolucao_pokemon_relacao_id", table_name="autorizacoes_evolucao_pokemon")
    op.drop_index("ix_autorizacoes_evolucao_pokemon_pokemon_id", table_name="autorizacoes_evolucao_pokemon")
    op.drop_table("autorizacoes_evolucao_pokemon")
