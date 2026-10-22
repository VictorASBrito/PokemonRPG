from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import HistoricoAlteracao, Item, PersonagemItem, Pokemon, Usuario
from app.services.inventario_service import adicionar_item, ajustar_quantidade_item


def _login(client, usuario="bartz-db", senha="abc123"):
    resposta = client.post("/login", data={"login": usuario, "senha": senha})
    assert resposta.status_code == 302


def _tornar_tester(app):
    with app.app_context():
        usuario = db.session.get(Usuario, uuid.UUID(app.config["TEST_IDS"]["jogador"]))
        usuario.perfil = "tester"
        db.session.commit()


def _quantos_pokemon(app):
    with app.app_context():
        return db.session.scalar(select(func.count(Pokemon.id))) or 0


def test_jogador_nao_cria_pokemon_nem_ve_links_de_criacao(app_db, client_db):
    _login(client_db)
    resposta = client_db.get("/jogador/boxes")
    assert resposta.status_code == 200
    assert "Criar Pokémon" not in resposta.get_data(as_text=True)
    assert "Espaço vazio" in resposta.get_data(as_text=True)
    for metodo in (client_db.get, client_db.post):
        resposta = metodo(
            "/jogador/equipe/novo?destino=box:box-unica",
            **({"data": {"especie_nome": "Bulbasaur"}} if metodo == client_db.post else {}),
        )
        assert resposta.status_code == 403
    assert _quantos_pokemon(app_db) == 0


def test_tester_cria_apenas_pela_box_e_perde_permissao_ao_rebaixar(app_db, client_db):
    _tornar_tester(app_db)
    _login(client_db)
    resposta = client_db.get("/jogador/boxes")
    assert resposta.status_code == 200
    assert "Criar Pokémon" in resposta.get_data(as_text=True)
    assert client_db.get("/jogador/equipe/novo?destino=box:box-unica").status_code == 200
    assert client_db.post(
        "/jogador/equipe/novo?destino=box:box-unica",
        data={"especie_nome": "Bulbasaur"},
    ).status_code == 302
    assert _quantos_pokemon(app_db) == 1
    with app_db.app_context():
        pokemon = db.session.scalars(select(Pokemon)).first()
        assert pokemon.localizacao == "box"
        assert str(pokemon.personagem_id) == app_db.config["TEST_IDS"]["personagem"]
        usuario = db.session.get(Usuario, uuid.UUID(app_db.config["TEST_IDS"]["jogador"]))
        usuario.perfil = "jogador"
        db.session.commit()
    # Login permanece aberto, mas a permissão consulta o banco a cada pedido.
    assert client_db.post(
        "/jogador/equipe/novo?destino=box:box-unica",
        data={"especie_nome": "Charmander"},
    ).status_code == 403
    assert _quantos_pokemon(app_db) == 1


@pytest.mark.parametrize("nivel", ["jogador", "tester"])
def test_niveis_nao_geram_itens_por_servico_ou_rota(app_db, client_db, nivel):
    if nivel == "tester":
        _tornar_tester(app_db)
    _login(client_db)
    with app_db.app_context():
        item = db.session.scalars(select(Item)).first()
        identificador = str(item.id)
        for funcao in (adicionar_item, ajustar_quantidade_item):
            with pytest.raises(ValueError, match="Apenas o mestre"):
                funcao(
                    personagem_id=app_db.config["TEST_IDS"]["personagem"],
                    item_id=identificador,
                    quantidade=30,
                    usuario_id=app_db.config["TEST_IDS"]["jogador"],
                    campanha_id=app_db.config["TEST_IDS"]["campanha"],
                )
    # O endpoint administrativo não é acessível a jogador/tester.
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    resposta = client_db.post(
        f"/mestre/jogadores/{jogador_id}/inventario/adicionar",
        data={"item_id": identificador, "quantidade": "30"},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count(PersonagemItem.id))) == 0


def test_mestre_altera_tester_e_jogador_e_audita(app_db, client_db):
    _login(client_db, "mestre-db", "senha-db")
    pagina = client_db.get("/mestre/jogadores")
    assert pagina.status_code == 200
    assert "Permissões" in pagina.get_data(as_text=True)
    with client_db.session_transaction() as sessao:
        token = sessao["perfil_csrf"]
    usuario_id = app_db.config["TEST_IDS"]["jogador"]
    url = f"/mestre/usuarios/{usuario_id}/perfil"
    assert client_db.post(url, data={"perfil": "tester"}).status_code == 400
    resposta = client_db.post(url, data={"perfil": "tester", "csrf_token": token})
    assert resposta.status_code == 302
    with app_db.app_context():
        usuario = db.session.get(Usuario, uuid.UUID(usuario_id))
        assert usuario.perfil == "tester"
        registro = db.session.scalars(select(HistoricoAlteracao).where(HistoricoAlteracao.acao == "alterar_perfil")).first()
        assert registro is not None
    assert client_db.post(url, data={"perfil": "mestre", "csrf_token": token}).status_code == 302
    with app_db.app_context():
        assert db.session.get(Usuario, uuid.UUID(usuario_id)).perfil == "tester"
    assert client_db.post(url, data={"perfil": "jogador", "csrf_token": token}).status_code == 302
    with app_db.app_context():
        assert db.session.get(Usuario, uuid.UUID(usuario_id)).perfil == "jogador"
