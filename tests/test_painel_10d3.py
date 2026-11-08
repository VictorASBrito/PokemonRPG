"""Testes sem conexão com PostgreSQL ou dependência do Flask."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import importlib.util
import tempfile

from jinja2 import Environment, DictLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
MODELO = (ROOT / 'patch_10d3/dashboard.html').read_text(encoding='utf-8')
CSS = (ROOT / 'static/css/painel-mestre-10d3.css').read_text(encoding='utf-8')


def _modulo():
    caminho = ROOT / 'scripts/instalar_painel_10d3.py'
    spec = importlib.util.spec_from_file_location('instalador_10d3', caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _render(jogadores):
    env = Environment(
        loader=DictLoader({
            'painel.html': MODELO,
            'base.html': '{% block estilos %}{% endblock %}<main>{% block conteudo %}{% endblock %}</main>{% block scripts %}{% endblock %}',
            'componentes/tipos.html': '{% macro selo_tipo(tipo) %}<span class="tipo-chip">{{ tipo }}</span>{% endmacro %}',
        }),
        autoescape=select_autoescape(default_for_string=True, default=True),
    )
    env.globals['url_for'] = lambda endpoint, **kwargs: '/' + endpoint.replace('.', '/') + ''.join('/' + str(z) for k,z in kwargs.items() if k != 'v')
    return env.get_template('painel.html').render(
        campanha={'nome': 'Ankar', 'descricao': 'Campanha'}, resumo={},
        jogadores=jogadores, nivel_csrf_token='csrf-sintetico'
    )


def _jogador():
    return {
        'id': 'treinador-1', 'usuario_id': 'usuario-1', 'nome': 'Power',
        'jogador': 'Tuts', 'login': 'tuts', 'sprite_url': '/static/img/login-personagens/slot-05.png',
        'nivel': 40, 'classe': 'Detetive', 'origem': 'Atleta', 'perfil': 'jogador',
        'pokedolares': 98, 'pv_atual': 30, 'pv_maximo': 30, 'equipe_total': 6,
        'limite_equipe': 6, 'box_total': 24, 'acesso_ativo': True, 'alertas': [],
        'busca': 'power tuts',
        'atributos': [{'nome': n, 'valor': i} for i,n in enumerate(('Físico','Destreza','Saúde','Conhecimento','Comunicação','Espírito'), 1)],
        'equipe': [
            {'id': f'pokemon-{i}', 'nome': 'Muchalucha' if i == 0 else 'Charmander',
             'especie': 'Hawlucha' if i == 0 else 'Charmander', 'tipos': ['Lutador'],
             'pv_atual': 20, 'pv_maximo': 80, 'status': [], 'imagem': '/sprite.png'}
            for i in range(6)
        ],
    }


def test_template_jinja_renderiza_e_mantem_elementos_de_interacao():
    html = _render([_jogador()])
    for trecho in ('class="painel-jogador-atributos"', 'data-painel-jogador',
                   'data-pv-form', 'data-operacao="mais"', 'data-operacao="menos"',
                   'data-cura-global="true"', 'data-cura-10d2', 'data-menu-opcoes',
                   'data-mover-ordem="cima"', 'data-ordem-url', 'painel-jogador-rodape'):
        assert trecho in html, trecho
    assert html.count('class="painel-pokemon-card"') == 6
    assert 'Hawlucha' in html and 'Muchalucha' in html
    assert 'Ver atributos do treinador' not in html
    assert 'Nível' in html and 'Salvar perfil' in html
    assert 'csrf-sintetico' in html
    assert 'painel-mestre-10d3.js' in html


def test_template_vazio_renderiza_sem_erros():
    html = _render([])
    assert 'Nenhum jogador cadastrado' in html
    assert 'Curar todos os Pokémon' in html
    assert 'data-painel-jogador' not in html


def test_css_traz_grid_2x3_e_responsividade():
    assert 'grid-template-columns: repeat(2,minmax(0,1fr))' in CSS
    assert '@media (min-width: 860px)' in CSS
    assert '@media (min-width: 1350px)' in CSS
    assert '@media (min-width: 1900px)' in CSS
    assert '@media (max-width: 440px)' in CSS
    assert '.painel-jogador-status' in CSS and '.painel-jogador-gestao-conteudo' in CSS


def test_instalador_windows_e_backup_e_idempotencia(tmp_path):
    modulo = _modulo()
    antigo = '<!-- ANKAR_10D2_CENTRAL_MESTRE -->\n' + '\n'.join(modulo.MARCADORES_ORIGEM)
    destino = tmp_path / 'templates/mestre/dashboard.html'
    destino.parent.mkdir(parents=True)
    destino.write_text(antigo, encoding='utf-8')
    pasta = tmp_path / 'patch_10d3'
    pasta.mkdir()
    (pasta / 'dashboard.html').write_text(MODELO, encoding='utf-8')
    css = tmp_path / 'static/css/painel-mestre-10d3.css'
    css.parent.mkdir(parents=True)
    css.write_text(CSS, encoding='utf-8')
    assert modulo.instalar(tmp_path, verificar=True) == ['templates/mestre/dashboard.html']
    assert destino.read_text(encoding='utf-8') == antigo
    assert modulo.instalar(tmp_path) == ['templates/mestre/dashboard.html']
    assert modulo.MARCADOR_DESTINO in destino.read_text(encoding='utf-8')
    assert modulo.instalar(tmp_path) == []
    copias = list((tmp_path / 'relatorios/backups_ui_10d3').rglob('dashboard.html'))
    assert len(copias) == 1 and copias[0].read_text(encoding='utf-8') == antigo


def test_instalador_bloqueia_template_incompativel(tmp_path):
    modulo = _modulo()
    destino = tmp_path / 'templates/mestre/dashboard.html'
    destino.parent.mkdir(parents=True)
    destino.write_text('versão antiga', encoding='utf-8')
    for p, value in ((tmp_path / 'patch_10d3/dashboard.html', MODELO),
                     (tmp_path / 'static/css/painel-mestre-10d3.css', CSS)):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value, encoding='utf-8')
    try:
        modulo.instalar(tmp_path)
        assert False, 'Deveria impedir a instalação'
    except modulo.InstalacaoIncompativel:
        assert destino.read_text(encoding='utf-8') == 'versão antiga'
