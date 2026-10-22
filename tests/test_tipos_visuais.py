"""Regressões das etiquetas CSS de tipos em português."""
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.tipos_visual import tipo_visual


@pytest.mark.parametrize('entrada,codigo,traducao', [
    ('Bug', 'bug', 'Inseto'), ('Dark', 'dark', 'Noturno'),
    ('Dragon', 'dragon', 'Dragão'), ('Electric', 'electric', 'Elétrico'),
    ('Fairy', 'fairy', 'Fada'), ('Fighting', 'fighting', 'Lutador'),
    ('Fire', 'fire', 'Fogo'), ('Flying', 'flying', 'Voador'),
    ('Ghost', 'ghost', 'Fantasma'), ('Grass', 'grass', 'Grama'),
    ('Ground', 'ground', 'Terra'), ('Ice', 'ice', 'Gelo'),
    ('Normal', 'normal', 'Normal'), ('Poison', 'poison', 'Veneno'),
    ('Psychic', 'psychic', 'Psíquico'), ('Rock', 'rock', 'Pedra'),
    ('Steel', 'steel', 'Metal'), ('Water', 'water', 'Água'),
    ('Fogo', 'fire', 'Fogo'), ('Água', 'water', 'Água'),
    ('Aço', 'steel', 'Metal'), ('Lutador', 'fighting', 'Lutador'),
])
def test_18_tipos_traduzidos_e_aliases(entrada, codigo, traducao):
    assert tipo_visual(entrada) == {'codigo': codigo, 'nome': traducao}


def test_tipos_personalizados_usam_classe_segura_e_nome_original():
    assert tipo_visual('Ankar Solar') == {
        'codigo': 'personalizado', 'nome': 'Ankar Solar',
    }
    assert tipo_visual('<img src=x onerror=alert(1)>')['codigo'] == 'personalizado'


def test_macro_e_etiqueta_css_sem_png_e_texto_escapado():
    raiz = Path(__file__).resolve().parents[1]
    env = Environment(
        loader=FileSystemLoader(raiz / 'templates'),
        autoescape=select_autoescape(['html']),
    )
    env.filters['tipo_visual'] = tipo_visual
    macro = env.get_template('componentes/tipos.html').module.selo_tipo
    assert 'etiqueta-tipo--fire' in str(macro('Fire'))
    assert '>Fogo</span>' in str(macro('Fire'))
    assert '<img' not in str(macro('Fire'))
    html_inseguro = str(macro('<script>alert(1)</script>'))
    assert '<script>' not in html_inseguro
    assert '&lt;script&gt;' in html_inseguro
    assert 'etiqueta-tipo--personalizado' in html_inseguro
    estilos = (raiz / 'static/css/tipos.css').read_text(encoding='utf-8')
    for codigo in (
        'normal', 'fire', 'water', 'electric', 'grass', 'ice', 'fighting',
        'poison', 'ground', 'flying', 'psychic', 'bug', 'rock', 'ghost',
        'dragon', 'dark', 'steel', 'fairy', 'personalizado',
    ):
        assert f'.etiqueta-tipo--{codigo}' in estilos
    assert not list((raiz / 'static/img/tipos').glob('*.png'))
