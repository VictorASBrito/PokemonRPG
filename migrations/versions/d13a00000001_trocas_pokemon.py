"""Adiciona negociações de Pokémon sem alterar registros existentes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d13a00000001"
down_revision = "d12a00000001"
branch_labels = None
depends_on = None


def upgrade():
    documento = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "trocas_pokemon",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("campanha_id", sa.Uuid(), sa.ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proponente_id", sa.Uuid(), sa.ForeignKey("personagens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destinatario_id", sa.Uuid(), sa.ForeignKey("personagens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("estado", sa.String(20), server_default="pendente", nullable=False),
        sa.Column("revisao", sa.Integer(), server_default="0", nullable=False),
        sa.Column("versao_lock", sa.Integer(), server_default="1", nullable=False),
        sa.Column("oferta_a", documento, nullable=False),
        sa.Column("oferta_b", documento, nullable=False),
        sa.Column("confirmou_a", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("confirmou_b", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint("proponente_id <> destinatario_id", name="participantes_distintos"),
        sa.CheckConstraint("estado IN ('pendente', 'negociacao', 'concluida', 'recusada', 'cancelada')", name="estado_valido"),
        sa.CheckConstraint("revisao >= 0", name="revisao_valida"),
    )
    for coluna in ("campanha_id", "proponente_id", "destinatario_id"):
        op.create_index("ix_trocas_pokemon_" + coluna, "trocas_pokemon", [coluna])


def downgrade():
    for coluna in ("campanha_id", "proponente_id", "destinatario_id"):
        op.drop_index("ix_trocas_pokemon_" + coluna, table_name="trocas_pokemon")
    op.drop_table("trocas_pokemon")
