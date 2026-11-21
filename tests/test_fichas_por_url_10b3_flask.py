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
    # Cada URL de ficha mantém o sprite do próprio slot configurado.
    html_a = a.get_data(as_text=True)
    html_b = b.get_data(as_text=True)
    assert "foto-treinador-link" in html_a and "foto-treinador-link" in html_b
    assert "img/login-personagens/slot-01.png" in html_a
    assert "img/login-personagens/slot-02.png" in html_b
    assert ">Minha ficha</a>" not in html_a and ">Minha ficha</a>" not in html_b
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


def test_preferencias_por_url_preservam_mestre_e_outro_personagem(configurados):
    import re

    def config(client, rota):
        res = client.get(rota)
        assert res.status_code == 200
        match = re.search(r\'<script type="application/json" id="aparencia-config">(.*?)</script>\', res.get_data(as_text=True), re.S)
        assert match
        return json.loads(match.group(1))
    from app.models.db import Item, PersonagemItem

    c = configurados.test_client()
    assert c.post("/login", data={"login": "mestre-db", "senha": "senha-db"}).status_code in (302, 303)
    mestre = config(c, "/mestre/dashboard")
    a = config(c, "/p/bartz-db/jogador/dashboard")
    outro = config(c, "/p/jogador2/jogador/dashboard")
    assert len({mestre["csrf"], a["csrf"], outro["csrf"]}) == 3
    url = "/p/bartz-db/preferencias/aparencia"
    escolha = {"paleta": "personagem", "modo": "dark"}
    assert "personagem" in a["opcoes"]
    assert c.post(url, json=escolha).status_code == 403
    assert c.post(url, json=escolha, headers={"X-Aparencia-CSRF": mestre["csrf"]}).status_code == 403
    assert c.post(url, json=escolha, headers={"X-Aparencia-CSRF": outro["csrf"]}).status_code == 403
    assert c.post(url, json=escolha, headers={"X-Aparencia-CSRF": a["csrf"]}).get_json() == {"ok": True}
    assert config(c, "/p/bartz-db/jogador/dashboard")["paleta"] == "personagem"
    assert config(c, "/p/jogador2/jogador/dashboard")["paleta"] == "classico"
    assert config(c, "/mestre/dashboard")["paleta"] == "classico"
    assert config(configurados.test_client(), "/p/bartz-db/jogador/dashboard")["modo"] == "dark"

    with configurados.app_context():
        dono = db.session.scalar(select(Personagem).join(Usuario).where(Usuario.login == "bartz-db"))
        segundo = db.session.scalar(select(Personagem).join(Usuario).where(Usuario.login == "jogador2"))
        itens = [Item(codigo=f"preferencia-url-{i}", nome=f"Item URL {i}", ativo=True) for i in range(3)]
        db.session.add_all(itens)
        db.session.flush()
        db.session.add_all([PersonagemItem(personagem_id=dono.id, item_id=i.id, quantidade=3) for i in itens[:2]])
        db.session.add(PersonagemItem(personagem_id=segundo.id, item_id=itens[2].id, quantidade=2))
        db.session.commit()
        ids = [str(i.id) for i in itens]
        dono_id, segundo_id = dono.id, segundo.id

    rota = "/p/bartz-db/jogador/inventario/ordem"
    assert c.post(rota, json={"bolsa": "avulsos", "itens": [ids[0], ids[2]]}).status_code == 400
    assert c.post(rota, json={"bolsa": "avulsos", "itens": [ids[1], ids[0]]}).get_json() == {"ok": True}
    with configurados.app_context():
        registros = db.session.scalars(select(PersonagemItem).where(
            PersonagemItem.personagem_id == dono_id).order_by(PersonagemItem.ordem_bolsa)).all()
        assert [str(reg.item_id) for reg in registros] == [ids[1], ids[0]]
        assert all(reg.quantidade == 3 for reg in registros)
        reg = db.session.scalar(select(PersonagemItem).where(PersonagemItem.personagem_id == segundo_id))
        assert reg.ordem_bolsa is None and reg.quantidade == 2
    assert c.post("/p/desconhecido/preferencias/aparencia", json=escolha).status_code == 404
    assert c.get("/p/bartz-db/mestre/dashboard").status_code == 404
