"""10D.4.5 — Painel do NPC com controle da equipe e acesso exclusivo do mestre."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import NPCModelo, Pokemon
from app.services.npc_ficha_service import opcoes_edicao_npc


def login(client, usuario="mestre-db", senha="senha-db"):
    assert client.post("/login", data={"login": usuario, "senha": senha}).status_code == 302


def criar_npc(app, client):
    assert client.get("/mestre/catalogo/npcs/novo").status_code == 200
    with client.session_transaction() as sess:
        csrf = sess["npc_catalogo_csrf"]
    dados = {
        "csrf_token": csrf, "nome": "Comandante Íris",
        "nivel": "35", "classe": "Comandante",
        "anotacoes": "Informação reservada à narrativa.",
    }
    with app.app_context():
        from app.services.npc_ficha_service import dados_ficha_npc
        regras = dados_ficha_npc(campanha_codigo="ankar")["regras"]
        for atributo in regras["atributos"]:
            dados[f'atributo_{atributo["id"]}'] = str(atributo["valor_inicial"])
    r = client.post("/mestre/catalogo/npcs/novo", data=dados)
    assert r.status_code == 302
    with app.app_context():
        modelo = db.session.scalar(select(NPCModelo))
        return str(modelo.id), csrf


def test_painel_npc_exibe_resumo_e_equipe_sem_login_de_jogador(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    resposta = client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    })
    assert resposta.status_code == 302
    pagina = client_db.get(f"/mestre/catalogo/npcs/{modelo_id}/painel")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    for trecho in (
        "Comandante Íris", "Treinador NPC", "Atributos atuais",
        "Golpes equipados", "Gerenciar integrante", "Salvar Pokémon",
        "Ações rápidas", 'data-dashboard-pokemon-grid',
        'data-dashboard-pokemon-card', 'data-pokemon-id="0"',
        "Natureza", "Gênero", "Shiny", "Recolher",
        "Anotações do mestre",
    ):
        assert trecho in html
    assert f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar" in html
    assert "/static/js/dashboard-pokemon.js" in html
    assert "/static/js/npc-painel.js" in html
    catalogo = client_db.get("/mestre/catalogo/npcs").get_data(as_text=True)
    assert f"/mestre/catalogo/npcs/{modelo_id}/painel" in catalogo
    assert "Painel NPC" in catalogo
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(Pokemon)) == 0


def test_editar_nome_natureza_genero_shiny_e_dados_persistem_no_modelo(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    assert client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    }).status_code == 302
    with app_db.app_context():
        generos = opcoes_edicao_npc(campanha_codigo="ankar")["generos"]
        genero = generos[-1]
    url = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar"
    resposta = client_db.post(url, data={
        "csrf_token": csrf, "foco": "0", "origem": "painel",
        "nome": "Verde", "forma_id": forma, "natureza_id": "",
        "genero": genero, "shiny": "1", "golpe_nome": ["", "", "", ""],
    })
    assert resposta.status_code == 302
    assert "/painel?foco=0" in resposta.headers["Location"]
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        assert len(modelo.equipe) == 1
        item = modelo.equipe[0]
        assert item["nome"] == "Verde" and item["shiny"] is True
        assert item["genero"] == genero
        assert item["forma_id"] == forma
        assert item["golpes"] == []
    assert "Verde" in client_db.get(resposta.headers["Location"]).get_data(as_text=True)


def test_reordenar_equipe_e_pv_no_painel(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    for codigo in ("bulbasaur", "charmander"):
        assert client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
            "csrf_token": csrf, "forma_id": app_db.config["TEST_IDS"]["formas"][codigo],
            "origem": "painel",
        }).status_code == 302
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        ids_antes = [m["forma_id"] for m in modelo.equipe]
        pv_antes = int(modelo.equipe[0]["pv_atual"])
    pv = client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/pv", data={
        "csrf_token": csrf, "origem": "painel", "foco": "0",
        "quantidade": "4", "operacao": "menos",
    })
    assert pv.status_code == 302 and "/painel" in pv.headers["Location"]
    mover = client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/mover", data={
        "csrf_token": csrf, "origem": "painel", "foco": "1",
        "direcao": "baixo",
    })
    assert mover.status_code == 302
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        assert [m["forma_id"] for m in modelo.equipe] == ids_antes[::-1]
        assert modelo.equipe[1]["pv_atual"] == pv_antes - 4


def test_painel_somente_mestre_valida_csrf_e_campanha(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    url = f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar"
    assert client_db.post(url, data={"csrf_token": "errado", "forma_id": forma}).status_code == 400
    assert client_db.post(url, data={"csrf_token": csrf, "forma_id": forma}).status_code == 302
    editar = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar"
    assert client_db.post(editar, data={
        "csrf_token": "errado", "nome": "Invasor",
    }).status_code == 400
    with app_db.app_context():
        assert db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe[0]["nome"] != "Invasor"
    client_db.post("/logout")
    login(client_db, "bartz-db", "abc123")
    assert client_db.get(f"/mestre/catalogo/npcs/{modelo_id}/painel").status_code in (302, 403)
    assert client_db.post(editar, data={"csrf_token": csrf, "nome": "Invasor"}).status_code in (302, 403)


def test_painel_rejeita_edicao_invalida_e_indice_fora_da_equipe(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    })
    url = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar"
    assert client_db.post(url, data={
        "csrf_token": csrf, "origem": "painel",
        "forma_id": forma, "natureza_id": "uuid-invalido", "genero": "Ø",
    }).status_code == 302
    assert client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/5/mover", data={
        "csrf_token": csrf, "origem": "painel", "direcao": "cima",
    }).status_code == 302
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        assert len(modelo.equipe) == 1
        assert modelo.equipe[0]["forma_id"] == forma
