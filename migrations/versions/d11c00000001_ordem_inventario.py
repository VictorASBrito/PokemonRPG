"""Preferência de ordem dos itens de cada personagem.

Revision ID: d11c00000001
Revises: c42e10040001
"""
from alembic import op
import sqlalchemy as sa

revision = "d11c00000001"
down_revision = "c42e10040001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("personagem_itens", sa.Column("ordem_bolsa", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("personagem_itens", "ordem_bolsa")
