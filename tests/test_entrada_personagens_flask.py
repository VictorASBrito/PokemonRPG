"""Testes com o fixture PostgreSQL-emulado/SQLite já usado no projeto."""
from __future__ import annotations

import json
import re

import pytest

from app.extensions import db
from app.models.db import Campanha, CampanhaMembro, Personagem, Usuario
from app.services.senha_service import gerar_hash_senha


def _config(app, caminho, logins):
    caminho.write_text(json.dumps({"habilitado": True, "slots": [
        {"login": login, "sprite": f"img/login-personagens/slot-{i:02}.png"}
        for i, login in enumerate(logins, start=1)
    ]}), encoding="utf-8")
    app.config["LOGIN_PERSONAGENS_ARQUIVO"] = caminho


def _token(html):
    match = re.search(r'name="csrf_token" value="([^\"]+)"', html)
    assert match, "Não encontrou token CSRF dos slots"
    return match.group(1)


@pytest.fixture
def entrada_nove(app_db, tmp_path):
    nomes = ["bartz-db"] + [f"jogador-{i}" for i in range(2, 10)]
    with app_db.app_context():
        campanha = db.session.query(Campanha).filter_by(codigo="ankar").one()
        for nome in nomes[1:]:
            usuario = Usuario(login=nome, nome=nome.title(), senha_hash=gerar_hash_senha("teste123456"), perfil="jogador", ativo=True)
            personagem = Personagem(usuario=usuario, campanha=campanha, nome="Char " + nome, nivel=1, pokedolares=0, pv_atual=10, ativo=True)
            db.session.add_all([usuario, personagem, CampanhaMembro(campanha=campanha, usuario=usuario, papel="jogador")])
        db.session.commit()
    _config(app_db, tmp_path / "entrada_slots.json", nomes)
    return nomes


def test_login_visual_nao_autentica_sem_configuracao(app_db, tmp_path):
    app_db.config["LOGIN_PERSONAGENS_ARQUIVO"] = tmp_path / "config_inexistente.json"
    with app_db.test_client() as cli:
        pagina = cli.get("/login")
        assert pagina.status_code == 200
        assert b"Coringa" in pagina.data
        with cli.session_transaction() as sess:
            token = sess["entrada_personagens_csrf"]
        resultado = cli.post("/login/personagem/1", data={"csrf_token": token})
        assert resultado.status_code == 303
        with cli.session_transaction() as sess:
            assert not sess.get("usuario_id")


def test_login_visual_usa_personagem_correto(entrada_nove, app_db):
    with app_db.test_client() as cli:
        pagina = cli.get("/login")
        assert pagina.status_code == 200
        assert b"Char jogador-2" in pagina.data
        resposta = cli.post("/login/personagem/2", data={"csrf_token": _token(pagina.get_data(as_text=True))})
        assert resposta.status_code == 303
        assert resposta.location.endswith("/jogador/dashboard")
        with cli.session_transaction() as sess:
            assert sess["perfil"] == "jogador"
            assert sess["perfil_conta"] == "jogador"
            assert sess["entrada_visual"] is True
            assert sess["personagem_id"]
            assert not sess.get("deve_alterar_senha")
        assert cli.get("/mestre/dashboard").status_code in (302, 303)


def test_login_visual_rejeita_csrf_ausente(entrada_nove, app_db):
    with app_db.test_client() as cli:
        cli.get("/login")
        resultado = cli.post("/login/personagem/1", data={})
        assert resultado.status_code == 303
        with cli.session_transaction() as sess:
            assert not sess.get("usuario_id")


def test_login_visual_rejeita_numero_de_coringa(entrada_nove, app_db):
    with app_db.test_client() as cli:
        pagina = cli.get("/login")
        r = cli.post("/login/personagem/10", data={"csrf_token": _token(pagina.get_data(as_text=True))})
        assert r.status_code == 303
        with cli.session_transaction() as sess:
            assert not sess.get("usuario_id")


def test_conta_mestre_na_allowlist_nao_entra(entrada_nove, app_db, tmp_path):
    nomes = entrada_nove.copy()
    nomes[0] = "mestre-db"
    _config(app_db, tmp_path / "suspicious.json", nomes)
    with app_db.test_client() as cli:
        pagina = cli.get("/login")
        r = cli.post("/login/personagem/1", data={"csrf_token": _token(pagina.get_data(as_text=True))})
        assert r.status_code == 303
        with cli.session_transaction() as sess:
            assert not sess.get("usuario_id")


def test_perfil_mudou_apos_exibir_tela_nao_entra(entrada_nove, app_db):
    with app_db.test_client() as cli:
        pagina = cli.get("/login")
        token = _token(pagina.get_data(as_text=True))
        with app_db.app_context():
            usuario = db.session.query(Usuario).filter_by(login="jogador-2").one()
            usuario.perfil = "tester"
            db.session.commit()
        r = cli.post("/login/personagem/2", data={"csrf_token": token})
        assert r.status_code == 303
        with cli.session_transaction() as sess:
            assert not sess.get("usuario_id")


def test_coringa_abre_login_normal_e_preserva_senha(app_db):
    with app_db.test_client() as cli:
        r = cli.get("/login/coringa")
        assert r.status_code == 200
        assert b'name="senha"' in r.data
        r = cli.post("/login", data={"login": "mestre-db", "senha": "senha-db"})
        assert r.status_code in (302, 303)
        with cli.session_transaction() as sess:
            assert sess["perfil"] == "mestre"
