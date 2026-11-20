"""Teste da migration sem tocar no PostgreSQL do usuário."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

ROOT = Path(__file__).resolve().parents[1]


def test_migration_npc_catalogo_upgrade_e_downgrade():
    path = ROOT / "migrations/versions/e31a6cf520d4_catalogo_npcs_regional.py"
    spec = importlib.util.spec_from_file_location("migration_regional", path)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert modulo.down_revision == "c84f2b1a7d90"
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    for table in ("campanhas", "personagens", "naturezas", "formas_pokemon"):
        sa.Table(table, metadata, sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True))
    sa.Table("grupos_npc_campo", metadata,
             sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True))
    sa.Table("pokemons_npc_campo", metadata,
             sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True))
    with engine.begin() as conn:
        metadata.create_all(conn)
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            modulo.upgrade()
        assert "npcs_catalogo" in sa.inspect(conn).get_table_names()
        assert {"modelo_id", "local_id", "encontrado_por_personagem_id"}.issubset(
            {col["name"] for col in sa.inspect(conn).get_columns("grupos_npc_campo")}
        )
        assert {"natureza_id", "genero", "enviado_captura"}.issubset(
            {col["name"] for col in sa.inspect(conn).get_columns("pokemons_npc_campo")}
        )
        with Operations.context(ctx):
            modulo.downgrade()
        assert "npcs_catalogo" not in sa.inspect(conn).get_table_names()
