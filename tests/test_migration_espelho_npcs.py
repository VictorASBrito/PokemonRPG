"""Migration f41c0de520d4 — coluna de vínculo e reversão isolada."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext


def test_upgrade_downgrade_vinculo_capturavel():
    path = Path(__file__).resolve().parents[1] / "migrations/versions/f41c0de520d4_espelho_capturaveis_hordas.py"
    spec = importlib.util.spec_from_file_location("migracao_espelho", path)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert modulo.down_revision == "e31a6cf520d4"
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    md = sa.MetaData()
    sa.Table("pokemons_capturaveis", md, sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True))
    sa.Table("pokemons_npc_campo", md,
             sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True))
    with engine.begin() as conn:
        md.create_all(conn)
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            modulo.upgrade()
        assert "capturavel_id" in {c["name"] for c in sa.inspect(conn).get_columns("pokemons_npc_campo")}
        with Operations.context(ctx):
            modulo.downgrade()
        assert "capturavel_id" not in {c["name"] for c in sa.inspect(conn).get_columns("pokemons_npc_campo")}
