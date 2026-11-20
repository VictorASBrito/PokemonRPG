"""Ajustes 10D.4.3: catálogo, seleção manual, nível único e espelho Capturáveis."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import GrupoNPCEmCampo, NPCModelo, PokemonCapturavel, PokemonNPCEmCampo
import app.services.gerador_npcs_ankar as regional


def _atlas():
    return {"locais": [{
        "id": "rota-teste", "nome": "Rota Teste", "tipo": "rota",
        "zonas": [{"nome": "Área geral", "tabelas": [{
            "terreno": "GRAMA", "encontros": [
                {"pokemon": "Bulbasaur", "d100": "1-50", "faixa_valida": True},
                {"pokemon": "Charmander", "d100": "51-100", "faixa_valida": True},
            ],
        }]}],
    }]}


def _login(client):
    assert client.post("/login", data={"login": "mestre-db", "senha": "senha-db"}).status_code == 302


def _csrf(client):
    assert client.get("/mestre/npcs").status_code == 200
    with client.session_transaction() as sess:
        return sess["npc_catalogo_csrf"]


def test_catalogo_npcs_na_area_de_catalogo(app_db, client_db):
    _login(client_db)
    inicial = client_db.get("/mestre/catalogo").get_data(as_text=True)
    assert "Catálogo de NPCs" in inicial or "NPCs" in inicial
    catalogo = client_db.get("/mestre/catalogo/npcs")
    assert catalogo.status_code == 200
    assert "Catálogo de NPCs fixos" in catalogo.get_data(as_text=True)
    gerador = client_db.get("/mestre/npcs").get_data(as_text=True)
    assert "Gerar NPCs e Hordas" in gerador
    assert 'name="modo"' in gerador
    assert 'name="nivel"' in gerador
    assert 'name="nivel_min"' not in gerador


def test_modo_manual_gera_equipe_nivel_unico_sem_localidade(app_db, client_db):
    _login(client_db)
    token = _csrf(client_db)
    ids = app_db.config["TEST_IDS"]["formas"]
    response = client_db.post("/mestre/npcs/gerar", data={
        "csrf_token": token, "tipo": "fixo", "nome": "Treinador Manual",
        "modo": "manual", "nivel": "31", "quantidade": "2",
        "forma_id_manual": [ids["bulbasaur"], ids["charmander"]],
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Prévia ainda não salva" in html
    assert "Bulbasaur" in html and "Charmander" in html
    with client_db.session_transaction() as sess:
        rascunho = sess["npc_ankar_rascunho"]
        assert [x["nivel"] for x in rascunho["pokemons"]] == [31, 31]
        assert rascunho["local_id"] == ""
    assert client_db.post("/mestre/npcs/confirmar", data={
        "csrf_token": token, "acao": "salvar_fixo",
    }).status_code == 302
    with app_db.app_context():
        npc = db.session.scalar(select(NPCModelo))
        assert npc and {x["nivel"] for x in npc.equipe} == {31}
    html = client_db.get("/mestre/catalogo/npcs").get_data(as_text=True)
    assert "Treinador Manual" in html


def test_aleatorio_toda_ankar_sem_filtro_mantem_nivel(app_db, client_db, monkeypatch):
    monkeypatch.setattr(regional, "carregar_catalogo_ankar", _atlas)
    _login(client_db)
    token = _csrf(client_db)
    response = client_db.post("/mestre/npcs/gerar", data={
        "csrf_token": token, "tipo": "temporario", "nome": "NPC Sorteado",
        "modo": "aleatorio", "nivel": "22", "quantidade": "2",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "Prévia ainda não salva" in response.get_data(as_text=True)
    with client_db.session_transaction() as sess:
        prev = sess["npc_ankar_rascunho"]
        assert prev["local_id"] == ""
        assert prev["local_nome"] == "Ankar — todas as localidades"
        assert len(prev["pokemons"]) == 2
        assert all(x["nivel"] == 22 and x["d100"] for x in prev["pokemons"])
        assert {x["nome"] for x in prev["pokemons"]} == {"Bulbasaur", "Charmander"}


def test_modo_manual_exige_exatamente_quantidade_e_bloqueia_repeticao(app_db, client_db):
    _login(client_db)
    token = _csrf(client_db)
    ids = app_db.config["TEST_IDS"]["formas"]
    response = client_db.post("/mestre/npcs/gerar", data={
        "csrf_token": token, "tipo": "fixo", "nome": "Teste",
        "modo": "manual", "nivel": "20", "quantidade": "2",
        "forma_id_manual": [ids["bulbasaur"]],
    }, follow_redirects=True)
    assert "exatamente 2" in response.get_data(as_text=True)
    response = client_db.post("/mestre/npcs/gerar", data={
        "csrf_token": token, "tipo": "fixo", "nome": "Teste",
        "modo": "manual", "nivel": "20", "quantidade": "2",
        "forma_id_manual": [ids["bulbasaur"], ids["bulbasaur"]],
    }, follow_redirects=True)
    assert "espécies repetidas" in response.get_data(as_text=True)


def test_capturavel_gera_espelho_horda_sem_novo_sorteio(app_db, client_db):
    _login(client_db)
    ids = app_db.config["TEST_IDS"]
    response = client_db.post("/mestre/capturaveis", data={
        "forma_id": ids["formas"]["bulbasaur"], "forma_nome": "Bulbasaur",
        "encontrado_por_personagem_id": ids["personagem"],
    })
    assert response.status_code == 302
    with app_db.app_context():
        capt = db.session.scalar(select(PokemonCapturavel))
        npc = db.session.scalar(select(PokemonNPCEmCampo))
        grupo = db.session.scalar(select(GrupoNPCEmCampo))
        assert capt and npc and grupo
        assert npc.capturavel_id == capt.id
        assert npc.enviado_captura is True
        assert grupo.tipo == "horda" and grupo.time_numero == 16
        assert (npc.forma_pokemon_id, npc.natureza_id, npc.genero, npc.shiny) == (
            capt.forma_pokemon_id, capt.natureza_id, capt.genero, capt.shiny
        )
        assert npc.nivel == 48
    campo = client_db.get("/campo").get_data(as_text=True)
    assert "Horda dos Capturáveis" in campo
    assert "Disponibilizado para captura" in campo
    with client_db.session_transaction() as sess:
        token = sess["capturaveis_atribuir_csrf"] if "capturaveis_atribuir_csrf" in sess else None
    client_db.get("/mestre/capturaveis")
    with client_db.session_transaction() as sess:
        token = sess["capturaveis_atribuir_csrf"]
    assert client_db.post(f"/mestre/capturaveis/{capt.id}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(PokemonNPCEmCampo)) is None


def test_capturaveis_representam_varios_pokemon_na_mesma_horda(app_db, client_db):
    _login(client_db)
    ids = app_db.config["TEST_IDS"]
    for name in ("bulbasaur", "charmander"):
        resp = client_db.post("/mestre/capturaveis", data={
            "forma_id": ids["formas"][name],
            "forma_nome": name.capitalize(),
            "encontrado_por_personagem_id": ids["personagem"],
        })
        assert resp.status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(GrupoNPCEmCampo)) == 1
        assert db.session.scalar(select(func.count()).select_from(PokemonNPCEmCampo)) == 2


def test_sem_permissao_nao_acessa_catalogo_npcs(client_db):
    assert client_db.get("/mestre/catalogo/npcs").status_code == 302
    assert client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"}).status_code == 302
    assert client_db.get("/mestre/catalogo/npcs").status_code == 302
