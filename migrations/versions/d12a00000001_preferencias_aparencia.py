"""Preferências de aparência opcionais por personagem e conta do mestre."""
from alembic import op
import sqlalchemy as sa

revision = "d12a00000001"
down_revision = "d11c00000001"
branch_labels = None
depends_on = None


def upgrade():
    for tabela in ("personagens", "usuarios"):
        op.add_column(tabela, sa.Column("aparencia_modo", sa.String(10), nullable=True))
        op.add_column(tabela, sa.Column("aparencia_paleta", sa.String(24), nullable=True))


def downgrade():
    for tabela in ("usuarios", "personagens"):
        op.drop_column(tabela, "aparencia_paleta")
        op.drop_column(tabela, "aparencia_modo")
