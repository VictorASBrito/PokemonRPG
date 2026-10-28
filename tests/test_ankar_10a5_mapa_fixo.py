"""Etapa 10A.5: mapa inteiro, 119 hotspots, sem zoom, scroll ou seletor redundante."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re

from jinja2 import Environment, ChoiceLoader, DictLoader, FileSystemLoader

RAIZ = Path(__file__).resolve().parents[1]


def _texto(caminho: str) -> str:
    return (RAIZ / caminho).read_text(encoding='utf-8')


def _renderizar():
    dados = json.loads(_texto('app/data/mapa_ankar_pontos.json'))
    catalogo = json.loads(_texto('app/data/catalogo_ankar_visual.json'))
    env = Environment(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block estilos_finais %}{% endblock %}{% block conteudo %}{% endblock %}{% block scripts %}{% endblock %}'}),
        FileSystemLoader(RAIZ / 'templates'),
    ]))
    def url_for(endpoint, **kwargs):
        if endpoint == 'static': return '/static/' + kwargs['filename']
        if endpoint == 'regiao.indice_ankar': return '/regiao/ankar'
        if endpoint == 'regiao.detalhe_ankar': return '/regiao/ankar/' + kwargs['slug']
        raise ValueError(endpoint)
    env.globals['url_for'] = url_for
    return env.get_template('regiao/indice.html').render(mapa=dados, catalogo=catalogo)


def test_filtros_quatro_categorias_e_todos_visiveis_inicialmente():
    html = _renderizar()
    for categoria in ['todos', 'rota', 'cidade', 'interesse']:
        assert f'data-mapa-tipo="{categoria}"' in html
    assert 'data-mapa-tipo="todos" aria-pressed="true"' in html
    assert html.count('data-mapa-id=') == 119
    assert 'data-mapa-zoom=' not in html
    assert 'ankar-mapa-escolher' not in html
    assert 'Localizar no mapa' not in html
    assert 'Zoom do mapa' not in html
    assert 'tabindex="0" aria-label="Mapa' not in html


def test_pontos_corrigidos_e_porcentagens_fieis():
    mapa = json.loads(_texto('app/data/mapa_ankar_pontos.json'))
    pts = mapa['pontos']
    assert len(pts) == 119
    assert len({p['id'] for p in pts}) == 119
    assert Counter(p['tipo'] for p in pts) == {'rota': 73, 'cidade': 26, 'interesse': 20}
    for ponto in pts:
        assert 0 <= ponto['x'] <= 100
        assert 0 <= ponto['y'] <= 100
    por_id = {p['id']: p for p in pts}
    assert abs(por_id['rota-1']['x'] - 625 / 767 * 100) < 0.005
    assert abs(por_id['rota-12']['y'] - 119 / 1024 * 100) < 0.005
    assert abs(por_id['p-13-antiga-usina-nuclear']['x'] - 728 / 767 * 100) < 0.005
    assert abs(por_id['p-15-cratera-heatran']['y'] - 15 / 1024 * 100) < 0.005


def test_mapa_sem_scroll_tooltip_e_zoom_de_escala():
    css = _texto('static/css/atlas-ankar.css')
    js = _texto('static/js/atlas-ankar.js')
    assert 'overflow:hidden' in css
    assert 'content:none!important' in css
    assert 'width:17px;height:17px' in css
    assert "mostrarCategoria('todos')" in js
    assert "tipo !== 'todos' &&" in js
    assert 'window.location.search' in js
    assert 'scrollTo(' not in js
    assert 'scrollLeft' not in js
    assert 'data-mapa-zoom' not in js
    assert 'ankar-mapa-escolher' not in js
    assert 'data-ankar-gerar' in js  # geração de capturáveis não foi alterada


def test_navegacao_preselecionada_preservada():
    html = _renderizar()
    assert 'href="/regiao/ankar/rota-1"' in html
    assert 'href="#ankar-explorador"' in html
    assert 'id="ankar-mapa-info-link"' in html
    assert 'data-mapa-id="p-13-antiga-usina-nuclear"' in html


def test_documentacao_10a5_aditiva_idempotente(tmp_path):
    import importlib.util
    path=RAIZ/'scripts/registrar_atlas_10a5.py'
    spec=importlib.util.spec_from_file_location('doc_ankar_10a5',path)
    modulo=importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(modulo)
    docdir=tmp_path/'docs'; docdir.mkdir()
    for name in ('CONTINUIDADE_PROJETO.md','DIARIO_DESENVOLVIMENTO.md'):
        (docdir/name).write_text('Histórico preservado.\n',encoding='utf-8')
    assert len(modulo.registrar(tmp_path))==2
    assert modulo.registrar(tmp_path)==[]
    for name in ('CONTINUIDADE_PROJETO.md','DIARIO_DESENVOLVIMENTO.md'):
        s=(docdir/name).read_text(encoding='utf-8')
        assert s.startswith('Histórico preservado.')
        assert s.count(modulo.MARCA)==1
