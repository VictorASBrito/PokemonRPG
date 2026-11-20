"""Ficha de NPC fixo: Vida, Status, identificação e anotações.

Revision ID: a14d4e4044a1
Revises: f41c0de520d4
"""
from alembic import op
import sqlalchemy as sa
from app.models.db.base import JSON_DOCUMENT

revision = "a14d4e4044a1"
down_revision = "f41c0de520d4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("npcs_catalogo") as batch:
        batch.add_column(sa.Column("nivel", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("classe", sa.String(160), nullable=True))
        batch.add_column(sa.Column("origem", sa.String(160), nullable=True))
        batch.add_column(sa.Column("foto_url", sa.String(500), nullable=True))
        batch.add_column(sa.Column("anotacoes", sa.Text(), nullable=True))
        batch.add_column(sa.Column("atributos", JSON_DOCUMENT, nullable=True))
        batch.add_column(sa.Column("pv_atual", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("npcs_catalogo") as batch:
        batch.drop_column("pv_atual")
        batch.drop_column("atributos")
        batch.drop_column("anotacoes")
        batch.drop_column("foto_url")
        batch.drop_column("origem")
        batch.drop_column("classe")
        batch.drop_column("nivel")
