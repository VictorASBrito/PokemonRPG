"""Integração real com app_db; executar no ambiente Flask do PokemonRPG."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.db import Campanha, CampanhaMembro, Personagem, Usuario
from app.services.senha_service import gerar_hash_senha


@pytest.fixture()
def configurados(app_db, tmp_path):
    logins = ["bartz-db"] + [f"jogador{i}" for i in range(2, 10)]
    destino = tmp_path / "entrada_personagens.json"
    destino.write_text(json.dumps({"habilitado": True, "slots": [
        {"login": login, "sprite": f"img/login-personagens/slot-{pos:02}.png"}
        for pos, login in enumerate(logins, start=1)
    ]}), encoding="utf-8")
    app_db.config["LOGIN_PERSONAGENS_ARQUIVO"] = str(destino)
    with app_db.app_context():
        campanha = db.session.execute(select(Campanha).where(Campanha.codigo == "ankar")).scalar_one()
        for n in range(2, 10):
            usuario = Usuario(login=f"jogador{n}", nome=f"Conta {n}", perfil="jogador",
                              senha_hash=gerar_hash_senha("senha-teste"), ativo=True)
            personagem = Personagem(usuario=usuario, campanha=campanha, nome=f"Treinador {n}", ativo=True)
            db.session.add_all([usuario, personagem, CampanhaMembro(usuario=usuario, campanha=campanha, papel="jogador")])
        db.session.commit()
    return app_db


def test_duas_fichas_no_mesmo_navegador(configurados):
    c = configurados.test_client()
    a = c.get("/p/bartz-db/jogador/dashboard")
    b = c.get("/p/jogador2/jogador/dashboard")
    assert a.status_code == b.status_code == 200
    assert "Bartz" in a.get_data(as_text=True)
    assert "Treinador 2" in b.get_data(as_text=True)
    assert "/p/bartz-db/jogador/ficha" in a.get_data(as_text=True)
    assert "/p/jogador2/jogador/ficha" in b.get_data(as_text=True)
    assert c.get("/p/bartz-db/jogador/ficha").status_code == 200
    assert c.get("/p/jogador2/jogador/ficha").status_code == 200


def test_urls_nunca_abrem_rotas_administrativas(configurados):
    c = configurados.test_client()
    assert c.get("/p/bartz-db/mestre/dashboard").status_code == 404
    assert c.get("/p/bartz-db/conta/senha").status_code == 404
    assert c.get("/p/bartz-db/api/catalogo/itens").status_code == 404
    assert c.get("/p/desconhecido/jogador/dashboard").status_code == 404


def test_sessao_mestre_permanece_independente(configurados):
    c = configurados.test_client()
    resp = c.post("/login", data={"login": "mestre-db", "senha": "senha-db"})
    assert resp.status_code in (302, 303)
    assert c.get("/mestre/dashboard").status_code == 200
    assert c.get("/p/bartz-db/jogador/dashboard").status_code == 200
    assert c.get("/p/jogador2/jogador/dashboard").status_code == 200
    assert c.get("/mestre/dashboard").status_code == 200
    assert c.get("/selecionar").status_code == 200
    saida = c.post("/p/bartz-db/logout")
    assert saida.status_code in (302, 303)
    assert saida.headers["Location"].endswith("/selecionar")
    assert c.get("/mestre/dashboard").status_code == 200


def test_selecao_redireciona_para_url_estavel_sem_trocar_login(configurados):
    c = configurados.test_client()
    c.post("/login", data={"login": "mestre-db", "senha": "senha-db"})
    html = c.get("/selecionar").get_data(as_text=True)
    import re
    token = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert token, html[:1500]
    resposta = c.post("/login/personagem/1", data={"csrf_token": token.group(1)})
    assert resposta.status_code == 303
    assert resposta.headers["Location"].endswith("/p/bartz-db/")
    assert c.get("/mestre/dashboard").status_code == 200
