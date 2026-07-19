from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import Pokemon


def _login_mestre(client) -> None:
    assert client.post(
        "/login", data={"login": "mestre-db", "senha": "senha-db"}
    ).status_code == 302


def _personagem_id(app) -> str:
    return app.config["TEST_IDS"]["personagem"]


def _criar_na_box(app, client, especie: str) -> str:
    jogador_id = _personagem_id(app)
    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": especie},
    )
    assert resposta.status_code == 302
    with app.app_context():
        pokemon = db.session.execute(
            select(Pokemon)
            .where(
                Pokemon.personagem_id == uuid.UUID(jogador_id),
                Pokemon.ativo.is_(True),
                Pokemon.localizacao == "box",
            )
            .order_by(Pokemon.posicao.desc())
        ).scalars().first()
        assert pokemon is not None
        return str(pokemon.id)


def test_box_unica_tem_cem_espacos_e_nao_possui_compra(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = _personagem_id(app_db)
    resposta = client_db.get(f"/mestre/jogadores/{jogador_id}/boxes")
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "100 espaços" in texto
    assert "Comprar Box" not in texto
    assert "/boxes/novo" not in texto
    assert "Fonte: PostgreSQL" not in texto  # sem poluir a tela principal


def test_pokemon_so_pode_ser_criado_em_espaco_da_box(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = _personagem_id(app_db)

    resposta = client_db.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo",
        data={"especie_nome": "Bulbasaur"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "só podem ser criados em um espaço vazio da Box" in resposta.get_data(as_text=True)

    with app_db.app_context():
        assert db.session.scalar(select(func.count(Pokemon.id))) == 0

    pokemon_id = _criar_na_box(app_db, client_db, "Bulbasaur")
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon is not None
        assert pokemon.localizacao == "box"
        assert pokemon.posicao == 1


def test_movimentacao_adiciona_ao_fim_da_equipe_e_da_box(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = _personagem_id(app_db)
    bulbasaur = _criar_na_box(app_db, client_db, "Bulbasaur")
    charmander = _criar_na_box(app_db, client_db, "Charmander")

    for pokemon_id in (bulbasaur, charmander):
        assert client_db.post(
            f"/mestre/jogadores/{jogador_id}/boxes/mover",
            data={"pokemon_id": pokemon_id, "destino": "equipe"},
        ).status_code == 302

    with app_db.app_context():
        equipe = list(
            db.session.execute(
                select(Pokemon)
                .where(Pokemon.localizacao == "equipe")
                .order_by(Pokemon.posicao)
            ).scalars()
        )
        assert [str(item.id) for item in equipe] == [bulbasaur, charmander]

    for pokemon_id in (bulbasaur, charmander):
        assert client_db.post(
            f"/mestre/jogadores/{jogador_id}/boxes/mover",
            data={"pokemon_id": pokemon_id, "destino": "box:box-unica"},
        ).status_code == 302

    with app_db.app_context():
        box = list(
            db.session.execute(
                select(Pokemon)
                .where(Pokemon.localizacao == "box")
                .order_by(Pokemon.posicao)
            ).scalars()
        )
        assert [str(item.id) for item in box] == [bulbasaur, charmander]
        assert [item.posicao for item in box] == [1, 2]


def test_equipe_cheia_impede_adicao_vinda_da_box(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = _personagem_id(app_db)
    especies = [
        "Bulbasaur",
        "Charmander",
        "Squirtle",
        "Caterpie",
        "Weedle",
        "Pidgey",
        "Rattata",
    ]
    ids = [_criar_na_box(app_db, client_db, especie) for especie in especies]

    for pokemon_id in ids[:6]:
        assert client_db.post(
            f"/mestre/jogadores/{jogador_id}/boxes/mover",
            data={"pokemon_id": pokemon_id, "destino": "equipe"},
        ).status_code == 302

    resposta = client_db.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": ids[6], "destino": "equipe"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "limite de 6" in resposta.get_data(as_text=True)

    with app_db.app_context():
        assert db.session.scalar(
            select(func.count(Pokemon.id)).where(Pokemon.localizacao == "equipe")
        ) == 6
        ultimo = db.session.get(Pokemon, uuid.UUID(ids[6]))
        assert ultimo is not None and ultimo.localizacao == "box"


def test_box_renderiza_pesquisa_dinamica_com_ordem(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = _personagem_id(app_db)
    _criar_na_box(app_db, client_db, "Bulbasaur")
    _criar_na_box(app_db, client_db, "Charmander")

    resposta = client_db.get(f"/mestre/jogadores/{jogador_id}/boxes")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert 'id="filtro-box-nome"' in texto
    assert "data-box-pokemon-card" in texto
    assert "data-ordem=" in texto
    assert "Adicionar ao time" in texto
    assert "Criar Pokémon" in texto
