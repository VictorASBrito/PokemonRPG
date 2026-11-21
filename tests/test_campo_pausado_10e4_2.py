"""10E.4.2 — Campo em pausa sem perda de dados e UI somente demonstrativa."""
from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models.db import PokemonEmCampo


def _login(client):
    assert client.post("/login", data={"login": "bartz-db", "senha": "abc123"}).status_code == 302


def test_campo_pausado_oculta_menu_bloqueia_posts_e_mantem_dados(app_db, client_db):
    _login(client_db)
    with app_db.app_context():
        anterior = list(db.session.scalars(select(PokemonEmCampo.id)))
    app_db.config["CAMPO_ATIVO"] = False
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert 'href="/campo"' not in html
    resposta = client_db.get("/campo")
    assert resposta.status_code == 200
    assert "Campo temporariamente indisponível" in resposta.get_data(as_text=True)
    assert client_db.get("/campo/estado").status_code == 503
    assert client_db.post("/campo/posicionar", data={"pokemon_id": "invalido"}).status_code == 503
    assert client_db.post("/campo/npcs/criar", data={"nome": "Invalido"}).status_code == 503
    with app_db.app_context():
        assert list(db.session.scalars(select(PokemonEmCampo.id))) == anterior


def test_campo_em_modo_demonstrativo_nao_exibe_formularios_e_bloqueia_mutacoes(app_db, client_db):
    _login(client_db)
    app_db.config.update(CAMPO_ATIVO=True, CAMPO_OPERACOES_ATIVAS=False)
    pagina = client_db.get("/campo")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert "Somente visualização" in html
    assert "Painel de Pokémon em campo" in html
    assert "<form" not in html.split('class="campo-pagina"', 1)[1].split("</div>", 1)[0]
    estado = client_db.get("/campo/estado")
    assert estado.status_code == 200
    assert "<form" not in estado.get_data(as_text=True)
    assert client_db.post("/campo/posicionar", data={"pokemon_id": "invalido"}).status_code == 403
