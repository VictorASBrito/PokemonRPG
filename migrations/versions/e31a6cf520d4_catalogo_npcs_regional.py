"""Catálogo NPC fixo e geração regional / captura de hordas.

Revision ID: e31a6cf520d4
Revises: c84f2b1a7d90
"""
from alembic import op
import sqlalchemy as sa
from app.models.db.base import JSON_DOCUMENT

revision = "e31a6cf520d4"
down_revision = "c84f2b1a7d90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "npcs_catalogo",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("campanha_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("local_id", sa.String(120), nullable=False),
        sa.Column("zona_nome", sa.String(120), nullable=False),
        sa.Column("terreno", sa.String(120), nullable=False),
        sa.Column("equipe", JSON_DOCUMENT, nullable=False),
    )
    op.create_index("ix_npcs_catalogo_campanha_id", "npcs_catalogo", ["campanha_id"])
    with op.batch_alter_table("grupos_npc_campo") as batch:
        batch.add_column(sa.Column("modelo_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.add_column(sa.Column("encontrado_por_personagem_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.add_column(sa.Column("local_id", sa.String(120), nullable=True))
        batch.add_column(sa.Column("zona_nome", sa.String(120), nullable=True))
        batch.add_column(sa.Column("terreno", sa.String(120), nullable=True))
        batch.create_foreign_key("fk_grupo_npc_modelo", "npcs_catalogo", ["modelo_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_grupo_npc_encontrador", "personagens", ["encontrado_por_personagem_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_grupos_npc_campo_modelo_id", ["modelo_id"])
        batch.create_index("ix_grupos_npc_campo_encontrado_por_personagem_id", ["encontrado_por_personagem_id"])
    with op.batch_alter_table("pokemons_npc_campo") as batch:
        batch.add_column(sa.Column("natureza_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.add_column(sa.Column("genero", sa.String(40), nullable=True))
        batch.add_column(sa.Column("enviado_captura", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_foreign_key("fk_pokemon_npc_natureza", "naturezas", ["natureza_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_pokemons_npc_campo_natureza_id", ["natureza_id"])


def downgrade():
    with op.batch_alter_table("pokemons_npc_campo") as batch:
        batch.drop_index("ix_pokemons_npc_campo_natureza_id")
        batch.drop_constraint("fk_pokemon_npc_natureza", type_="foreignkey")
        batch.drop_column("enviado_captura")
        batch.drop_column("genero")
        batch.drop_column("natureza_id")
    with op.batch_alter_table("grupos_npc_campo") as batch:
        batch.drop_index("ix_grupos_npc_campo_modelo_id")
        batch.drop_index("ix_grupos_npc_campo_encontrado_por_personagem_id")
        batch.drop_constraint("fk_grupo_npc_modelo", type_="foreignkey")
        batch.drop_constraint("fk_grupo_npc_encontrador", type_="foreignkey")
        batch.drop_column("terreno")
        batch.drop_column("zona_nome")
        batch.drop_column("local_id")
        batch.drop_column("encontrado_por_personagem_id")
        batch.drop_column("modelo_id")
    op.drop_index("ix_npcs_catalogo_campanha_id", table_name="npcs_catalogo")
    op.drop_table("npcs_catalogo")
