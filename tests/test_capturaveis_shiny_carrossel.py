"""Etapa 08: Shiny por 1d100 e vitrine de encontros por treinador."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import CampanhaMembro, HistoricoAlteracao, Personagem, Pokemon, PokemonCapturavel, Usuario
from app.services.capturaveis_service import sortear_shiny


def _login(client, login, senha):
    assert client.post("/login", data={"login": login, "senha": senha}).status_code == 302


def _gerar(client, ids, nome="Bulbasaur", forma="bulbasaur", encontrador=None):
    return client.post("/mestre/capturaveis", data={
        "forma_id": ids["formas"][forma],
        "forma_nome": nome,
        "encontrado_por_personagem_id": encontrador or ids["personagem"],
    })


def test_shiny_usa_d100_e_nao_numero_da_pokedex(monkeypatch):
    from app.services import capturaveis_service
    monkeypatch.setattr(capturaveis_service.random, "randint", lambda a, b: 7)
    assert sortear_shiny([7, 31]) == (True, 7)
    assert sortear_shiny(["7", 31]) == (True, 7)
    assert sortear_shiny([1, 25]) == (False, 7)
    assert sortear_shiny([0, 101, -7, "invalido"]) == (False, 7)
    assert sortear_shiny([]) == (False, 7)
    assert sortear_shiny(None) == (False, 7)
    assert sortear_shiny([True, False]) == (False, 7)
    assert sortear_shiny([7.0]) == (True, 7)


def test_shiny_determinado_no_encontro_e_preservado_na_box(app_db, client_db, monkeypatch):
    from app.services import capturaveis_service
    ids = app_db.config["TEST_IDS"]
    monkeypatch.setattr(capturaveis_service.random, "randint", lambda minimo, maximo: 7)
    _login(client_db, "mestre-db", "senha-db")
    assert _gerar(client_db, ids).status_code == 302

    with app_db.app_context():
        capturavel = db.session.execute(select(PokemonCapturavel)).scalar_one()
        assert capturavel.shiny is True
        assert capturavel.forma_pokemon.nome == "Bulbasaur"
        id_capturavel = capturavel.id
        registro = db.session.execute(select(HistoricoAlteracao).where(
            HistoricoAlteracao.entidade == "pokemon_capturavel",
            HistoricoAlteracao.registro_id == capturavel.id,
            HistoricoAlteracao.acao == "criar",
        )).scalar_one()
        assert registro.dados_novos["sorteio_shiny"] == 7
        assert registro.dados_novos["shiny"] is True

    painel = client_db.get("/mestre/capturaveis")
    assert painel.status_code == 200
    assert "Shinies" in painel.get_data(as_text=True)
    assert "Shiny" in painel.get_data(as_text=True)
    with client_db.session_transaction() as sessao:
        token = sessao["capturaveis_atribuir_csrf"]
    resposta = client_db.post(
        f"/mestre/capturaveis/{id_capturavel}/atribuir",
        data={"csrf_token": token, "personagem_id": ids["personagem"]},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        assert pokemon.shiny is True
        assert pokemon.localizacao == "box"
        assert db.session.get(PokemonCapturavel, id_capturavel).ativo is False


def test_sorteio_sem_acerto_nao_gera_shiny(app_db, client_db, monkeypatch):
    from app.services import capturaveis_service
    monkeypatch.setattr(capturaveis_service.random, "randint", lambda minimo, maximo: 8)
    _login(client_db, "mestre-db", "senha-db")
    assert _gerar(client_db, app_db.config["TEST_IDS"]).status_code == 302
    with app_db.app_context():
        assert db.session.execute(select(PokemonCapturavel)).scalar_one().shiny is False


def test_carrossel_exibe_todos_e_prioriza_encontros_proprios(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    with app_db.app_context():
        original = db.session.get(Personagem, uuid.UUID(ids["personagem"]))
        outro = Usuario(login="outro-teste", nome="Outro treinador", senha_hash="hash", perfil="jogador", ativo=True)
        outro_personagem = Personagem(usuario=outro, campanha_id=original.campanha_id, nome="Nina", nivel=5, pv_atual=20, ativo=True)
        db.session.add_all([outro, outro_personagem, CampanhaMembro(campanha_id=original.campanha_id, usuario=outro, papel="jogador")])
        db.session.commit()
        outro_id = str(outro_personagem.id)

    _login(client_db, "mestre-db", "senha-db")
    assert _gerar(client_db, ids).status_code == 302
    assert _gerar(client_db, ids, nome="Charmander", forma="charmander", encontrador=outro_id).status_code == 302
    client_db.post("/logout")
    _login(client_db, "bartz-db", "abc123")
    pagina = client_db.get("/jogador/capturaveis")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert f'data-meu-personagem="{ids["personagem"]}"' in html
    assert f'data-encontrador="{ids["personagem"]}"' in html
    assert f'data-encontrador="{outro_id}"' in html
    assert "Bulbasaur" in html and "Charmander" in html
    assert "Encontrado por você" in html
    assert 'data-carousel-filtro' in html
    assert 'data-carousel-miniatura' in html
    assert 'data-carousel-proximo' in html
    assert "Todos os Pokémon" in html
    assert '<option value="todos" selected>Todos os Pokémon</option>' in html
    assert '<option value="meus">Meus encontrados</option>' in html
    assert "etapa-09-3" in html
    assert "Nina" in html
    assert "capturaveis.js" in html


def test_mestre_tem_filtros_resumo_e_preserva_formulario(app_db, client_db):
    _login(client_db, "mestre-db", "senha-db")
    pagina = client_db.get("/mestre/capturaveis")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    for valor in ["Vagas restantes", "Shinies", "Treinadores envolvidos", "data-filtro-nome", "data-filtro-shiny", "data-captura-form", "data-seletor-alvo=\"forma_id\""]:
        assert valor in html
