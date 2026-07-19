from __future__ import annotations

from app import create_app
from app.extensions import db


def test_metadata_contem_estrutura_relacional(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'teste.db'}")
    create_app()

    tabelas_esperadas = {
        "usuarios",
        "campanhas",
        "campanha_membros",
        "personagens",
        "atributos",
        "tipos_pokemon",
        "efetividades_tipo",
        "especies_pokemon",
        "formas_pokemon",
        "golpes",
        "pokemons",
        "pokemon_golpes",
        "itens",
        "regras",
        "regra_valores",
        "historico_alteracoes",
    }

    assert tabelas_esperadas.issubset(db.metadata.tables)
    assert len(db.metadata.tables) == 32


def test_modelo_pokemon_respeita_regras_da_campanha(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'teste.db'}")
    create_app()

    colunas_pokemon = db.metadata.tables["pokemons"].c
    colunas_golpe = db.metadata.tables["golpes"].c

    assert "nivel" not in colunas_pokemon
    assert "experiencia" not in colunas_pokemon
    assert "amizade" not in colunas_pokemon
    assert "taxa_captura" not in colunas_pokemon
    assert "pp" not in colunas_golpe
    assert "custo_pp" not in colunas_golpe
