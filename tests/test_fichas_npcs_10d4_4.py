"""10D.4.4 — Fichas de NPC permanentes: notas privadas, Vida, Status e equipe."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import NPCModelo
from app.services.npc_ficha_service import dados_ficha_npc


def login(client, usuario="mestre-db", senha="senha-db"):
    assert client.post("/login", data={"login": usuario, "senha": senha}).status_code == 302


def token(client):
    assert client.get("/mestre/catalogo/npcs/novo").status_code == 200
    with client.session_transaction() as sess:
        return sess["npc_catalogo_csrf"]


def _atributos(app_db, saude=4):
    with app_db.app_context():
        configuracao = dados_ficha_npc(campanha_codigo="ankar")
        atributos = {}
        for atr in configuracao["regras"]["atributos"]:
            valor = int(atr["valor_inicial"])
            if atr["id"] == "saude":
                valor = saude
            atributos[f'atributo_{atr["id"]}'] = str(valor)
        return atributos


def _cadastro(app_db, token_csrf, *, saude=4, nome="Líder Antares", nivel=25):
    return dict({
        "csrf_token": token_csrf, "nome": nome, "nivel": str(nivel),
        "classe": "Líder de Ginásio", "origem": "Yrezon",
        "foto_url": "https://example.org/sprite.png",
        "anotacoes": "Suspeita que a Equipe Rocket esteja na cidade.\nTem um acordo secreto.",
    }, **_atributos(app_db, saude=saude))


def test_criar_ficha_npc_com_notas_vida_status_e_card(app_db, client_db):
    login(client_db)
    csrf = token(client_db)
    formulario = _cadastro(app_db, csrf)
    resposta = client_db.post("/mestre/catalogo/npcs/novo", data=formulario)
    assert resposta.status_code == 302
    assert "/ficha" in resposta.headers["Location"]
    with app_db.app_context():
        npc = db.session.scalar(select(NPCModelo))
        assert npc is not None
        npc_id = str(npc.id)
        assert npc.nome == "Líder Antares"
        assert npc.nivel == 25
        assert npc.atributos["saude"] == 4
        assert npc.pv_atual == 40
        assert npc.classe == "Líder de Ginásio"
        assert npc.foto_url.endswith("sprite.png")
        assert "acordo secreto" in npc.anotacoes
        assert npc.equipe == []

    catalogo = client_db.get("/mestre/catalogo/npcs")
    pagina = catalogo.get_data(as_text=True)
    assert catalogo.status_code == 200
    assert "Líder Antares" in pagina
    assert "Vida" in pagina and "Status" in pagina
    assert "Equipe" in pagina and "40/40" in pagina
    assert "Saúde" in pagina and "Ficha NPC" in pagina
    assert "Anotações:" in pagina
    assert "/mestre/catalogo/npcs/" + npc_id + "/ficha" in pagina
    assert 'name="senha"' not in pagina and "Box 0" not in pagina

    ficha = client_db.get(f"/mestre/catalogo/npcs/{npc_id}/ficha").get_data(as_text=True)
    assert "Anotações do mestre" in ficha and "acordo secreto" in ficha


def test_edicao_recalcula_pv_e_preserva_notas(app_db, client_db):
    login(client_db)
    csrf = token(client_db)
    client_db.post("/mestre/catalogo/npcs/novo", data=_cadastro(app_db, csrf))
    with app_db.app_context():
        npc_id = str(db.session.scalar(select(NPCModelo)).id)
    editar = _cadastro(app_db, csrf, saude=2, nivel=29)
    editar["anotacoes"] = "Agora trabalha para o antagonista."
    resposta = client_db.post(f"/mestre/catalogo/npcs/{npc_id}/ficha", data=editar)
    assert resposta.status_code == 302
    with app_db.app_context():
        npc = db.session.get(NPCModelo, uuid.UUID(npc_id))
        assert npc.nivel == 29
        assert npc.atributos["saude"] == 2
        assert npc.pv_atual == 20  # 40/40 anterior, agora limite de 20.
        assert npc.anotacoes == "Agora trabalha para o antagonista."

    assert client_db.post(f"/mestre/catalogo/npcs/{npc_id}/pv", data={
        "csrf_token": csrf, "quantidade": "7", "operacao": "menos",
    }).status_code == 302
    with app_db.app_context():
        assert db.session.get(NPCModelo, uuid.UUID(npc_id)).pv_atual == 13
    assert client_db.post(f"/mestre/catalogo/npcs/{npc_id}/pv", data={
        "csrf_token": csrf, "quantidade": "9999", "operacao": "mais",
    }).status_code == 302
    with app_db.app_context():
        assert db.session.get(NPCModelo, uuid.UUID(npc_id)).pv_atual == 20


def test_ficha_pokemon_adicionar_vida_e_remover(app_db, client_db):
    login(client_db)
    csrf = token(client_db)
    client_db.post("/mestre/catalogo/npcs/novo", data=_cadastro(app_db, csrf))
    with app_db.app_context():
        npc_id = str(db.session.scalar(select(NPCModelo)).id)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    criar = client_db.post(f"/mestre/catalogo/npcs/{npc_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    }, follow_redirects=True)
    assert criar.status_code == 200
    with app_db.app_context():
        npc = db.session.get(NPCModelo, uuid.UUID(npc_id))
        assert len(npc.equipe) == 1
        assert npc.equipe[0]["nivel"] == 25
        assert npc.equipe[0]["pv_atual"] > 0
        pv = npc.equipe[0]["pv_atual"]

    resposta = client_db.post(f"/mestre/catalogo/npcs/{npc_id}/equipe/0/pv", data={
        "csrf_token": csrf, "quantidade": "6", "operacao": "menos",
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        npc = db.session.get(NPCModelo, uuid.UUID(npc_id))
        assert npc.equipe[0]["pv_atual"] == pv - 6

    editar = _cadastro(app_db, csrf, nivel=30)
    client_db.post(f"/mestre/catalogo/npcs/{npc_id}/ficha", data=editar)
    with app_db.app_context():
        npc = db.session.get(NPCModelo, uuid.UUID(npc_id))
        assert npc.equipe[0]["nivel"] == 30

    assert client_db.post(f"/mestre/catalogo/npcs/{npc_id}/equipe/0/retirar", data={
        "csrf_token": csrf,
    }).status_code == 302
    with app_db.app_context():
        assert db.session.get(NPCModelo, uuid.UUID(npc_id)).equipe == []


def test_pv_rejeita_csrf_forjado_e_limita_valores(app_db, client_db):
    login(client_db)
    csrf = token(client_db)
    client_db.post("/mestre/catalogo/npcs/novo", data=_cadastro(app_db, csrf))
    with app_db.app_context():
        npc_id = str(db.session.scalar(select(NPCModelo)).id)
    resposta = client_db.post(f"/mestre/catalogo/npcs/{npc_id}/pv", data={
        "csrf_token": "invalido", "quantidade": "10", "operacao": "menos",
    })
    assert resposta.status_code == 400
    with app_db.app_context():
        assert db.session.get(NPCModelo, uuid.UUID(npc_id)).pv_atual == 40
    # Não é permitido aumentar o PV acima do máximo.
    client_db.post(f"/mestre/catalogo/npcs/{npc_id}/pv", data={
        "csrf_token": csrf, "quantidade": "100", "operacao": "mais",
    })
    with app_db.app_context():
        assert db.session.get(NPCModelo, uuid.UUID(npc_id)).pv_atual == 40


def test_npcs_nao_possuem_login_e_jogadores_nao_acessam_fichas(app_db, client_db):
    login(client_db)
    csrf = token(client_db)
    client_db.post("/mestre/catalogo/npcs/novo", data=_cadastro(app_db, csrf))
    with app_db.app_context():
        npc_id = str(db.session.scalar(select(NPCModelo)).id)
    client_db.post("/logout")
    login(client_db, "bartz-db", "abc123")
    for url in (
        "/mestre/catalogo/npcs", "/mestre/catalogo/npcs/novo",
        f"/mestre/catalogo/npcs/{npc_id}/ficha",
    ):
        assert client_db.get(url).status_code in (302, 403)
    assert client_db.post("/mestre/catalogo/npcs/novo", data={
        "csrf_token": csrf, "nome": "Intruso",
    }).status_code in (302, 403)


def test_ficha_npc_impede_acesso_a_outro_id_de_campanha(app_db, client_db):
    login(client_db)
    csrf = token(client_db)
    client_db.post("/mestre/catalogo/npcs/novo", data=_cadastro(app_db, csrf))
    from app.models.db import Campanha
    with app_db.app_context():
        npc = db.session.scalar(select(NPCModelo))
        npc_id = str(npc.id)
        outra = Campanha(codigo="outra", nome="Outra", ativo=True)
        db.session.add(outra)
        db.session.flush()
        npc.campanha_id = outra.id
        db.session.commit()
    assert client_db.get(f"/mestre/catalogo/npcs/{npc_id}/ficha").status_code == 404
