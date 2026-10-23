"""Contrato da camada de frontend transversal, independente do PostgreSQL."""
from pathlib import Path

import tinycss2
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static/css/sistema-ui.css"
TEMPLATES = ROOT / "templates"


def test_folha_transversal_valida_e_carregada_por_ultimo():
    css = CSS.read_text(encoding="utf-8")
    errors = [n for n in tinycss2.parse_stylesheet(css) if n.type == "error"]
    assert errors == []
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    assert base.index("{% block estilos_finais %}") < base.index("css/sistema-ui.css")
    assert 'class="app-shell"' in base
    assert 'id="conteudo-principal"' in base


def test_nav_movel_visivel_e_cartoes_sem_overflow():
    css = CSS.read_text(encoding="utf-8")
    assert "body.app-shell .navegacao-principal {" in css
    assert "display: flex; max-width: 100%" in css
    assert "overflow-x: hidden" in css
    assert "grid-template-columns: clamp(54px, 4.4vw, 74px) minmax(0, 1fr)" in css
    assert "-webkit-line-clamp: 2" in css
    assert "max-width: 100%" in css
    assert 'body.app-shell [hidden] { display: none !important; }' in css


def test_todos_os_templates_compilam_com_o_filtro_proprio_do_site():
    from app.services.tipos_visual import tipo_visual
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    env.filters["tipo_visual"] = tipo_visual
    for path in TEMPLATES.rglob("*.html"):
        env.get_template(path.relative_to(TEMPLATES).as_posix())


def test_senha_sem_inline_style():
    senha = (TEMPLATES / "conta/trocar_senha.html").read_text(encoding="utf-8")
    assert 'style="' not in senha
    assert 'class="conta-senha-formulario"' in senha
