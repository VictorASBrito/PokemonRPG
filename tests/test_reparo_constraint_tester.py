"""Regressão: PostgreSQL deve aceitar Tester na CHECK real de usuários."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def _modulo_migracao():
    arquivo = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "b72cf044e6ad_reconciliar_perfil_tester_postgresql.py"
    )
    spec = importlib.util.spec_from_file_location("migration_reparo_perfil_tester", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


class _ResultadoQuery:
    def __init__(self, perfis):
        self.perfis = perfis

    def scalars(self):
        return self

    def all(self):
        return self.perfis


class _BancoSimulado:
    def __init__(self, dialeto="postgresql", perfis=()):
        self.dialect = SimpleNamespace(name=dialeto)
        self.perfis = perfis

    def execute(self, consulta):
        assert "WHERE perfil NOT IN" in str(consulta)
        return _ResultadoQuery(list(self.perfis))


def test_migracao_recria_constraint_com_tester(monkeypatch):
    modulo = _modulo_migracao()
    comandos = []
    mock_op = SimpleNamespace(
        get_bind=lambda: _BancoSimulado(),
        execute=lambda comando: comandos.append(str(comando)),
    )
    monkeypatch.setattr(modulo, "op", mock_op)

    modulo.upgrade()

    assert len(comandos) == 2
    assert "DROP CONSTRAINT IF EXISTS ck_usuarios_perfil_valido" in comandos[0]
    assert "ADD CONSTRAINT ck_usuarios_perfil_valido" in comandos[1]
    for perfil in ("administrador", "mestre", "tester", "jogador"):
        assert f"'{perfil}'" in comandos[1]
    assert modulo.down_revision == "3a8e5c71d902"


def test_migracao_nao_apaga_usuarios_com_perfis_desconhecidos(monkeypatch):
    modulo = _modulo_migracao()
    comandos = []
    monkeypatch.setattr(
        modulo,
        "op",
        SimpleNamespace(
            get_bind=lambda: _BancoSimulado(perfis=["outro"]),
            execute=comandos.append,
        ),
    )
    with pytest.raises(RuntimeError, match="perfis não reconhecidos"):
        modulo.upgrade()
    assert comandos == []


def test_migracao_reparo_restrita_ao_postgresql(monkeypatch):
    modulo = _modulo_migracao()
    comandos = []
    monkeypatch.setattr(
        modulo,
        "op",
        SimpleNamespace(
            get_bind=lambda: _BancoSimulado(dialeto="sqlite"),
            execute=comandos.append,
        ),
    )
    modulo.upgrade()
    assert comandos == []


def test_diagnostico_usuarios_continua_valido_no_sqlite(app_db):
    resultado = app_db.test_cli_runner().invoke(args=["usuarios", "verificar"])
    assert resultado.exit_code == 0, resultado.output
    assert "Autenticação e vínculos estão consistentes." in resultado.output
