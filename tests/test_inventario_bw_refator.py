"""Regressões da mochila B&W: fluxo real, assets e classificação estável."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models.db import FormaPokemon, Item, Personagem, PersonagemItem, Pokemon
from app.services.inventario_apresentacao import BOLSAS, VERSAO_INTERFACE, bolsa_item


def mock_item(nome: str, categoria: str = "", descricao: str = ""):
    return SimpleNamespace(
        nome=nome,
        codigo=nome.lower().replace(' ', '-'),
        descricao=descricao,
        categoria=SimpleNamespace(nome=categoria, codigo=categoria.lower().replace(' ', '-')),
    )


@pytest.mark.parametrize('nome,categoria,descricao,esperado', [
    ('Frutinha', 'Inventário dos personagens', 'Cura 20', 'frutas'),
    ('Baga Laranja', 'Bagas', 'Recupera pontos de vida', 'frutas'),
    ('Super Poção', 'Remédios', 'Recupera pontos de vida', 'cura'),
    ('Ultra Ball', 'Captura', '', 'pokebolas'),
    ('Chave da Torre', 'Itens-chave', '', 'chave'),
    ('Carvão', 'Itens gerais', 'Melhora golpes de fogo', 'avulsos'),
])
def test_categorizacao_da_mochila(nome, categoria, descricao, esperado):
    assert bolsa_item(mock_item(nome, categoria, descricao)) == esperado


def test_assinatura_da_tela_estilos_depois_do_tema_e_assets(app_db, client_db):
    assert client_db.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'}).status_code == 302
    personagem_id = app_db.config['TEST_IDS']['personagem']
    response = client_db.get(f'/mestre/jogadores/{personagem_id}/inventario')
    texto = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.headers['X-PokemonRPG-Inventario'] == VERSAO_INTERFACE
    assert response.headers['Cache-Control'] == 'no-store'
    assert f'data-inventario-versao="{VERSAO_INTERFACE}"' in texto
    assert texto.index('css/tema.css') < texto.index('css/inventario.css')
    assert f'css/inventario.css?v={VERSAO_INTERFACE}' in texto
    assert f'js/inventario.js?v={VERSAO_INTERFACE}' in texto
    assert '<strong>BAG</strong>' in texto
    for bolsa in BOLSAS:
        assert bolsa['codigo'] in texto
        assert f'img/inventory/{bolsa["icone"]}' in texto
        assert f'img/inventory/{bolsa["arte"]}' in texto
        assert client_db.get(f'/static/img/inventory/{bolsa["icone"]}').status_code == 200
        assert client_db.get(f'/static/img/inventory/{bolsa["arte"]}').status_code == 200
    assert 'data-seletor-visual="item"' in texto
    assert 'inventario-nds' in texto
    assert 'Pesquisar na mochila' not in texto


def test_jogador_ve_a_mochila_e_pokemon_no_lado_esquerdo(app_db, client_db):
    with app_db.app_context():
        import uuid
        personagem = db.session.get(Personagem, uuid.UUID(app_db.config['TEST_IDS']['personagem']))
        forma = db.session.query(FormaPokemon).filter_by(codigo='charmander').one()
        baga = db.session.query(Item).filter_by(codigo='baga-laranja').one()
        db.session.add(Pokemon(personagem=personagem, forma_pokemon=forma, apelido='Brasinha', localizacao='equipe', posicao=1, pv_atual=20, ativo=True))
        db.session.add(PersonagemItem(personagem=personagem, item=baga, quantidade=2))
        db.session.commit()
    assert client_db.post('/login', data={'login': 'bartz-db', 'senha': 'abc123'}).status_code == 302
    response = client_db.get('/jogador/inventario')
    texto = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Brasinha' in texto
    assert 'Baga Laranja' in texto
    assert 'data-bolsa="frutas"' in texto
    assert '/jogador/inventario/usar' in texto
    assert '/mestre/jogadores/' not in texto
    assert 'Gerenciamento do mestre' not in texto


def test_versao_dos_assets_revisada():
    root = Path(__file__).resolve().parents[1]
    assert 'BW6: painel de mochila alinhado' in (root / 'static/css/inventario.css').read_text(encoding='utf-8')
    codigo = (root / 'static/js/inventario.js').read_text(encoding='utf-8')
    assert 'selectBag(' in codigo
    assert 'selectItem(' in codigo


def test_categorias_identificadas_e_contador_alinhado(app_db, client_db):
    assert client_db.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'}).status_code == 302
    personagem_id = app_db.config['TEST_IDS']['personagem']
    pagina = client_db.get(f'/mestre/jogadores/{personagem_id}/inventario').get_data(as_text=True)
    assert 'inventario-nds-toolbar-resumo' in pagina
    assert 'inventario-nds-toolbar-counter' in pagina
    assert 'inventario-nds-aba-nome' in pagina
    assert 'inventario-nds-aba-icone' in pagina
    for bolsa in BOLSAS:
        assert bolsa['nome'] in pagina
        assert bolsa['icone'].endswith('-hq.png')
        assert f'img/inventory/{bolsa["icone"]}' in pagina


def test_layout_compacto_preserva_rolagem_interna():
    root = Path(__file__).resolve().parents[1]
    css = (root / 'static/css/inventario.css').read_text(encoding='utf-8')
    assert 'height: calc(100dvh - 92px)' in css
    assert 'overflow-y: auto' in css
    assert 'grid-template-columns: minmax(0, 1fr) 220px' in css
    assert 'image-rendering: pixelated' in css
