"""Regressões da atribuição de capturáveis pelo mestre à Box única."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    HistoricoAlteracao,
    CampanhaMembro,
    Personagem,
    Natureza,
    Pokemon,
    PokemonCapturavel,
    Regra,
    RegraValor,
    Usuario,
)


def _login_mestre(client_db):
    assert client_db.post(
        "/login", data={"login": "mestre-db", "senha": "senha-db"}
    ).status_code == 302


def _criar_encontro(client_db, ids, especie="bulbasaur"):
    resposta = client_db.post(
        "/mestre/capturaveis",
        data={
            "forma_id": ids["formas"][especie],
            "forma_nome": especie.capitalize(),
            "encontrado_por_personagem_id": ids["personagem"],
        },
    )
    assert resposta.status_code == 302


def _enviar_atribuicao(client_db, capturavel_id, personagem_id, *, token=None):
    if token is None:
        assert client_db.get("/mestre/capturaveis").status_code == 200
        with client_db.session_transaction() as sessao:
            token = sessao["capturaveis_atribuir_csrf"]
    return client_db.post(
        f"/mestre/capturaveis/{capturavel_id}/atribuir",
        data={"personagem_id": personagem_id, "csrf_token": token},
        follow_redirects=True,
    )


def test_atribuicao_preserva_identidade_calcula_pv_e_registra_historico(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    _criar_encontro(client_db, ids)

    with app_db.app_context():
        capturavel = db.session.execute(select(PokemonCapturavel)).scalar_one()
        natureza = db.session.execute(select(Natureza).where(Natureza.codigo == "valente")).scalar_one()
        capturavel.natureza_id = natureza.id
        natureza_id = natureza.id
        capturavel.genero = "♀"
        capturavel.shiny = True
        id_origem = capturavel.id
        db.session.commit()

    pagina = client_db.get("/mestre/capturaveis").get_data(as_text=True)
    assert 'Atribuir à Box' in pagina
    assert f'destinatario-{id_origem}' in pagina
    resposta = _enviar_atribuicao(client_db, id_origem, ids["personagem"])
    assert resposta.status_code == 200
    assert "Pokémon atribuído à Box de Bartz com sucesso." in resposta.get_data(as_text=True)

    with app_db.app_context():
        pokemons = list(db.session.execute(select(Pokemon)).scalars())
        assert len(pokemons) == 1
        pokemon = pokemons[0]
        assert str(pokemon.personagem_id) == ids["personagem"]
        assert str(pokemon.forma_pokemon_id) == ids["formas"]["bulbasaur"]
        assert pokemon.natureza_id == natureza_id
        assert pokemon.genero == "♀"
        assert pokemon.shiny is True
        assert pokemon.localizacao == "box" and pokemon.posicao == 1
        assert pokemon.pv_atual > 0
        origem = db.session.get(PokemonCapturavel, id_origem)
        assert origem is not None and not origem.ativo and origem.ordem is None
        evento = db.session.execute(
            select(HistoricoAlteracao).where(
                HistoricoAlteracao.entidade == "pokemon_capturavel",
                HistoricoAlteracao.acao == "atribuir",
                HistoricoAlteracao.registro_id == id_origem,
            )
        ).scalar_one()
        assert evento.dados_novos["pokemon_id"] == str(pokemon.id)
        assert evento.dados_novos["personagem_id"] == ids["personagem"]
        assert evento.dados_anteriores["genero"] == "♀"
        evento_pokemon = db.session.execute(
            select(HistoricoAlteracao).where(
                HistoricoAlteracao.entidade == "pokemon",
                HistoricoAlteracao.registro_id == pokemon.id,
                HistoricoAlteracao.acao == "criacao",
            )
        ).scalar_one()
        assert evento_pokemon.dados_novos["origem"] == "campo_capturaveis"


def test_nao_atribui_duas_vezes_o_mesmo_encontro(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    _criar_encontro(client_db, ids)
    with app_db.app_context():
        encontro_id = db.session.execute(select(PokemonCapturavel.id)).scalar_one()
    assert "sucesso" in _enviar_atribuicao(client_db, encontro_id, ids["personagem"]).get_data(as_text=True)
    resposta = _enviar_atribuicao(client_db, encontro_id, ids["personagem"])
    assert "já saiu do campo" in resposta.get_data(as_text=True)
    with app_db.app_context():
        assert len(db.session.execute(select(Pokemon)).scalars().all()) == 1


def test_box_cheia_preserva_capturavel_ativo_e_nenhum_pokemon_extra(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    with app_db.app_context():
        regra_valor = db.session.execute(
            select(RegraValor).join(Regra).where(Regra.codigo == "tamanho-box")
        ).scalar_one()
        regra_valor.valor = 1
        db.session.commit()

    # Preenche o único espaço usando a criação normal da Box.
    assert client_db.post(
        f'/mestre/jogadores/{ids["personagem"]}/equipe/novo?destino=box:box-unica',
        data={"especie_nome": "Charmander"},
    ).status_code == 302
    _criar_encontro(client_db, ids)
    with app_db.app_context():
        encontro_id = db.session.execute(select(PokemonCapturavel.id)).scalar_one()

    resposta = _enviar_atribuicao(client_db, encontro_id, ids["personagem"])
    assert "está cheia" in resposta.get_data(as_text=True)
    with app_db.app_context():
        encontro = db.session.get(PokemonCapturavel, encontro_id)
        assert encontro.ativo and encontro.ordem == 1
        assert len(db.session.execute(select(Pokemon)).scalars().all()) == 1


def test_destino_invalido_nao_remove_encontro(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    _criar_encontro(client_db, ids)
    with app_db.app_context():
        encontro_id = db.session.execute(select(PokemonCapturavel.id)).scalar_one()
    for destino in ("invalido", str(uuid.uuid4()), ""):
        resposta = _enviar_atribuicao(client_db, encontro_id, destino)
        assert resposta.status_code == 200
        assert "erro" in resposta.get_data(as_text=True)
    with app_db.app_context():
        assert db.session.get(PokemonCapturavel, encontro_id).ativo
        assert not db.session.execute(select(Pokemon)).scalars().all()


def test_atribuicao_do_quinto_entre_dez_preserva_ordem(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    for _ in range(10):
        _criar_encontro(client_db, ids)
    with app_db.app_context():
        itens = db.session.execute(
            select(PokemonCapturavel).order_by(PokemonCapturavel.ordem)
        ).scalars().all()
        id_quinto = itens[4].id
    resposta = _enviar_atribuicao(client_db, id_quinto, ids["personagem"])
    assert "com sucesso" in resposta.get_data(as_text=True)
    with app_db.app_context():
        ativos = db.session.execute(
            select(PokemonCapturavel)
            .where(PokemonCapturavel.ativo.is_(True))
            .order_by(PokemonCapturavel.ordem)
        ).scalars().all()
        assert [item.ordem for item in ativos] == list(range(1, 10))
        assert len(db.session.execute(select(Pokemon)).scalars().all()) == 1


def test_csrf_e_acesso_jogador_nao_atribuem(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    _criar_encontro(client_db, ids)
    with app_db.app_context():
        encontro_id = db.session.execute(select(PokemonCapturavel.id)).scalar_one()
    resposta = _enviar_atribuicao(client_db, encontro_id, ids["personagem"], token="invalido")
    assert "expirado" in resposta.get_data(as_text=True)
    assert client_db.post("/logout").status_code == 302
    assert client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"}).status_code == 302
    resposta = client_db.post(
        f"/mestre/capturaveis/{encontro_id}/atribuir",
        data={"personagem_id": ids["personagem"]},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.get(PokemonCapturavel, encontro_id).ativo
        assert not db.session.execute(select(Pokemon)).scalars().all()


def test_sequencia_de_atribuicoes_ocupa_slots_distintos_na_box(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    _criar_encontro(client_db, ids)
    _criar_encontro(client_db, ids, especie="charmander")
    with app_db.app_context():
        encontros = db.session.execute(
            select(PokemonCapturavel).order_by(PokemonCapturavel.ordem)
        ).scalars().all()
        encontros_ids = [item.id for item in encontros]
    for encontro_id in encontros_ids:
        resposta = _enviar_atribuicao(client_db, encontro_id, ids["personagem"])
        assert "com sucesso" in resposta.get_data(as_text=True)
    with app_db.app_context():
        pokemons = db.session.execute(select(Pokemon).order_by(Pokemon.posicao)).scalars().all()
        assert [item.posicao for item in pokemons] == [1, 2]
        assert [str(item.forma_pokemon_id) for item in pokemons] == [
            ids["formas"]["bulbasaur"], ids["formas"]["charmander"]
        ]
        assert all(item.localizacao == "box" for item in pokemons)


def test_usuario_destinatario_desativado_nao_recebe_captura(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    _criar_encontro(client_db, ids)
    with app_db.app_context():
        encontro_id = db.session.execute(select(PokemonCapturavel.id)).scalar_one()
        usuario = db.session.get(Usuario, uuid.UUID(ids["jogador"]))
        usuario.ativo = False
        db.session.commit()
    resposta = _enviar_atribuicao(client_db, encontro_id, ids["personagem"])
    assert "jogador ativo" in resposta.get_data(as_text=True)
    with app_db.app_context():
        assert db.session.get(PokemonCapturavel, encontro_id).ativo is True
        assert db.session.execute(select(Pokemon)).scalars().first() is None


def test_mestre_pode_escolher_destinatario_diferente_de_quem_encontrou(app_db, client_db):
    ids = app_db.config["TEST_IDS"]
    _login_mestre(client_db)
    _criar_encontro(client_db, ids)
    with app_db.app_context():
        usuario = Usuario(
            login="destinatario-db", nome="Outro Jogador", senha_hash="teste",
            perfil="jogador", ativo=True,
        )
        destino = Personagem(
            usuario=usuario, campanha_id=uuid.UUID(ids["campanha"]),
            nome="Treinador Destino", nivel=5, pv_atual=10, ativo=True,
        )
        db.session.add_all([
            usuario, destino,
            CampanhaMembro(
                campanha_id=uuid.UUID(ids["campanha"]),
                usuario=usuario, papel="jogador",
            ),
        ])
        db.session.commit()
        destino_id = destino.id
        encontro_id = db.session.execute(select(PokemonCapturavel.id)).scalar_one()

    resposta = _enviar_atribuicao(client_db, encontro_id, destino_id)
    assert "Box de Treinador Destino" in resposta.get_data(as_text=True)
    with app_db.app_context():
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        assert pokemon.personagem_id == destino_id
        assert pokemon.pv_atual > 0
        origem = db.session.get(PokemonCapturavel, encontro_id)
        assert str(origem.encontrado_por_personagem_id) == ids["personagem"]
