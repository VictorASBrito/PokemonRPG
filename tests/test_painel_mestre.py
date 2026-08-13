from __future__ import annotations

import uuid
from decimal import Decimal


from sqlalchemy import select

from app.extensions import db
from app.models.db import Atributo, Campanha, CampanhaMembro, Personagem, PersonagemAtributo, Pokemon, Usuario


def _login_mestre(client_db) -> None:
    resposta = client_db.post(
        "/login",
        data={"login": "mestre-db", "senha": "senha-db"},
    )
    assert resposta.status_code == 302


def test_painel_geral_exibe_resumo_jogador_e_equipe(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": "Bulbasaur"},
    ).status_code == 302

    with app_db.app_context():
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        pokemon_id = str(pokemon.id)

    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": pokemon_id, "destino": "equipe"},
    ).status_code == 302

    resposta = client_db.get("/mestre/dashboard")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Painel geral do mestre" in texto
    assert "Bartz" in texto
    assert "Bulbasaur" in texto
    assert "Pesquisar na campanha" in texto
    assert "PV do treinador" in texto
    assert "data-pv-form" in texto


def test_painel_permite_ajuste_rapido_de_pv(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]

    resposta = client_db.post(
        f"/mestre/painel/personagens/{jogador_id}/pv",
        data={"delta": "-5"},
    )
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["pv_atual"] == 25
    assert dados["pv_maximo"] == 30

    with app_db.app_context():
        personagem = db.session.get(Personagem, uuid.UUID(jogador_id))
        assert personagem is not None
        assert personagem.pv_atual == 25


def test_painel_permite_ajuste_rapido_de_pv_do_pokemon(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": "Charmander"},
    ).status_code == 302

    with app_db.app_context():
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        pokemon_id = str(pokemon.id)
        pv_inicial = pokemon.pv_atual

    resposta = client_db.post(
        f"/mestre/painel/pokemons/{pokemon_id}/pv",
        data={"delta": "-5"},
    )
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["pv_atual"] == max(0, pv_inicial - 5)

    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon is not None
        assert pokemon.pv_atual == max(0, pv_inicial - 5)


def test_painel_exibe_atributos_do_personagem_ao_lado_dos_pv(app_db, client_db) -> None:
    _login_mestre(client_db)
    resposta = client_db.get("/mestre/dashboard")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert 'class="painel-jogador-atributos"' in texto
    assert "Físico" in texto
    assert "Saúde" in texto
    assert 'class="painel-jogador-contadores"' not in texto


def test_mestre_define_e_persiste_ordem_manual_dos_jogadores(app_db, client_db) -> None:
    with app_db.app_context():
        campanha = db.session.execute(select(Campanha).where(Campanha.codigo == "ankar")).scalar_one()
        bartz = db.session.get(Personagem, uuid.UUID(app_db.config["TEST_IDS"]["personagem"]))
        assert bartz is not None
        bartz.ordem_painel = 1

        usuario = Usuario(
            login="segundo-db",
            nome="Segundo jogador",
            senha_hash="hash-teste",
            perfil="jogador",
            ativo=True,
        )
        personagem = Personagem(
            usuario=usuario,
            campanha=campanha,
            nome="Ayla",
            nivel=20,
            pv_atual=20,
            ordem_painel=2,
            ativo=True,
        )
        db.session.add_all([
            usuario,
            personagem,
            CampanhaMembro(campanha=campanha, usuario=usuario, papel="jogador"),
        ])
        db.session.flush()
        atributos = list(
            db.session.execute(
                select(Atributo).where(Atributo.escopo.in_(["personagem", "ambos"]))
            ).scalars()
        )
        for atributo in atributos:
            db.session.add(
                PersonagemAtributo(
                    personagem=personagem,
                    atributo=atributo,
                    valor=Decimal("2"),
                )
            )
        db.session.commit()
        bartz_id = str(bartz.id)
        ayla_id = str(personagem.id)

    _login_mestre(client_db)
    resposta = client_db.post(
        "/mestre/painel/ordem",
        json={"ordem": [ayla_id, bartz_id]},
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["ordem"] == [ayla_id, bartz_id]

    with app_db.app_context():
        ayla = db.session.get(Personagem, uuid.UUID(ayla_id))
        bartz = db.session.get(Personagem, uuid.UUID(bartz_id))
        assert ayla is not None and ayla.ordem_painel == 1
        assert bartz is not None and bartz.ordem_painel == 2

    pagina = client_db.get("/mestre/dashboard").get_data(as_text=True)
    assert pagina.index("Ayla") < pagina.index("Bartz")


def test_mestre_pode_visualizar_mesmo_dashboard_do_jogador(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    resposta = client_db.get(f"/mestre/jogadores/{jogador_id}/preview")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Visualização como jogador" in texto
    assert "Área do jogador" in texto
    assert "Painel de Bartz" in texto
    assert "Minha ficha" in texto
    assert "Voltar ao painel do mestre" in texto
    assert f'/mestre/jogadores/{jogador_id}/equipe' in texto


def test_botoes_voltar_das_telas_do_mestre_retornam_ao_painel(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]

    ficha = client_db.get(f"/mestre/jogadores/{jogador_id}/ficha").get_data(as_text=True)
    equipe = client_db.get(f"/mestre/jogadores/{jogador_id}/equipe").get_data(as_text=True)
    boxes = client_db.get(f"/mestre/jogadores/{jogador_id}/boxes").get_data(as_text=True)
    inventario = client_db.get(f"/mestre/jogadores/{jogador_id}/inventario").get_data(as_text=True)

    for pagina in [ficha, equipe, boxes, inventario]:
        assert 'href="/mestre/dashboard"' in pagina
