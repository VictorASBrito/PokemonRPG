"""Exercita upgrade/downgrade da migration 10D.4 em SQLite isolado.

O teste não toca no PostgreSQL ou em dados da campanha.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

ROOT = Path(__file__).resolve().parents[1]


def test_upgrade_e_downgrade_npcs_hordas():
    caminho = ROOT / "migrations/versions/c84f2b1a7d90_npcs_hordas_campo.py"
    spec = importlib.util.spec_from_file_location("migration_npc_10d4", caminho)
    migracao = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migracao)
    assert migracao.revision == "c84f2b1a7d90"
    assert migracao.down_revision == "7a1f20d9c405"

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadados = sa.MetaData()
    sa.Table("campanhas", metadados, sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True))
    sa.Table("formas_pokemon", metadados, sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True))

    with engine.begin() as conexao:
        metadados.create_all(conexao)
        contexto = MigrationContext.configure(conexao)
        with Operations.context(contexto):
            migracao.upgrade()
        nomes = set(sa.inspect(conexao).get_table_names())
        assert {"campanhas", "formas_pokemon", "grupos_npc_campo", "pokemons_npc_campo"} <= nomes

        with Operations.context(contexto):
            migracao.downgrade()
        nomes = set(sa.inspect(conexao).get_table_names())
        assert "grupos_npc_campo" not in nomes
        assert "pokemons_npc_campo" not in nomes
        assert {"campanhas", "formas_pokemon"} <= nomes
