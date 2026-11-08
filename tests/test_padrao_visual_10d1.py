"""Testes independentes de PostgreSQL para a Etapa 10D.1.

Nao dependem de tinycss2 ou de caminhos POSIX do sistema operacional.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _modulo():
    fonte = ROOT / 'scripts' / 'instalar_padrao_visual_10d1.py'
    spec = importlib.util.spec_from_file_location('instalar_padrao_visual_10d1', fonte)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _modelo(tmp_path):
    base = tmp_path / 'templates' / 'base.html'
    base.parent.mkdir(parents=True)
    base.write_text('''<!doctype html>
<html><head>
    {# ANKAR_VISUAL_RESPONSIVO_10C5 #}
    <link rel="stylesheet" href="{{ url_for('static', filename='css/visual-global-10c5.css', v='10c5-1') }}">
</head><body><header class="topo"></header>
    </header>

    <main class="conteudo" id="conteudo-principal" tabindex="-1"></main>
</body></html>
''', encoding='utf-8')
    return base


def test_verificacao_sem_gravacao_e_caminhos_windows(tmp_path):
    modelo = _modelo(tmp_path)
    antes = modelo.read_bytes()
    retorno = _modulo().instalar(tmp_path, verificar=True)
    assert retorno == ['templates/base.html']
    assert modelo.read_bytes() == antes
    assert not (tmp_path / 'relatorios').exists()


def test_instalacao_idempotente_com_backup(tmp_path):
    arquivo = _modelo(tmp_path)
    antes = arquivo.read_bytes()
    modulo = _modulo()
    assert modulo.instalar(tmp_path) == ['templates/base.html']
    depois = arquivo.read_text(encoding='utf-8')
    assert depois.count(modulo.MARCADOR) == 1
    assert depois.count('class="ui10d-menu-contexto"') == 1
    assert modulo.instalar(tmp_path) == []
    assert arquivo.read_text(encoding='utf-8') == depois
    backups = list((tmp_path / 'relatorios' / 'backups_ui_10d1').glob('*/templates/base.html'))
    assert len(backups) == 1
    assert backups[0].read_bytes() == antes


def test_incompativel_nao_modifica_original(tmp_path):
    arquivo = _modelo(tmp_path)
    texto = arquivo.read_text(encoding='utf-8').replace('visual-global-10c5.css', 'versao-diferente.css')
    arquivo.write_text(texto, encoding='utf-8')
    from pytest import raises
    with raises(RuntimeError):
        _modulo().instalar(tmp_path)
    assert arquivo.read_text(encoding='utf-8') == texto


def test_links_do_catalogo_e_permissoes_existentes():
    m = _modulo()
    assert "ui10d_endpoint.startswith('catalogo_admin.')" in m.MENU_CATALOGO
    for nome in ['dashboard', 'pokemons', 'golpes', 'itens']:
        assert f"url_for('catalogo_admin.{nome}')" in m.MENU_CATALOGO
    assert 'aria-current="page"' in m.MENU_CATALOGO
    assert not any(palavra in m.MENU_CATALOGO for palavra in ['session.clear', 'usuario_id=', 'db.session'])


def test_jinja_compila_com_menu_contextual(tmp_path):
    arquivo = _modelo(tmp_path)
    _modulo().instalar(tmp_path)
    from jinja2 import Environment
    Environment().parse(arquivo.read_text(encoding='utf-8'))


def test_css_possui_breakpoints_e_nao_exige_bibliotecas():
    css = (ROOT / 'static' / 'css' / 'padrao-visual-10d1.css').read_text(encoding='utf-8')
    assert 'display: block;' in css
    assert '.cabecalho-pagina.cabecalho-com-acoes > div:first-child' in css
    for q in ['max-width: 1100px', 'max-width: 700px', 'max-width: 420px']:
        assert q in css
    assert 'aria-current="page"' in css
    assert 'overflow-x: auto' in css
    assert '@media (prefers-reduced-motion: reduce)' in css
    # CSS inteiro é independente de funcionalidades Flask e não há !important global.
    assert 'body { display:' not in css


def test_diagnostico_documentado():
    doc = (ROOT / 'docs' / 'AUDITORIA_UX_FUNCIONAL_10D1.md').read_text(encoding='utf-8')
    assert 'a7198a1' in doc
    for ponto in ['Catálogo', 'Inventário', 'Atlas', 'Capturáveis', 'Campo', 'Acesso']:
        assert ponto in doc
    assert 'Não alterado' in doc
