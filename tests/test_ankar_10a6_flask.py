"""Integração Flask (depende do fixture app_db e do banco temporário de testes)."""
from __future__ import annotations

from sqlalchemy import func, select
from app.extensions import db
from app.models.db import FormaPokemon, PokemonCapturavel
from app.services.regiao_ankar_service import carregar_catalogo_ankar


def _entrada(nome: str):
    for local in carregar_catalogo_ankar()['locais']:
        for zi, zona in enumerate(local['zonas']):
            for ti, tabela in enumerate(zona['tabelas']):
                for ei, encontro in enumerate(tabela['encontros']):
                    if encontro.get('pokemon') == nome and not encontro.get('marcador'):
                        return local['id'], zi, ti, ei
    raise AssertionError(f'Encontro não encontrado: {nome}')


def _renomear(app_db, antigo: str, codigo: str, nome: str) -> str:
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == antigo)).scalar_one()
        forma.codigo, forma.nome = codigo, nome
        db.session.commit()
        return str(forma.id)


def test_grimer_alola_tem_sprite_e_pode_ser_gerado(app_db):
    forma_id = _renomear(app_db, 'rattata', 'grimer-alola', 'Grimer (Alola)')
    local, zona, tabela, indice = _entrada('Grimer-A')
    with app_db.test_client() as c:
        assert c.post('/login', data={'login':'mestre-db','senha':'senha-db'}).status_code in (302,303)
        pagina = c.get('/regiao/ankar/'+local)
        assert pagina.status_code == 200
        html = pagina.get_data(as_text=True)
        assert 'Grimer-A' in html and 'grimer-alola' in html
        with c.session_transaction() as s: s['atlas_ankar_gerar_csrf']='token'
        response = c.post('/regiao/ankar/'+local+'/gerar-encontro',data={
            'csrf_token':'token','zona':zona,'tabela':tabela,'indice':indice,
            'forma_id':forma_id, 'encontrado_por_personagem_id':app_db.config['TEST_IDS']['personagem']
        })
        assert response.status_code in (302,303)
        assert '/mestre/capturaveis' in response.location
    with app_db.app_context():
        encontrado = db.session.execute(select(PokemonCapturavel)).scalar_one()
        assert str(encontrado.forma_pokemon_id) == forma_id


def test_nao_aceita_forma_de_outra_especie(app_db):
    _renomear(app_db, 'rattata', 'grimer-alola', 'Grimer (Alola)')
    local, zona, tabela, indice = _entrada('Grimer-A')
    outra_forma_id = app_db.config['TEST_IDS']['formas']['bulbasaur']
    with app_db.test_client() as c:
        c.post('/login', data={'login':'mestre-db','senha':'senha-db'})
        with c.session_transaction() as s: s['atlas_ankar_gerar_csrf']='token'
        response = c.post('/regiao/ankar/'+local+'/gerar-encontro',data={
            'csrf_token':'token','zona':zona,'tabela':tabela,'indice':indice,
            'forma_id':outra_forma_id,'encontrado_por_personagem_id':app_db.config['TEST_IDS']['personagem']
        })
        assert '/mestre/capturaveis' not in response.location
    with app_db.app_context():
        assert db.session.scalar(select(func.count(PokemonCapturavel.id))) == 0


def test_burmy_com_varias_formas_exige_escolha(app_db):
    primeira = _renomear(app_db,'bulbasaur','burmy-planta','Burmy (Planta)')
    segunda = _renomear(app_db,'charmander','burmy-arenoso','Burmy (Arenoso)')
    local, zona, tabela, indice = _entrada('Burmy')
    with app_db.test_client() as c:
        c.post('/login',data={'login':'mestre-db','senha':'senha-db'})
        pagina = c.get('/regiao/ankar/'+local).get_data(as_text=True)
        assert 'Burmy (Planta)' in pagina and 'Burmy (Arenoso)' in pagina
        with c.session_transaction() as s: s['atlas_ankar_gerar_csrf']='token'
        entrada={'csrf_token':'token','zona':zona,'tabela':tabela,'indice':indice,
                 'encontrado_por_personagem_id':app_db.config['TEST_IDS']['personagem']}
        negada = c.post('/regiao/ankar/'+local+'/gerar-encontro', data=entrada)
        assert '/mestre/capturaveis' not in negada.location
        aprovada = c.post('/regiao/ankar/'+local+'/gerar-encontro',data={**entrada,'forma_id':segunda})
        assert '/mestre/capturaveis' in aprovada.location
    with app_db.app_context():
        encontro = db.session.execute(select(PokemonCapturavel)).scalar_one()
        assert str(encontro.forma_pokemon_id) == segunda
        assert str(encontro.forma_pokemon_id) != primeira


def test_busca_indexada_por_pokemon_e_forma(app_db):
    with app_db.test_client() as c:
        c.post('/login',data={'login':'mestre-db','senha':'senha-db'})
        html = c.get('/regiao/ankar').get_data(as_text=True)
        assert 'data-pokemon-indice=' in html
        assert 'Corsola (Galar)' in html
        assert 'data-pokemon-resultado' in html
