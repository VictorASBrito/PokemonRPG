"""Testes do mapa visual de Ankar, sem servidor nem banco de dados."""
from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

from jinja2 import Environment, ChoiceLoader, DictLoader, FileSystemLoader, select_autoescape

RAIZ = Path(__file__).resolve().parents[1]
MAPA = RAIZ / 'app/data/mapa_ankar_pontos.json'
ATLAS = RAIZ / 'app/data/catalogo_ankar_visual.json'


def _dados():
    mapa = json.loads(MAPA.read_text(encoding='utf-8'))
    atlas = json.loads(ATLAS.read_text(encoding='utf-8'))
    return mapa, atlas


def test_119_marcadores_e_identificadores_do_atlas():
    mapa, atlas = _dados()
    pontos = mapa['pontos']
    assert len(pontos) == 119
    assert len({p['id'] for p in pontos}) == 119
    assert Counter(p['tipo'] for p in pontos) == {'rota': 73, 'cidade': 26, 'interesse': 20}
    assert {p['id'] for p in pontos} == {local['id'] for local in atlas['locais']}


def test_posicoes_numeros_e_fontes_consistentes():
    mapa, atlas = _dados()
    assert 'Mapa.jpg' in mapa['imagem']
    assert (RAIZ / 'static/img/ankar-mapa.jpg').is_file()
    for ponto in mapa['pontos']:
        assert 0 <= ponto['x'] <= 100 and 0 <= ponto['y'] <= 100
        assert ponto['numero'].isdigit()
    assert [p['numero'] for p in mapa['pontos'] if p['tipo']=='rota'] == [str(n) for n in range(1,74)]
    assert len([p for p in mapa['pontos'] if p['id'].startswith('gym-')]) == 18
    assert len([p for p in mapa['pontos'] if p['id'].startswith('aux-')]) == 8
    assert len([p for p in mapa['pontos'] if p['tipo']=='interesse']) == 20


def test_servico_so_leitura_e_consulta_de_slug():
    caminho = RAIZ / 'app/services/regiao_ankar_service.py'
    spec = importlib.util.spec_from_file_location('mapa_ankar_service_test', caminho)
    modulo = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(modulo)
    mapa = modulo.carregar_mapa_ankar()
    assert len(mapa['pontos']) == 119
    assert modulo.ponto_no_mapa('rota-1')['numero'] == '1'
    assert modulo.ponto_no_mapa('p-20-montes-gelados')['numero'] == '20'
    assert modulo.ponto_no_mapa('inexistente') is None


def _ambiente():
    env = Environment(
        loader=ChoiceLoader([
            DictLoader({'base.html': '{% block estilos_finais %}{% endblock %}{% block conteudo %}{% endblock %}{% block scripts %}{% endblock %}'}),
            FileSystemLoader(RAIZ / 'templates'),
        ]),
        autoescape=select_autoescape(['html']),
    )
    def url_for(endpoint, **kwargs):
        if endpoint == 'static':
            return '/static/' + kwargs['filename']
        if endpoint == 'regiao.indice_ankar':
            return '/regiao/ankar' + ('?local='+kwargs['local'] if 'local' in kwargs else '')
        if endpoint == 'regiao.detalhe_ankar':
            return '/regiao/ankar/' + kwargs['slug']
        raise ValueError(endpoint)
    env.globals['url_for'] = url_for
    return env


def test_template_index_marca_pontos_com_links_e_controles():
    mapa, catalogo = _dados()
    html = _ambiente().get_template('regiao/indice.html').render(mapa=mapa, catalogo=catalogo)
    assert html.count('data-mapa-id=') == 119
    assert 'href="/regiao/ankar/rota-1"' in html
    assert 'img/ankar-mapa.jpg' in html
    assert 'id="ankar-mapa-viewport"' in html
    assert 'data-mapa-tipo="todos"' in html
    assert 'data-mapa-zoom' not in html
    assert 'ankar-mapa-escolher' not in html
    assert html.count('data-mapa-tipo=') == 4
    assert 'href="#ankar-explorador"' in html
    assert html.count('class="ankar-local"') == 119


def test_template_detalhe_aponta_para_mapa_sem_alterar_encontros():
    mapa, catalogo = _dados()
    rota1 = next(l for l in catalogo['locais'] if l['id']=='rota-1')
    ponto = next(p for p in mapa['pontos'] if p['id']=='rota-1')
    html = _ambiente().get_template('regiao/detalhe.html').render(local=rota1, ponto_mapa=ponto)
    assert 'href="/regiao/ankar?local=rota-1#ankar-mapa"' in html
    assert 'Tentacool' in html
    assert '60-75' in html


def test_modificacoes_isoladas_no_atlas():
    css = (RAIZ/'static/css/atlas-ankar.css').read_text(encoding='utf-8')
    js = (RAIZ/'static/js/atlas-ankar.js').read_text(encoding='utf-8')
    assert '--surface,' not in css and '--text,' not in css
    assert 'var(--superficie)' in css and 'var(--borda)' in css
    assert 'prefers-reduced-motion' in css
    assert 'aria-pressed' in js
    assert 'ponto.hidden' in js
    assert 'URLSearchParams' in js


def test_registro_documentacao_utf8_idempotente(tmp_path):
    script = RAIZ / 'scripts' / 'registrar_revisao_visual_ankar.py'
    spec = importlib.util.spec_from_file_location('doc_ankar_10a3', script)
    modulo = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(modulo)
    (tmp_path/'docs').mkdir()
    for nome in ('CONTINUIDADE_PROJETO.md', 'DIARIO_DESENVOLVIMENTO.md'):
        (tmp_path/'docs'/nome).write_text('Histórico: Pokémon, região e diálogos.\n', encoding='utf-8')
    assert len(modulo.registrar(tmp_path)) == 2
    assert modulo.registrar(tmp_path) == []
    for nome in ('CONTINUIDADE_PROJETO.md', 'DIARIO_DESENVOLVIMENTO.md'):
        texto = (tmp_path/'docs'/nome).read_text(encoding='utf-8')
        assert texto.count(modulo.MARCA) == 1
        assert texto.startswith('Histórico: Pokémon, região e diálogos.')
