"""10E.4.2 — captura de integrantes de hordas não depende da tela Campo."""
from __future__ import annotations

from sqlalchemy import select, func

from app.extensions import db
from app.models.db import PokemonNPCEmCampo, PokemonCapturavel


def test_horda_ja_gerada_pode_ser_encaminhada_pelos_capturaveis_com_campo_pausado(app_db, client_db):
    assert client_db.post("/login", data={"login": "mestre-db", "senha": "senha-db"}).status_code == 302
    assert client_db.get("/campo").status_code == 200
    with client_db.session_transaction() as sess:
        campo_token = sess["campo_csrf"]
    assert client_db.post("/campo/npcs/criar", data={
        "csrf_token": campo_token,
        "nome": "Horda preparada",
        "tipo": "horda",
        "time_numero": "1",
        "forma_id": app_db.config["TEST_IDS"]["formas"]["bulbasaur"],
        "nivel": "10",
        "quantidade": "1",
    }).status_code == 302
    with app_db.app_context():
        membro = db.session.scalar(select(PokemonNPCEmCampo))
        assert membro is not None
        pokemon_id = str(membro.id)
        genero = membro.genero
        natureza_id = membro.natureza_id
        shiny = membro.shiny

    app_db.config.update(CAMPO_ATIVO=False, CAMPO_OPERACOES_ATIVAS=False)
    pagina = client_db.get("/mestre/capturaveis")
    assert pagina.status_code == 200
    assert "Horda preparada" in pagina.get_data(as_text=True)
    assert "Disponibilizar captura" in pagina.get_data(as_text=True)
    with client_db.session_transaction() as sess:
        token = sess["capturaveis_atribuir_csrf"]
    url = f"/mestre/capturaveis/hordas/{pokemon_id}/encaminhar"
    assert client_db.post(url, data={
        "csrf_token": "errado",
        "encontrador_id": app_db.config["TEST_IDS"]["personagem"],
    }).status_code == 403
    r = client_db.post(url, data={
        "csrf_token": token,
        "encontrador_id": app_db.config["TEST_IDS"]["personagem"],
    })
    assert r.status_code == 302
    with app_db.app_context():
        membro = db.session.scalar(select(PokemonNPCEmCampo))
        capturavel = db.session.scalar(select(PokemonCapturavel))
        assert membro.enviado_captura is True
        assert capturavel is not None
        assert capturavel.genero == genero
        assert capturavel.natureza_id == natureza_id
        assert capturavel.shiny == shiny
    assert client_db.post(url, data={
        "csrf_token": token,
        "encontrador_id": app_db.config["TEST_IDS"]["personagem"],
    }).status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(PokemonCapturavel)) == 1


def test_envio_ao_campo_pelo_catalogo_npc_fica_bloqueado_sem_impedir_gerador(app_db, client_db):
    assert client_db.post("/login", data={"login": "mestre-db", "senha": "senha-db"}).status_code == 302
    app_db.config.update(CAMPO_ATIVO=False, CAMPO_OPERACOES_ATIVAS=False)
    painel = client_db.get("/mestre/npcs")
    assert painel.status_code == 200
    assert "Gerar NPCs e Hordas" in painel.get_data(as_text=True)
    assert 'name="acao" value="colocar_campo"' not in painel.get_data(as_text=True)
    r = client_db.post("/mestre/npcs/confirmar", data={"acao": "colocar_campo"})
    assert r.status_code == 403
