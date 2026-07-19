from __future__ import annotations

import json
from pathlib import Path

from app.services.importacao import FontesImportacao
from app.services.importacao.utils import categoria_forma, nome_especie, slug, uuid_legado


def _gravar(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def test_analisar_fontes_conta_catalogos_e_campanha(tmp_path) -> None:
    _gravar(tmp_path / "usuarios.json", {"usuarios": [{"id": "u1"}]})
    _gravar(
        tmp_path / "catalogo" / "pokemons.json",
        {"pokemons": [{"id": "pikachu", "nome": "Pikachu", "tipos": ["Elétrico"]}]},
    )
    _gravar(
        tmp_path / "catalogo" / "golpes.json",
        {"golpes": [{"id": "choque", "tipo": "Elétrico", "categoria": "Especial"}]},
    )
    _gravar(
        tmp_path / "catalogo" / "regras_pokemon.json",
        {"atributos": [{"id": "pv"}], "naturezas": [], "status": []},
    )
    _gravar(
        tmp_path / "catalogo" / "regras_treinador.json",
        {"atributos": [{"id": "fisico"}]},
    )
    _gravar(
        tmp_path / "campanhas" / "ankar" / "campanha.json",
        {"id": "ankar", "jogadores": ["j1"]},
    )
    _gravar(
        tmp_path / "campanhas" / "ankar" / "jogadores" / "j1.json",
        {"id": "j1", "usuario_id": "u1", "pokemons": [{"id": "p1"}]},
    )

    resultado = FontesImportacao(tmp_path).analisar()

    assert resultado["usuarios"] == 1
    assert resultado["campanhas"] == 1
    assert resultado["jogadores"] == 1
    assert resultado["pokemon_jogadores"] == 1
    assert resultado["formas_pokemon"] == 1
    assert resultado["golpes"] == 1
    assert resultado["tipos"] == 1
    assert resultado["atributos"] == 2


def test_utilitarios_da_importacao_sao_deterministicos() -> None:
    assert slug("Ataque Especial") == "ataque-especial"
    assert nome_especie("Charizard (Mega X)") == "Charizard"
    assert categoria_forma({"id": "charizard-mega-x", "nome": "Charizard (Mega X)"}) == "mega"
    assert uuid_legado("pokemon", "pkm_1") == uuid_legado("pokemon", "pkm_1")
