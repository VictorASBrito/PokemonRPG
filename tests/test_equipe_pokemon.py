from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import Pokemon, PokemonGolpe


def _login_mestre(client) -> None:
    assert client.post(
        "/login", data={"login": "mestre-db", "senha": "senha-db"}
    ).status_code == 302


def _criar_na_box(app, client, especie: str = "Bulbasaur") -> str:
    jogador_id = app.config["TEST_IDS"]["personagem"]
    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": especie},
    )
    assert resposta.status_code == 302
    with app.app_context():
        pokemon = db.session.execute(
            select(Pokemon).order_by(Pokemon.criado_em.desc())
        ).scalars().first()
        assert pokemon is not None
        return str(pokemon.id)


def test_adicionar_na_box_e_editar_pokemon_sem_pp_xp_ou_amizade(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    pokemon_id = _criar_na_box(app_db, client_db)

    resposta = client_db.post(
        f"/mestre/jogadores/{jogador_id}/pokemon/{pokemon_id}?retorno=boxes",
        data={
            "retorno": "boxes",
            "especie_nome": "Bulbasaur",
            "apelido": "Broto",
            "genero": "♂",
            "natureza": "Valente",
            "status": "Paralisado",
            "item_carregado": "Baga Laranja",
            "pv_atual": "70",
            "bonus_pv": "0",
            "bonus_ataque": "2",
            "bonus_defesa": "0",
            "bonus_ataque_especial": "0",
            "bonus_defesa_especial": "0",
            "bonus_velocidade": "0",
            "golpe_nome": ["Arranhão", "Ataque de Chamas", "", ""],
            "anotacoes": "Inicial do Bartz",
        },
    )
    assert resposta.status_code == 302

    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon is not None
        assert pokemon.apelido == "Broto"
        assert pokemon.genero == "♂"
        assert pokemon.natureza.nome == "Valente"
        assert pokemon.item_equipado.nome == "Baga Laranja"
        assert pokemon.status_ativos[0].status.nome == "Paralisado"
        golpes = list(
            db.session.execute(
                select(PokemonGolpe)
                .where(PokemonGolpe.pokemon_id == pokemon.id)
                .order_by(PokemonGolpe.posicao)
            ).scalars()
        )
        assert [item.golpe.nome for item in golpes] == ["Arranhão", "Ataque de Chamas"]
        colunas = Pokemon.__table__.c
        assert "nivel" not in colunas
        assert "experiencia" not in colunas
        assert "amizade" not in colunas


def test_nivel_do_pokemon_vem_do_jogador_e_status_altera_calculo(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    pokemon_id = _criar_na_box(app_db, client_db)

    resposta = client_db.post(
        f"/mestre/jogadores/{jogador_id}/pokemon/{pokemon_id}?retorno=boxes",
        data={
            "retorno": "boxes",
            "especie_nome": "Bulbasaur",
            "apelido": "Broto",
            "genero": "Ø",
            "natureza": "Dócil",
            "status": "Paralisado",
            "item_carregado": "",
            "pv_atual": "80",
            "bonus_pv": "0",
            "bonus_ataque": "0",
            "bonus_defesa": "0",
            "bonus_ataque_especial": "0",
            "bonus_defesa_especial": "0",
            "bonus_velocidade": "0",
            "golpe_nome": ["", "", "", ""],
            "anotacoes": "",
        },
        follow_redirects=True,
    )
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Nível compartilhado" in texto
    assert ">48<" in texto
    assert "Pontos de Poder" not in texto
    assert "Experiência" not in texto
    assert "Amizade" not in texto


def test_tela_da_equipe_direciona_espacos_vazios_para_box(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    resposta = client_db.get(f"/mestre/jogadores/{jogador_id}/equipe")
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Gerenciar pela Box" in texto
    assert "Adicione um Pokémon pela Box" in texto
    assert f"/mestre/jogadores/{jogador_id}/boxes" in texto
    assert "Adicionar Pokémon" not in texto
