"""Regressão: mestre/admin altera o nível sem reenviar toda a ficha."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.db import HistoricoAlteracao, Personagem, Usuario


def _login_administrativo(app_db, client_db, perfil: str):
    if perfil == "administrador":
        with app_db.app_context():
            mestre = db.session.get(Usuario, uuid.UUID(app_db.config["TEST_IDS"]["mestre"]))
            mestre.perfil = "administrador"
            db.session.commit()
    assert client_db.post("/login", data={"login": "mestre-db", "senha": "senha-db"}).status_code == 302
    assert client_db.get("/mestre/jogadores").status_code == 200
    with client_db.session_transaction() as sessao:
        return sessao["perfil_csrf"]


@pytest.mark.parametrize("perfil", ["mestre", "administrador"])
def test_mestre_e_admin_alteram_apenas_nivel(app_db, client_db, perfil):
    token = _login_administrativo(app_db, client_db, perfil)
    personagem_id = app_db.config["TEST_IDS"]["personagem"]
    with app_db.app_context():
        personagem = db.session.get(Personagem, uuid.UUID(personagem_id))
        personagem.pv_atual = 999  # dado legado: salvar a ficha inteira validaria outros campos
        db.session.commit()

    resposta = client_db.post(
        f"/mestre/jogadores/{personagem_id}/nivel",
        data={"csrf_token": token, "nivel": "55", "voltar": "ficha"},
    )
    assert resposta.status_code == 302
    assert f"/mestre/jogadores/{personagem_id}/ficha" in resposta.headers["Location"]
    with app_db.app_context():
        personagem = db.session.get(Personagem, uuid.UUID(personagem_id))
        assert personagem.nivel == 55
        assert personagem.pv_atual == 999
        assert personagem.nome == "Bartz"
        auditoria = db.session.scalars(select(HistoricoAlteracao).where(HistoricoAlteracao.acao == "ajustar_nivel")).one()
        assert auditoria.dados_anteriores["nivel"] == 48
        assert auditoria.dados_novos["nivel"] == 55


def test_nivel_invalido_csrf_e_outra_campanha_sao_bloqueados(app_db, client_db):
    token = _login_administrativo(app_db, client_db, "mestre")
    personagem_id = app_db.config["TEST_IDS"]["personagem"]
    url = f"/mestre/jogadores/{personagem_id}/nivel"
    assert client_db.post(url, data={"nivel": "60"}).status_code == 400
    assert client_db.post(url, data={"csrf_token": token, "nivel": "101"}).status_code == 302
    assert client_db.post(url, data={"csrf_token": token, "nivel": "abc"}).status_code == 302
    assert client_db.post(f"/mestre/jogadores/{uuid.uuid4()}/nivel", data={"csrf_token": token, "nivel": "60"}).status_code == 302
    with app_db.app_context():
        assert db.session.get(Personagem, uuid.UUID(personagem_id)).nivel == 48


@pytest.mark.parametrize("perfil", ["jogador", "tester"])
def test_jogador_e_tester_nao_acessam_ajuste_nivel_de_outrem(app_db, client_db, perfil):
    if perfil == "tester":
        with app_db.app_context():
            usuario = db.session.get(Usuario, uuid.UUID(app_db.config["TEST_IDS"]["jogador"]))
            usuario.perfil = "tester"
            db.session.commit()
    assert client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"}).status_code == 302
    url = f"/mestre/jogadores/{app_db.config['TEST_IDS']['personagem']}/nivel"
    assert client_db.post(url, data={"nivel": "99"}).status_code == 302
    with app_db.app_context():
        assert db.session.get(Personagem, uuid.UUID(app_db.config["TEST_IDS"]["personagem"])).nivel == 48


def test_admin_consegue_alterar_perfil_da_conta(app_db, client_db):
    token = _login_administrativo(app_db, client_db, "administrador")
    usuario_id = app_db.config["TEST_IDS"]["jogador"]
    resposta = client_db.post(
        f"/mestre/usuarios/{usuario_id}/perfil",
        data={"csrf_token": token, "perfil": "tester"},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.get(Usuario, uuid.UUID(usuario_id)).perfil == "tester"
