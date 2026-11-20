"""Migração da ficha NPC, upgrade/downgrade isolado."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext


def test_migration_ficha_npc_upgrade_downgrade():
    root = Path(__file__).resolve().parents[1]
    path = root / "migrations/versions/a14d4e4044a1_ficha_npcs_fixos.py"
    spec = importlib.util.spec_from_file_location("mig_npc_ficha", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.revision == "a14d4e4044a1"
    assert m.down_revision == "f41c0de520d4"
    eng = sa.create_engine("sqlite+pysqlite:///:memory:")
    md = sa.MetaData()
    sa.Table("npcs_catalogo", md,
             sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True))
    with eng.begin() as con:
        md.create_all(con)
        ctx = MigrationContext.configure(con)
        with Operations.context(ctx):
            m.upgrade()
        cols = {x["name"] for x in sa.inspect(con).get_columns("npcs_catalogo")}
        assert {"nivel", "classe", "origem", "foto_url", "anotacoes", "atributos", "pv_atual"} <= cols
        with Operations.context(ctx):
            m.downgrade()
        cols = {x["name"] for x in sa.inspect(con).get_columns("npcs_catalogo")}
        assert cols == {"id"}
