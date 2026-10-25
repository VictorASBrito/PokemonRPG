"""Regressões da Etapa 07: campo compartilhado com até 16 times."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import Campanha, CampanhaMembro, HistoricoAlteracao, Personagem, Pokemon, PokemonEmCampo, Usuario


def _entrar(client, login="mestre-db", senha="senha-db"):
    resposta = client.post("/login", data={"login": login, "senha": senha})
    assert resposta.status_code == 302


def _sair(client):
    assert client.post("/logout").status_code == 302


def _token(client):
    assert client.get("/campo").status_code == 200
    with client.session_transaction() as sessao:
        return sessao["campo_csrf"]


def _pokemon_equipe(app, client, especie="Bulbasaur"):
    pessoa = app.config["TEST_IDS"]["personagem"]
    resp = client.post(
        f"/mestre/jogadores/{pessoa}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": especie},
    )
    assert resp.status_code == 302
    with app.app_context():
        pokemon = db.session.execute(
            select(Pokemon).where(Pokemon.localizacao == "box", Pokemon.ativo.is_(True))
            .order_by(Pokemon.criado_em.desc())
        ).scalars().first()
        assert pokemon is not None
        pk = str(pokemon.id)
    resp = client.post(
        f"/mestre/jogadores/{pessoa}/boxes/mover",
        data={"pokemon_id": pk, "destino": "equipe"},
    )
    assert resp.status_code == 302
    with app.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pk))
        assert pokemon.localizacao == "equipe"
    return pk


def _posicionar(client, pokemon_id, time, token, follow_redirects=False):
    return client.post(
        "/campo/posicionar",
        data={"pokemon_id": pokemon_id, "time_numero": str(time), "csrf_token": token},
        follow_redirects=follow_redirects,
    )


def test_16_times_e_pokemon_visivel_para_todos(app_db, client_db):
    _entrar(client_db)
    pokemon_id = _pokemon_equipe(app_db, client_db)
    token = _token(client_db)
    assert _posicionar(client_db, pokemon_id, 16, token).status_code == 302
    painel = client_db.get("/campo").get_data(as_text=True)
    assert "Painel de Pokémon em campo" in painel
    assert 'aria-label="Time 16"' in painel
    assert "Bulbasaur" in painel and "Grama" in painel

    with app_db.app_context():
        registro = db.session.execute(select(PokemonEmCampo)).scalar_one()
        assert registro.time_numero == 16
        assert str(registro.pokemon_id) == pokemon_id
    _sair(client_db)
    _entrar(client_db, "bartz-db", "abc123")
    compartilhado = client_db.get("/campo/estado")
    assert compartilhado.status_code == 200
    assert "Bulbasaur" in compartilhado.get_data(as_text=True)
    assert 'aria-label="Time 16"' in compartilhado.get_data(as_text=True)


def test_jogador_posiciona_somente_proprios_pokemons(app_db, client_db):
    _entrar(client_db)
    pokemon_id = _pokemon_equipe(app_db, client_db)
    with app_db.app_context():
        campanha = db.session.execute(select(Campanha).where(Campanha.codigo == "ankar")).scalar_one()
        outro = Usuario(login="outro-atacante", nome="Outro", senha_hash="hash", perfil="jogador", ativo=True)
        treinador = Personagem(usuario=outro, campanha=campanha, nome="Outro Treinador", nivel=5, pv_atual=10, ativo=True)
        db.session.add_all([outro, treinador, CampanhaMembro(campanha=campanha, usuario=outro, papel="jogador")])
        db.session.flush()
        atacante = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        outro_pokemon = Pokemon(personagem=treinador, forma_pokemon_id=atacante.forma_pokemon_id, localizacao="equipe", posicao=1, pv_atual=15, ativo=True)
        db.session.add(outro_pokemon)
        db.session.commit()
        outro_id = str(outro_pokemon.id)
    _sair(client_db)
    _entrar(client_db, "bartz-db", "abc123")
    token = _token(client_db)
    assert _posicionar(client_db, pokemon_id, 1, token).status_code == 302
    assert _posicionar(client_db, outro_id, 2, token).status_code == 403
    assert _posicionar(client_db, pokemon_id, 17, token, follow_redirects=True).status_code == 200
    with app_db.app_context():
        assert db.session.scalar(select(PokemonEmCampo).where(PokemonEmCampo.pokemon_id == uuid.UUID(outro_id))) is None
        registros = list(db.session.execute(select(PokemonEmCampo)).scalars())
        assert len(registros) == 1 and registros[0].time_numero == 1


def test_trocar_time_nao_duplica_e_remover_preserva_equipe(app_db, client_db):
    _entrar(client_db)
    pokemon_id = _pokemon_equipe(app_db, client_db)
    token = _token(client_db)
    assert _posicionar(client_db, pokemon_id, 1, token).status_code == 302
    assert _posicionar(client_db, pokemon_id, 3, token).status_code == 302
    assert _posicionar(client_db, pokemon_id, 3, token).status_code == 302
    with app_db.app_context():
        registros = list(db.session.execute(select(PokemonEmCampo)).scalars())
        assert len(registros) == 1 and registros[0].time_numero == 3
        assert db.session.get(Pokemon, uuid.UUID(pokemon_id)).ativo
    assert client_db.post(f"/campo/pokemons/{pokemon_id}/retirar", data={"csrf_token": token}).status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(PokemonEmCampo)) is None
        assert db.session.get(Pokemon, uuid.UUID(pokemon_id)).localizacao == "equipe"
        eventos = list(db.session.execute(
            select(HistoricoAlteracao).where(HistoricoAlteracao.entidade == "pokemon_em_campo")
        ).scalars())
        assert {e.acao for e in eventos} == {"posicionar", "mudar_time", "retirar"}


def test_pokemon_na_box_nao_pode_entrar_e_mover_para_box_retira_do_campo(app_db, client_db):
    _entrar(client_db)
    pokemon_id = _pokemon_equipe(app_db, client_db)
    token = _token(client_db)
    assert _posicionar(client_db, pokemon_id, 4, token).status_code == 302
    pessoa = app_db.config["TEST_IDS"]["personagem"]
    assert client_db.post(
        f"/mestre/jogadores/{pessoa}/boxes/mover",
        data={"pokemon_id": pokemon_id, "destino": "box:box-unica"},
    ).status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(PokemonEmCampo)) is None
        assert db.session.get(Pokemon, uuid.UUID(pokemon_id)).localizacao == "box"
    pagina = _posicionar(client_db, pokemon_id, 1, token, follow_redirects=True)
    assert "não está disponível na equipe" in pagina.get_data(as_text=True)


def test_mestre_limpa_campo_e_jogador_nao_pode_limpar(app_db, client_db):
    _entrar(client_db)
    pk_a = _pokemon_equipe(app_db, client_db, "Bulbasaur")
    pk_b = _pokemon_equipe(app_db, client_db, "Charmander")
    token = _token(client_db)
    _posicionar(client_db, pk_a, 1, token)
    _posicionar(client_db, pk_b, 12, token)
    with app_db.app_context():
        registros = list(db.session.execute(select(PokemonEmCampo)).scalars())
        assert len(registros) == 2
        assert {r.time_numero for r in registros} == {1, 12}
    assert client_db.post("/campo/limpar", data={"csrf_token": token}, follow_redirects=True).status_code == 200
    with app_db.app_context():
        assert list(db.session.execute(select(PokemonEmCampo)).scalars()) == []
        assert db.session.get(Pokemon, uuid.UUID(pk_a)).ativo
    _sair(client_db)
    _entrar(client_db, "bartz-db", "abc123")
    token_jogador = _token(client_db)
    assert client_db.post("/campo/limpar", data={"csrf_token": token_jogador}).status_code == 403


def test_post_sem_csrf_e_bloqueado(app_db, client_db):
    _entrar(client_db)
    pk = _pokemon_equipe(app_db, client_db)
    assert client_db.post("/campo/posicionar", data={"pokemon_id": pk, "time_numero": "1"}).status_code == 400
    with app_db.app_context():
        assert db.session.scalar(select(PokemonEmCampo)) is None


def test_pokemon_de_outro_jogador_so_pode_ser_retirado_pelo_dono_ou_mestre(app_db, client_db):
    _entrar(client_db)
    pk = _pokemon_equipe(app_db, client_db)
    token = _token(client_db)
    _posicionar(client_db, pk, 1, token)
    # Simula contexto adulterado do jogador: a autorização é confirmada no banco.
    _sair(client_db)
    _entrar(client_db, "bartz-db", "abc123")
    with client_db.session_transaction() as sessao:
        sessao["personagem_id"] = str(uuid.uuid4())
    token2 = _token(client_db)
    assert client_db.post(f"/campo/pokemons/{pk}/retirar", data={"csrf_token": token2}).status_code == 403
    with app_db.app_context():
        assert db.session.scalar(select(PokemonEmCampo)) is not None
