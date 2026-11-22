"""Confirmação de exclusão não pode ser contornada por POST direto."""
import re
from uuid import UUID

import pytest

from app.extensions import db
from app.models.db import Pokemon


@pytest.mark.parametrize("apelido,esperado", [("Buby", "Buby"), (None, "Bulbasaur")])
@pytest.mark.parametrize("mestre", [False, True])
def test_exclusao_exige_csrf_e_nome_atual(app_db, apelido, esperado, mestre):
    cfg = app_db.config["TEST_IDS"]
    with app_db.app_context():
        p = Pokemon(personagem_id=UUID(cfg["personagem"]),
                    forma_pokemon_id=UUID(cfg["formas"]["bulbasaur"]),
                    apelido=apelido, localizacao="box", posicao=1, pv_atual=10)
        db.session.add(p)
        db.session.flush()
        pid = p.id
        db.session.commit()
    c = app_db.test_client()
    login, senha = ("mestre-db", "senha-db") if mestre else ("bartz-db", "abc123")
    assert c.post("/login", data={"login": login, "senha": senha}).status_code in (302, 303)
    prefixo = f"/mestre/jogadores/{cfg['personagem']}" if mestre else "/jogador"
    rota = f"{prefixo}/pokemon/{pid}"
    html = c.get(rota + "?retorno=boxes").get_data(as_text=True)
    assert "modal-excluir-pokemon" in html
    assert f'id="exclusao-nome-alvo">{esperado}</strong>' in html
    token = re.search(r'name="csrf_token" value="([^"]+)"', html.split('id="form-excluir-pokemon"', 1)[1]).group(1)
    assert c.post(rota + "/excluir", data={"nome_confirmacao": esperado}).status_code == 403
    assert c.post(rota + "/excluir", data={"csrf_token": "errado", "nome_confirmacao": esperado}).status_code == 403
    for texto in ("", "errado", esperado.lower()):
        r = c.post(rota + "/excluir", data={"csrf_token": token, "nome_confirmacao": texto, "retorno": "boxes"})
        assert r.status_code == 303
        assert f"/pokemon/{pid}" in r.headers["Location"]
        with app_db.app_context():
            assert db.session.get(Pokemon, pid).ativo
    # Uma ficha aberta antes de um novo apelido não pode excluir com o nome antigo.
    with app_db.app_context():
        db.session.get(Pokemon, pid).apelido = "Novo apelido"
        db.session.commit()
    r = c.post(rota + "/excluir", data={"csrf_token": token, "nome_confirmacao": esperado})
    assert r.status_code == 303
    with app_db.app_context():
        assert db.session.get(Pokemon, pid).ativo
    r = c.post(rota + "/excluir", data={"csrf_token": token, "nome_confirmacao": "Novo apelido", "retorno": "boxes"})
    assert r.status_code in (302, 303)
    assert r.headers["Location"].endswith("/boxes")
    with app_db.app_context():
        assert not db.session.get(Pokemon, pid).ativo
