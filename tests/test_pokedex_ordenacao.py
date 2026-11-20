from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.extensions import db
from app.models.db import EspeciePokemon, FormaPokemon
from app.services.catalogo_admin_service import listar_formas_admin
from app.services.pokedex_service import codigo_especie_pokedex, mapear_numeros_pokedex
from app.services.pokemon_db_service import listar_formas_ativas, pesquisar_formas_autocomplete


FONTE = Path(__file__).resolve().parents[1] / "data" / "catalogo" / "pokemons.json"


def test_pokedex_nacional_nao_conta_formas_como_especies() -> None:
    registros = json.loads(FONTE.read_text(encoding="utf-8"))["pokemons"]
    numeros = mapear_numeros_pokedex(registros)
    assert len(numeros) == 898
    assert numeros["bulbasaur"] == 1
    assert numeros["ivysaur"] == 2
    assert numeros["venusaur"] == 3
    assert numeros["charmander"] == 4
    assert numeros["pikachu"] == 25
    assert numeros["nidoran"] == 29
    assert numeros["nidoran-m"] == 32
    assert numeros["abomasnow"] == 460
    assert numeros["calyrex"] == 898
    assert codigo_especie_pokedex("Rattata (Alola)") == "rattata"
    assert codigo_especie_pokedex("Charizard (Mega X)") == "charizard"


def test_todas_listagens_respeitam_numero_da_pokedex(app_db) -> None:
    with app_db.app_context():
        for codigo, numero in (("bulbasaur", 1), ("charmander", 4), ("squirtle", 7)):
            especie = db.session.execute(
                select(EspeciePokemon).where(EspeciePokemon.codigo == codigo)
            ).scalar_one()
            especie.numero = numero
        db.session.commit()

        pagina = listar_formas_admin(pagina=1, por_pagina=12)
        assert [f.codigo for f in pagina.itens[:3]] == [
            "bulbasaur", "charmander", "squirtle",
        ]
        assert [f.codigo for f in listar_formas_ativas()[:3]] == [
            "bulbasaur", "charmander", "squirtle",
        ]
        assert [f["valor"] for f in pesquisar_formas_autocomplete("")[:3]] == [
            "Bulbasaur", "Charmander", "Squirtle",
        ]


def test_comando_pokedex_simula_antes_de_aplicar(app_db) -> None:
    runner = app_db.test_cli_runner()
    simulacao = runner.invoke(args=["catalogo", "pokedex-preencher"])
    assert simulacao.exit_code == 0, simulacao.output
    assert "SIMULAÇÃO" in simulacao.output
    with app_db.app_context():
        bulbasaur = db.session.execute(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "bulbasaur")
        ).scalar_one()
        assert bulbasaur.numero is None

    aplicacao = runner.invoke(args=["catalogo", "pokedex-preencher", "--aplicar"])
    assert aplicacao.exit_code == 0, aplicacao.output
    with app_db.app_context():
        bulbasaur = db.session.execute(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "bulbasaur")
        ).scalar_one()
        assert bulbasaur.numero == 1
    segunda = runner.invoke(args=["catalogo", "pokedex-preencher", "--aplicar"])
    assert segunda.exit_code == 0, segunda.output
    assert "0 número(s) preenchido(s)" in segunda.output


def test_reparo_separa_nidoran_m_sem_alterar_id_da_forma(app_db) -> None:
    with app_db.app_context():
        femea = EspeciePokemon(codigo="nidoran", nome="Nidoran♀", ativo=True)
        macho = FormaPokemon(
            especie=femea,
            codigo="nidoran-2",
            nome="Nidoran♂",
            categoria="normal",
            configuracoes={"origem": "Ficha Editável v2.5.xlsx"},
            ativo=True,
        )
        db.session.add(macho)
        db.session.commit()
        forma_id = macho.id

    runner = app_db.test_cli_runner()
    resposta = runner.invoke(args=["catalogo", "pokedex-preencher", "--aplicar"])
    assert resposta.exit_code == 0, resposta.output
    with app_db.app_context():
        macho = db.session.get(FormaPokemon, forma_id)
        assert macho is not None
        assert macho.especie.codigo == "nidoran-m"
        assert macho.especie.numero == 32
        assert db.session.execute(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "nidoran")
        ).scalar_one().numero == 29
