"""Preferências independentes e contraste das paletas."""
import json
import re
from uuid import UUID

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.db import Personagem, Usuario
from app.services.aparencia_service import PALETAS, _hex


def luminancia(cor):
    rgb = [int(cor[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    return sum(v * p for v, p in zip(linear, (.2126, .7152, .0722)))


def contraste(a, b):
    x, y = sorted([luminancia(a), luminancia(b)])
    return (y + .05) / (x + .05)


@pytest.mark.parametrize("paleta", PALETAS.values(), ids=PALETAS.keys())
def test_contraste_paletas(paleta):
    for modo in ("light", "dark"):
        c = paleta[modo]
        for texto in (c[3], c[4]):
            for fundo in c[:3]:
                assert contraste(texto, fundo) >= 4.5, (paleta["nome"], modo, texto, fundo)
        assert contraste(c[6], c[1]) >= 4.5
        assert contraste(c[9], c[6]) >= 4.5
        assert contraste(c[9], c[7]) >= 4.5


def test_contraste_personagem_em_todas_as_matizes():
    for i in range(24):
        h = i / 24
        assert contraste(_hex(h,.64,.26), "#ffffff") >= 4.5
        assert contraste(_hex(h,.65,.75), "#111111") >= 4.5
        assert contraste(_hex(h,.65,.75), _hex(h,.20,.14)) >= 4.5


def config(client, rota):
    res = client.get(rota)
    assert res.status_code == 200
    match = re.search(r'<script type="application/json" id="aparencia-config">(.*?)</script>',
                      res.get_data(as_text=True), re.S)
    assert match
    return json.loads(match.group(1))


def test_preferencia_persistente_isolada(app_db, client_db):
    url = "/preferencias/aparencia"
    assert client_db.post(url, json={"modo":"dark","paleta":"ankar"}).status_code == 403
    assert client_db.post("/login", data={"login":"bartz-db","senha":"abc123"}).status_code == 302
    dados = config(client_db, "/jogador/inventario")
    assert dados["paleta"] == "classico"
    headers = {"X-Aparencia-CSRF": dados["csrf"]}
    assert client_db.post(url, json={"modo":"dark","paleta":"ankar"}).status_code == 403
    for invalido in [{"modo":"dark","paleta":"invalida"},{"modo":"x","paleta":"ankar"}]:
        assert client_db.post(url, json=invalido, headers=headers).status_code == 400
    assert client_db.post(url, json={"modo":"dark","paleta":"ankar"}, headers=headers).get_json() == {"ok":True}
    with app_db.app_context():
        jogador = db.session.get(Personagem, UUID(app_db.config["TEST_IDS"]["personagem"]))
        assert (jogador.aparencia_modo, jogador.aparencia_paleta) == ("dark","ankar")
        assert jogador.usuario.aparencia_paleta is None
    assert config(client_db, "/jogador/inventario")["paleta"] == "ankar"
    client_db.post("/logout")
    assert client_db.post("/login", data={"login":"mestre-db","senha":"senha-db"}).status_code == 302
    dados = config(client_db, "/mestre/dashboard")
    assert dados["paleta"] == "classico"
    assert "personagem" not in dados["opcoes"]
    assert client_db.post(url, json={"modo":"light","paleta":"eclipse"},
                          headers={"X-Aparencia-CSRF":dados["csrf"]}).get_json() == {"ok":True}
    with app_db.app_context():
        mestre = db.session.scalar(select(Usuario).where(Usuario.login == "mestre-db"))
        jogador = db.session.get(Personagem, UUID(app_db.config["TEST_IDS"]["personagem"]))
        assert mestre.aparencia_paleta == "eclipse" and jogador.aparencia_paleta == "ankar"
