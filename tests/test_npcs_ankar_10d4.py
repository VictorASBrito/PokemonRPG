"""Regressões do catálogo de NPCs e hordas regionais (Flask + SQLite)."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    GrupoNPCEmCampo, NPCModelo, Personagem, PokemonCapturavel,
    PokemonNPCEmCampo, Pokemon, Usuario,
)
import app.services.gerador_npcs_ankar as atlas


def _atlas_falso():
    return {"locais": [{
        "id": "rota-teste", "nome": "Rota Teste", "tipo": "rota",
        "zonas": [{"nome": "Área geral", "tabelas": [{
            "terreno": "GRAMA", "encontros": [
                {"pokemon": "Bulbasaur", "d100": "1-50", "faixa_valida": True, "marcador": False},
                {"pokemon": "Charmander", "d100": "51-100", "faixa_valida": True, "marcador": False},
            ],
        }]}],
    }]}


def _login(client, user="mestre-db", password="senha-db"):
    assert client.post("/login", data={"login": user, "senha": password}).status_code == 302


def _token(client):
    assert client.get("/mestre/npcs").status_code == 200
    with client.session_transaction() as sess:
        return sess["npc_catalogo_csrf"]


def _gerar(client, token, tipo="fixo", n=2, **extra):
    payload = {
        "csrf_token": token, "tipo": tipo, "nome": "Rival Regional",
        "local_id": "rota-teste", "zona_index": "0", "tabela_index": "0",
        "quantidade": str(n), "nivel": "12", "modo": "aleatorio",
    }
    payload.update(extra)
    return client.post("/mestre/npcs/gerar", data=payload, follow_redirects=True)


def test_criar_npc_fixo_salvar_catalogo_e_colocar_copia(app_db, client_db, monkeypatch):
    monkeypatch.setattr(atlas, "carregar_catalogo_ankar", _atlas_falso)
    _login(client_db)
    token = _token(client_db)
    pagina = client_db.get("/mestre/npcs").get_data(as_text=True)
    assert "Gerar NPCs e Hordas" in pagina
    assert "Seleção de Pokémon" in pagina
    resposta = _gerar(client_db, token)
    texto = resposta.get_data(as_text=True)
    assert "Prévia ainda não salva" in texto
    assert "Bulbasaur" in texto and "Charmander" in texto

    # O mestre pode refazer individualmente antes de salvar.
    assert client_db.post("/mestre/npcs/refazer/0", data={"csrf_token": token}).status_code == 302
    assert client_db.post("/mestre/npcs/confirmar", data={
        "csrf_token": token, "acao": "salvar_fixo",
    }).status_code == 302

    with app_db.app_context():
        modelo = db.session.scalar(select(NPCModelo))
        assert modelo is not None and len(modelo.equipe) == 2
        modelo_id = str(modelo.id)
        identidade = [dict(item) for item in modelo.equipe]

    assert client_db.post(f"/mestre/npcs/modelos/{modelo_id}/campo", data={
        "csrf_token": token, "time_numero": "4",
    }).status_code == 302
    with app_db.app_context():
        grupo = db.session.scalar(select(GrupoNPCEmCampo))
        assert grupo and grupo.tipo == "npc" and str(grupo.modelo_id) == modelo_id
        assert grupo.time_numero == 4
        assert db.session.scalar(select(func.count()).select_from(PokemonNPCEmCampo)) == 2
        assert db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe == identidade
        assert db.session.scalar(select(func.count()).select_from(Pokemon)) == 0


def test_horda_captura_preserva_shiny_natureza_genero_sem_duplicar(app_db, client_db, monkeypatch):
    monkeypatch.setattr(atlas, "carregar_catalogo_ankar", _atlas_falso)
    with app_db.app_context():
        p = db.session.get(Personagem, uuid.UUID(app_db.config["TEST_IDS"]["personagem"]))
        p.numeros_shiny = list(range(1, 101))
        db.session.commit()
    _login(client_db)
    token = _token(client_db)
    encontrador = app_db.config["TEST_IDS"]["personagem"]
    resposta = _gerar(client_db, token, tipo="horda", n=2, encontrador_id=encontrador)
    assert "Prévia ainda não salva" in resposta.get_data(as_text=True)
    assert client_db.post("/mestre/npcs/confirmar", data={
        "csrf_token": token, "acao": "colocar_campo", "time_numero": "8",
    }).status_code == 302

    with app_db.app_context():
        grupo = db.session.scalar(select(GrupoNPCEmCampo))
        assert grupo and grupo.tipo == "horda" and grupo.time_numero == 8
        assert str(grupo.encontrado_por_personagem_id) == encontrador
        pokemon = db.session.scalar(select(PokemonNPCEmCampo))
        pokemon_id = str(pokemon.id)
        original = (pokemon.forma_pokemon_id, pokemon.natureza_id, pokemon.genero, pokemon.shiny)
        assert original[3] is True

    campo = client_db.get("/campo").get_data(as_text=True)
    assert "Adicionar aos Capturáveis" in campo

    campo_token = None
    with client_db.session_transaction() as sessao:
        campo_token = sessao["campo_csrf"]
    transferencia = client_db.post(f"/campo/npcs/pokemons/{pokemon_id}/capturavel", data={
        "csrf_token": campo_token, "encontrador_id": encontrador,
    })
    assert transferencia.status_code == 302

    with app_db.app_context():
        capturavel = db.session.scalar(select(PokemonCapturavel))
        assert capturavel is not None
        assert (capturavel.forma_pokemon_id, capturavel.natureza_id,
                capturavel.genero, capturavel.shiny) == original
        assert db.session.get(PokemonNPCEmCampo, uuid.UUID(pokemon_id)).enviado_captura is True

    assert client_db.post(f"/campo/npcs/pokemons/{pokemon_id}/capturavel", data={
        "csrf_token": campo_token, "encontrador_id": encontrador,
    }).status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(PokemonCapturavel)) == 1

    # Limpar Campo remove a horda, mas nunca o Pokémon já disponibilizado.
    assert client_db.post("/campo/limpar", data={"csrf_token": campo_token}).status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(GrupoNPCEmCampo)) == 0
        assert db.session.scalar(select(func.count()).select_from(PokemonCapturavel)) == 1


def test_jogadores_nao_geram_npcs_nem_enviam_hordas(app_db, client_db, monkeypatch):
    monkeypatch.setattr(atlas, "carregar_catalogo_ankar", _atlas_falso)
    _login(client_db, "bartz-db", "abc123")
    pagina = client_db.get("/mestre/npcs")
    assert pagina.status_code in (302, 403)
    assert client_db.post("/mestre/npcs/gerar", data={
        "tipo": "fixo", "quantidade": "6",
    }).status_code in (302, 403)
    # Campo trata restrições de mestre com 403 mesmo se a URL for forjada.
    _login(client_db)
    token = _token(client_db)
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(NPCModelo)) == 0


def test_gerador_exige_csrf_e_localidade_verdadeira(app_db, client_db, monkeypatch):
    monkeypatch.setattr(atlas, "carregar_catalogo_ankar", _atlas_falso)
    _login(client_db)
    token = _token(client_db)
    assert client_db.post("/mestre/npcs/gerar", data={
        "nome": "Ataque", "tipo": "fixo", "quantidade": "1",
    }).status_code == 400
    resp = _gerar(client_db, token, local_id="rota-inexistente")
    assert "Localidade inexistente" in resp.get_data(as_text=True)
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(NPCModelo)) == 0
