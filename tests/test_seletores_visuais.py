"""Contratos de seleção visual: tipos e imagens vêm do catálogo, não do cliente."""
from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models.db import FormaPokemon, Golpe, Item


def _login_mestre(client):
    assert client.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'}).status_code == 302


def test_seletores_visuais_possuem_metadados_e_imagens(app_db, client_db):
    with app_db.app_context():
        charmander = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'charmander')).scalar_one()
        charmander.imagem_url = 'https://example.test/charmander.png'
        item = db.session.execute(select(Item).where(Item.codigo == 'baga-laranja')).scalar_one()
        item.imagem_url = '/static/uploads/itens/baga.png'
        db.session.commit()
    _login_mestre(client_db)

    formas = client_db.get('/api/catalogo/formas?q=char').get_json()['itens']
    char = next(forma for forma in formas if forma['valor'] == 'Charmander')
    assert char['imagem'] == 'https://example.test/charmander.png'
    assert char['tipos'] and {'nome', 'codigo'} <= set(char['tipos'][0])

    golpes = client_db.get('/api/catalogo/golpes?q=chamas').get_json()['itens']
    movimento = next(golpe for golpe in golpes if golpe['valor'] == 'Ataque de Chamas')
    assert movimento['detalhe'] and movimento['tipos']
    assert movimento['imagem'] == ''  # Não existe imagem de golpe no banco.

    itens = client_db.get('/api/catalogo/itens?q=baga').get_json()['itens']
    baga = next(registro for registro in itens if registro['rotulo'] == 'Baga Laranja')
    assert baga['imagem'] == '/static/uploads/itens/baga.png'
    assert baga['valor']
    assert baga['detalhe']


def test_pagina_criacao_e_edicao_usam_seletor_visual(app_db, client_db):
    _login_mestre(client_db)
    personagem_id = app_db.config['TEST_IDS']['personagem']
    pagina = client_db.get(f'/mestre/jogadores/{personagem_id}/equipe/novo?destino=box:box-unica')
    assert pagina.status_code == 200
    assert 'data-seletor-visual="pokemon"' in pagina.get_data(as_text=True)
    assert 'seletor-visual.css' in pagina.get_data(as_text=True)
    inventario = client_db.get(f'/mestre/jogadores/{personagem_id}/inventario')
    assert inventario.status_code == 200
    texto = inventario.get_data(as_text=True)
    assert 'data-seletor-visual="item"' in texto
    assert 'name="item_id" type="hidden"' in texto


def test_itens_somente_para_mestre(client_db):
    assert client_db.get('/api/catalogo/itens?q=baga').status_code in (302, 401, 403)
    client_db.post('/login', data={'login':'bartz-db', 'senha':'abc123'})
    assert client_db.get('/api/catalogo/itens?q=baga').status_code in (302, 401, 403)
