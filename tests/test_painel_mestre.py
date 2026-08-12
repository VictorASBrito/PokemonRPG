from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import Personagem, Pokemon


def _login_mestre(client_db) -> None:
    resposta = client_db.post(
        "/login",
        data={"login": "mestre-db", "senha": "senha-db"},
    )
    assert resposta.status_code == 302


def test_painel_geral_exibe_resumo_jogador_e_equipe(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": "Bulbasaur"},
    ).status_code == 302

    with app_db.app_context():
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        pokemon_id = str(pokemon.id)

    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": pokemon_id, "destino": "equipe"},
    ).status_code == 302

    resposta = client_db.get("/mestre/dashboard")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Painel geral do mestre" in texto
    assert "Bartz" in texto
    assert "Bulbasaur" in texto
    assert "Pesquisar na campanha" in texto
    assert "PV do treinador" in texto
    assert "data-pv-form" in texto


def test_painel_permite_ajuste_rapido_de_pv(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]

    resposta = client_db.post(
        f"/mestre/painel/personagens/{jogador_id}/pv",
        data={"delta": "-5"},
    )
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["pv_atual"] == 25
    assert dados["pv_maximo"] == 30

    with app_db.app_context():
        personagem = db.session.get(Personagem, uuid.UUID(jogador_id))
        assert personagem is not None
        assert personagem.pv_atual == 25


def test_painel_permite_ajuste_rapido_de_pv_do_pokemon(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": "Charmander"},
    ).status_code == 302

    with app_db.app_context():
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        pokemon_id = str(pokemon.id)
        pv_inicial = pokemon.pv_atual

    resposta = client_db.post(
        f"/mestre/painel/pokemons/{pokemon_id}/pv",
        data={"delta": "-5"},
    )
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["pv_atual"] == max(0, pv_inicial - 5)

    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon is not None
        assert pokemon.pv_atual == max(0, pv_inicial - 5)
