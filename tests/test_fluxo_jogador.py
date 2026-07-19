from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import Personagem, Pokemon


def test_fluxo_completo_jogador_no_postgresql(app_db, client_db) -> None:
    assert client_db.post(
        "/login", data={"login": "mestre-db", "senha": "senha-db"}
    ).status_code == 302
    jogador_id = app_db.config["TEST_IDS"]["personagem"]

    resposta = client_db.post(
        f"/mestre/jogadores/{jogador_id}/ficha",
        data={
            "nome": "Bartz Atualizado",
            "foto_url": "",
            "nivel": "49",
            "idade": "17",
            "genero": "Masculino",
            "origem": "Atleta",
            "classe": "Treinador(a)",
            "estilo_combate": "Agressivo",
            "numeros_shiny": "7, 42",
            "pokedolares": "350",
            "pv_atual": "25",
            "atributo_fisico": "2",
            "atributo_destreza": "2",
            "atributo_saude": "3",
            "atributo_conhecimento": "1",
            "atributo_comunicacao": "1",
            "atributo_espirito": "1",
            "beneficios_habilidades": "Teste",
            "anotacoes": "Campanha",
        },
    )
    assert resposta.status_code == 302

    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": "Charmander"},
    ).status_code == 302

    with app_db.app_context():
        personagem = db.session.execute(
            select(Personagem).where(Personagem.id == uuid.UUID(jogador_id))
        ).scalar_one()
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        assert personagem.nome == "Bartz Atualizado"
        assert personagem.nivel == 49
        assert personagem.pokedolares == 350
        assert pokemon.localizacao == "box"
        pokemon_id = str(pokemon.id)

    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": pokemon_id, "destino": "equipe"},
    ).status_code == 302

    client_db.post("/logout")
    assert client_db.post(
        "/login", data={"login": "bartz-db", "senha": "abc123"}
    ).status_code == 302
    painel = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert "Bartz Atualizado" in painel
    assert "Charmander" in painel
    assert "49" in painel


def test_comando_verifica_pokemon_no_postgresql(app_db) -> None:
    runner = app_db.test_cli_runner()
    resultado = runner.invoke(args=["pokemon", "verificar"])

    assert resultado.exit_code == 0, resultado.output
    assert "Pokémon, equipes e Boxes estão consistentes" in resultado.output
