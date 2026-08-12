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
        # Itens agora são equipados exclusivamente pela tela de inventário.
        assert pokemon.item_equipado is None
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


def test_natureza_percentual_aplica_dez_por_cento_e_nao_mil_por_cento(app_db, client_db) -> None:
    from sqlalchemy.orm import selectinload

    from app.models.db import (
        FormaPokemon,
        FormaPokemonAtributo,
        Natureza,
        NaturezaModificador,
        Personagem,
        PokemonBonusAtributo,
        PokemonStatus,
    )
    from app.services.pokemon_db_service import (
        calcular_pokemon,
        carregar_regras_pokemon_db,
    )

    _login_mestre(client_db)
    pokemon_id = _criar_na_box(app_db, client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]

    resposta = client_db.post(
        f"/mestre/jogadores/{jogador_id}/pokemon/{pokemon_id}?retorno=boxes",
        data={
            "retorno": "boxes",
            "especie_nome": "Bulbasaur",
            "apelido": "Broto",
            "genero": "Ø",
            "natureza": "Valente",
            "status": "Nenhum",
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
    )
    assert resposta.status_code == 302

    with app_db.app_context():
        personagem = db.session.execute(
            select(Personagem)
            .where(Personagem.id == uuid.UUID(jogador_id))
            .options(
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.forma_pokemon)
                .selectinload(FormaPokemon.atributos_base)
                .selectinload(FormaPokemonAtributo.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.natureza)
                .selectinload(Natureza.modificadores)
                .selectinload(NaturezaModificador.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.bonus_atributos)
                .selectinload(PokemonBonusAtributo.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.status_ativos)
                .selectinload(PokemonStatus.status),
            )
        ).scalar_one()
        pokemon = next(item for item in personagem.pokemons if str(item.id) == pokemon_id)
        regras = carregar_regras_pokemon_db(personagem.campanha_id)
        calculos = calcular_pokemon(pokemon, personagem, regras)

        # Base 5 no nível 48 vira 52. Valente aumenta Ataque em 10%
        # e reduz Velocidade em 10%; depois o estilo Agressivo soma 10% ao Ataque.
        assert calculos["totais"]["ataque"] == 64
        assert calculos["totais"]["velocidade"] == 46


def test_shiny_aplica_bonus_em_ataque_e_defesa_especiais_com_codigos_importados(
    app_db, client_db
) -> None:
    """O catálogo real usa hífen, enquanto a regra antiga usa sublinhado."""
    from sqlalchemy.orm import selectinload

    from app.models.db import (
        Atributo,
        FormaPokemon,
        FormaPokemonAtributo,
        Natureza,
        NaturezaModificador,
        Personagem,
        PokemonBonusAtributo,
        PokemonStatus,
    )
    from app.services.pokemon_db_service import (
        calcular_pokemon,
        carregar_regras_pokemon_db,
    )

    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]

    # Reproduz exatamente os códigos gerados pelo slug durante a importação real.
    with app_db.app_context():
        ataque_especial = db.session.execute(
            select(Atributo).where(Atributo.codigo == "ataque_especial")
        ).scalar_one()
        defesa_especial = db.session.execute(
            select(Atributo).where(Atributo.codigo == "defesa_especial")
        ).scalar_one()
        ataque_especial.codigo = "ataque-especial"
        defesa_especial.codigo = "defesa-especial"
        db.session.commit()

    pokemon_id = _criar_na_box(app_db, client_db, "Charmander")
    resposta = client_db.post(
        f"/mestre/jogadores/{jogador_id}/pokemon/{pokemon_id}?retorno=boxes",
        data={
            "retorno": "boxes",
            "especie_nome": "Charmander",
            "apelido": "Brasa",
            "genero": "Ø",
            "shiny": "1",
            "natureza": "Dócil",
            "status": "Nenhum",
            "item_carregado": "",
            "pv_atual": "80",
            "bonus_pv": "0",
            "bonus_ataque": "0",
            "bonus_defesa": "0",
            "bonus_ataque-especial": "0",
            "bonus_defesa-especial": "0",
            "bonus_velocidade": "0",
            "golpe_nome": ["", "", "", ""],
            "anotacoes": "",
        },
    )
    assert resposta.status_code == 302

    with app_db.app_context():
        personagem = db.session.execute(
            select(Personagem)
            .where(Personagem.id == uuid.UUID(jogador_id))
            .options(
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.forma_pokemon)
                .selectinload(FormaPokemon.atributos_base)
                .selectinload(FormaPokemonAtributo.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.natureza)
                .selectinload(Natureza.modificadores)
                .selectinload(NaturezaModificador.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.bonus_atributos)
                .selectinload(PokemonBonusAtributo.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.status_ativos)
                .selectinload(PokemonStatus.status),
            )
        ).scalar_one()
        pokemon = next(item for item in personagem.pokemons if str(item.id) == pokemon_id)
        regras = carregar_regras_pokemon_db(personagem.campanha_id)
        calculos = calcular_pokemon(pokemon, personagem, regras)

        # Charmander possui bases 6 e 5. Por ser Shiny, ambas recebem +1.
        assert calculos["bases"]["ataque_especial"] == 7
        assert calculos["bases"]["defesa_especial"] == 6
        # As aliases com hífen alimentam a tela gerada pelos atributos do banco.
        assert calculos["bases"]["ataque-especial"] == 7
        assert calculos["bases"]["defesa-especial"] == 6
