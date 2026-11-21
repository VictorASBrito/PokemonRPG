"""Contrato transversal: design system, assets e organização do repositório.

Sem acesso a banco, HTTP externo ou arquivos pessoais de jogadores.
"""
from __future__ import annotations

import re
from pathlib import Path

import tinycss2
from jinja2 import Environment, FileSystemLoader

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "static/css"
TEMPLATES = RAIZ / "templates"


def _texto(relativo: str) -> str:
    return (RAIZ / relativo).read_text(encoding="utf-8")


def test_design_system_centraliza_tokens_sem_esconder_titulos():
    base = _texto("templates/base.html")
    central = _texto("static/css/sistema-ui.css")
    padrao = _texto("static/css/padrao-visual-10d1.css")
    geral = _texto("static/css/geral.css")
    assert "css/refinamento.css" not in base
    assert not (CSS / "refinamento.css").exists()
    for nome in (
        "--ui-radius-xs", "--ui-radius-md", "--ui-page-gutter",
        "--ui-control-height", "--ui-field-height", "--ui-v10-gutter",
        "--ui10d-raio", "--ui10d-gap",
    ):
        assert nome in central
    assert ".cabecalho-dashboard > div:first-child" in padrao
    assert "display: block" in padrao
    assert "display: none" not in central.split("Densidade operacional única")[1].split("Componentes transversais")[0]
    assert "Layout operacional: usa toda a tela" not in geral


def test_css_globais_sao_validos_e_ordem_preservada():
    base = _texto("templates/base.html")
    csss = [
        "geral.css", "tema.css", "sistema-ui.css",
        "visual-global-10c5.css", "padrao-visual-10d1.css",
    ]
    for nome in csss:
        css = _texto(f"static/css/{nome}")
        erros = [
            item for item in tinycss2.parse_stylesheet(
                css, skip_comments=True, skip_whitespace=True
            ) if item.type == "error"
        ]
        assert not erros, (nome, erros)
        assert base.count(f"filename='css/{nome}'") == 1
    assert base.index("css/geral.css") < base.index("css/tema.css")
    assert base.index("css/tema.css") < base.index("css/sistema-ui.css")
    assert base.index("css/sistema-ui.css") < base.index("css/visual-global-10c5.css")
    assert base.index("css/visual-global-10c5.css") < base.index("css/padrao-visual-10d1.css")


def test_arquivos_css_estaticos_referenciados_nos_templates_existem():
    padrao = re.compile(r"filename\s*=\s*['\"](css/[^'\"]+\.css)['\"]")
    faltando = set()
    for template in TEMPLATES.rglob("*.html"):
        for recurso in padrao.findall(template.read_text(encoding="utf-8")):
            if not (RAIZ / "static" / recurso).is_file():
                faltando.add((str(template.relative_to(RAIZ)), recurso))
    assert not faltando, sorted(faltando)


def test_arquivos_historicos_fora_da_raiz_e_backup_nao_versionado():
    assert (RAIZ / "README.md").is_file()
    for nome in (
        "INSTRUCOES_LEGADAS_10A_10B.md",
        "README_ETAPAS_LEGADAS_10C_10D.md",
        "INSTALADORES_POWERSHELL_LEGADOS.md",
    ):
        assert (RAIZ / "docs/historico" / nome).is_file()
    assert not list(RAIZ.glob("INSTRUCOES_*.txt"))
    assert not list(RAIZ.glob("README_10*.txt"))
    assert not list(RAIZ.glob("INSTALAR_*.ps1"))
    assert not list(RAIZ.glob("APLICAR_*.ps1"))
    assert not list((RAIZ / "relatorios").glob("backups_ui_*/*/*"))
    assert not list((RAIZ / "templates").rglob("*.bak*"))
    assert not list((RAIZ / "app").rglob("*.bak*"))
    assert not list((RAIZ / "static").rglob("*.bak*"))
    assert not list((RAIZ / "tests").rglob("*.bak*"))
    ignorados = _texto(".gitignore")
    assert "*.bak-*" in ignorados
    assert "relatorios/backups_ui_*/" in ignorados


def test_migrations_e_recursos_criticos_permanece():
    versoes = list((RAIZ / "migrations/versions").glob("*.py"))
    assert len(versoes) >= 15
    assert (RAIZ / "static/img/inventory/itens/keystone.png").is_file()
    assert (RAIZ / "data/ankar").is_dir()
    assert (RAIZ / "static/img/pokemon-hd").is_dir()
    assert (RAIZ / "tests/test_painel_npcs_10d4_5.py").is_file()


def test_templates_continuam_compilaveis():
    from app.services.tipos_visual import tipo_visual

    env = Environment(loader=FileSystemLoader(TEMPLATES))
    env.filters["tipo_visual"] = tipo_visual
    for template in TEMPLATES.rglob("*.html"):
        env.get_template(template.relative_to(TEMPLATES).as_posix())
