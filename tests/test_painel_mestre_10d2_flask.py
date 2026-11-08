"""Integração Flask/SQLite com fixtures existentes do PokemonRPG.

Execute junto à suíte no repositório real. Nenhum acesso ao PostgreSQL de Ankar.
"""
import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import HistoricoAlteracao, Pokemon, PokemonStatus, StatusCondicao


def entrar(client_db):
    resposta = client_db.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'})
    assert resposta.status_code == 302
    assert client_db.get('/mestre/dashboard').status_code == 200
    with client_db.session_transaction() as sessao:
        return sessao['perfil_csrf']


def criar_pokemon_na_box(client_db, app_db):
    pid = app_db.config['TEST_IDS']['personagem']
    assert client_db.post(
        f'/mestre/jogadores/{pid}/equipe/novo?destino=box:box-unica',
        data={'especie_nome': 'Bulbasaur'},
    ).status_code == 302
    with app_db.app_context():
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        status = db.session.execute(select(StatusCondicao).where(StatusCondicao.codigo == 'paralisado')).scalar_one()
        pokemon.pv_atual = 1
        db.session.add(PokemonStatus(pokemon_id=pokemon.id, status_id=status.id))
        db.session.commit()
        return str(pokemon.id)


def test_cura_individual_recupera_box_e_condicao(app_db, client_db):
    token = entrar(client_db)
    pokemon_id = criar_pokemon_na_box(client_db, app_db)
    treinador = app_db.config['TEST_IDS']['personagem']
    resposta = client_db.post(
        f'/mestre/painel/treinadores/{treinador}/curar',
        data={'csrf_token': token, 'confirmar': 'CURAR_POKEMONS'},
        headers={'X-Requested-With': 'fetch'},
    )
    assert resposta.status_code == 200, resposta.get_data(as_text=True)
    assert resposta.json['alterados'] == 1
    assert resposta.json['condicoes_removidas'] == 1
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon.pv_atual > 1
        assert not db.session.execute(select(PokemonStatus).where(PokemonStatus.pokemon_id == pokemon.id)).scalars().all()
        assert db.session.execute(select(HistoricoAlteracao).where(HistoricoAlteracao.acao == 'curar_total_mestre')).scalar_one_or_none()


def test_cura_global_e_csrf(app_db, client_db):
    token = entrar(client_db)
    pokemon_id = criar_pokemon_na_box(client_db, app_db)
    url = '/mestre/painel/curar-todos'
    assert client_db.post(url, data={'csrf_token': 'errado', 'confirmar': 'CURAR_POKEMONS'}).status_code == 400
    assert client_db.post(url, data={'csrf_token': token}).status_code == 400
    resposta = client_db.post(url, data={'csrf_token': token, 'confirmar': 'CURAR_POKEMONS'},
                             headers={'X-Requested-With': 'fetch'})
    assert resposta.status_code == 200, resposta.get_data(as_text=True)
    assert resposta.json['treinadores'] >= 1
    assert resposta.json['alterados'] == 1
    with app_db.app_context():
        assert db.session.get(Pokemon, uuid.UUID(pokemon_id)).pv_atual > 1


def test_jogadores_mesma_central(app_db, client_db):
    entrar(client_db)
    resposta = client_db.get('/mestre/jogadores')
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert 'Curar todos os Pokémon' in texto
    assert 'Gerenciar nível e acesso' in texto
    assert 'data-operacao="menos"' in texto
    assert 'painel-mestre-metricas' not in texto
