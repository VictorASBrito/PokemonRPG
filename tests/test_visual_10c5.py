"""Testes locais sem PostgreSQL para a camada visual da Etapa 10C.5."""
from __future__ import annotations

from pathlib import Path
import importlib.util
import subprocess
import sys

import pytest

RAIZ = Path(__file__).resolve().parents[1]
INSTALADOR = RAIZ / "scripts/instalar_visual_10c5.py"


def _modulo():
    spec = importlib.util.spec_from_file_location("instalar_visual_10c5", INSTALADOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _fixture(raiz: Path):
    arquivos = {
        "templates/base.html": '''<!doctype html>
<html><head>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/avisos-toast-10c4-1.css', v='10c4-1') }}">
</head><body><header class="topo">
{% if session.get('usuario_id') %}
            <nav class="navegacao-principal" aria-label="Navegação principal">
                <a href="{{ url_for('mestre.dashboard') }}">Painel</a>
            </nav>
{% endif %}</header>
    <script src="{{ url_for('static', filename='js/avisos-toast-10c4-1.js', v='10c4-2') }}" defer></script>
</body></html>''',
        "templates/jogador/inventario.html": '''{% extends 'base.html' %}
{% block estilos_finais %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/inventario-uso-10c4.css', v='10c4-2') }}">
{% endblock %}''',
    }
    for arquivo, conteudo in arquivos.items():
        destino = raiz / arquivo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    for arquivo in ["static/css/visual-global-10c5.css", "static/css/visual-inventario-10c5.css", "static/js/visual-navegacao-10c5.js"]:
        destino = raiz / arquivo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes((RAIZ / arquivo).read_bytes())


def test_instala_sem_modificar_rotas_e_idempotente(tmp_path):
    _fixture(tmp_path)
    modulo = _modulo()
    assert modulo.instalar(tmp_path, verificar=True) == ["templates/base.html", "templates/jogador/inventario.html"]
    assert modulo.instalar(tmp_path) == ["templates/base.html", "templates/jogador/inventario.html"]
    assert modulo.instalar(tmp_path) == []
    base = (tmp_path / "templates/base.html").read_text(encoding="utf-8")
    mochila = (tmp_path / "templates/jogador/inventario.html").read_text(encoding="utf-8")
    assert base.count("ANKAR_VISUAL_RESPONSIVO_10C5") == 1
    assert 'aria-expanded="false"' in base
    assert 'data-ui-navegacao' in base
    assert 'visual-global-10c5.css' in base
    assert 'visual-inventario-10c5.css' in mochila
    assert 'inventario-uso-10c4.css' in mochila
    assert 'avisos-toast-10c4-1' in base
    copias = list((tmp_path / "relatorios/backups_ui_10c5").rglob("*.html"))
    assert len(copias) == 2


def test_preflight_nao_grava_se_template_divergir(tmp_path):
    _fixture(tmp_path)
    arquivo = tmp_path / "templates/jogador/inventario.html"
    arquivo.write_text("{% block estilos %}{% endblock %}", encoding="utf-8")
    antes = (tmp_path / "templates/base.html").read_text(encoding="utf-8")
    with pytest.raises(RuntimeError, match="ponto de inserção"):
        _modulo().instalar(tmp_path)
    assert (tmp_path / "templates/base.html").read_text(encoding="utf-8") == antes
    assert not (tmp_path / "relatorios").exists()


def test_preserva_urls_permissoes_e_mensagens(tmp_path):
    _fixture(tmp_path)
    _modulo().instalar(tmp_path)
    base = (tmp_path / "templates/base.html").read_text(encoding="utf-8")
    assert "{{ url_for('mestre.dashboard') }}" in base
    assert "{% if session.get('usuario_id') %}" in base
    assert "get_flashed_messages" not in base  # fixture simplificada, código de toast permanece fora do patch
    assert "type=\"button\"" in base


def test_js_sintaxe_valida():
    processo = subprocess.run(
        ["node", "--check", str(RAIZ / "static/js/visual-navegacao-10c5.js")],
        capture_output=True, text=True, check=False,
    )
    assert processo.returncode == 0, processo.stderr


def _css_blocos_balanceados(css: str) -> bool:
    """Validação estrutural mínima sem dependência de bibliotecas de CSS.

    Ignora comentários e strings para não interpretar chaves em seu conteúdo.
    Quando tinycss2 está instalado, o teste ainda executa sua análise completa.
    """
    pilha = []
    indice = 0
    comentario = False
    aspas = None
    while indice < len(css):
        char = css[indice]
        seguinte = css[indice + 1] if indice + 1 < len(css) else ""
        if comentario:
            if char == "*" and seguinte == "/":
                comentario = False
                indice += 2
                continue
        elif aspas is not None:
            if char == "\\":
                indice += 2
                continue
            if char == aspas:
                aspas = None
        elif char == "/" and seguinte == "*":
            comentario = True
            indice += 2
            continue
        elif char in ("'", '"'):
            aspas = char
        elif char == "{":
            pilha.append("{")
        elif char == "}":
            if not pilha:
                return False
            pilha.pop()
        indice += 1
    return not (comentario or aspas or pilha)


def test_css_estruturado_e_breakpoints():
    global_css = (RAIZ / "static/css/visual-global-10c5.css").read_text(encoding="utf-8")
    mochila = (RAIZ / "static/css/visual-inventario-10c5.css").read_text(encoding="utf-8")
    for css in (global_css, mochila):
        assert "@media" in css
        assert _css_blocos_balanceados(css)
        # Análise extra, opcional: nenhum pacote adicional precisa ser instalado.
        try:
            import tinycss2
        except ModuleNotFoundError:
            pass
        else:
            regras = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
            assert not [r for r in regras if r.type == "error"]
            assert any(r.type == "at-rule" and r.at_keyword == "media" for r in regras)
    assert "max-width: 1100px" in global_css
    assert "max-width: 420px" in global_css
    assert "max-width: 540px" in mochila
    assert "min-width: 800px" in mochila
    assert "overflow-y: auto !important" in mochila
    assert "max-height: none !important" in mochila


def test_melhorias_acessibilidade_e_selecao_nao_interferem_no_consumo():
    js = (RAIZ / "static/js/visual-navegacao-10c5.js").read_text(encoding="utf-8")
    assert "aria-expanded" in js and "Escape" in js and "aria-current" in js
    assert "fetch(" not in js and "POST" not in js
    css = (RAIZ / "static/css/visual-inventario-10c5.css").read_text(encoding="utf-8")
    assert ".inventario-uso-elegivel" in css
    assert ".seletor-visual-resultados" in css
