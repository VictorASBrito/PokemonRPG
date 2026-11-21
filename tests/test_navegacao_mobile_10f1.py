"""Regressões estáticas da navegação responsiva, sem PostgreSQL ou Flask."""
from pathlib import Path
import re

import tinycss2

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "static" / "css"


def _estilos_em_media(conteudo: str, consulta: str) -> dict[str, dict[str, str]]:
    """Lê declarações de seletores dentro de um @media específico."""
    estilos = {}
    regras = tinycss2.parse_stylesheet(conteudo, skip_comments=True, skip_whitespace=True)
    for regra in regras:
        if regra.type != "at-rule" or regra.at_keyword != "media":
            continue
        if tinycss2.serialize(regra.prelude).strip() != consulta:
            continue
        internas = tinycss2.parse_rule_list(regra.content, skip_comments=True, skip_whitespace=True)
        for interna in internas:
            if interna.type != "qualified-rule":
                continue
            seletor = tinycss2.serialize(interna.prelude).strip()
            valores = estilos.setdefault(seletor, {})
            for decl in tinycss2.parse_declaration_list(
                interna.content, skip_comments=True, skip_whitespace=True
            ):
                if decl.type == "declaration":
                    valores[decl.lower_name] = re.sub(
                        r"\s+", "", tinycss2.serialize(decl.value)
                    )
    return estilos


def test_css_compartilhado_nao_redefine_layout_do_cabecalho():
    sistema = (CSS / "sistema-ui.css").read_text(encoding="utf-8")
    for seletor in (
        "body.app-shell .topo",
        "body.app-shell .marca",
        "body.app-shell .navegacao-principal",
        "body.app-shell .usuario-topo",
    ):
        assert seletor not in sistema, f"Regra concorrente: {seletor}"
    assert "grid-template-areas" not in sistema


def test_menu_mobile_tem_estados_fechado_aberto_e_layout_proprio():
    visual = (CSS / "visual-global-10c5.css").read_text(encoding="utf-8")
    mobile = _estilos_em_media(visual, "(max-width: 1100px)")

    assert mobile[".topo"]["grid-template-columns"] == "minmax(0,1fr)auto"
    assert mobile[".ui-mobile-nav-toggle"]["display"] == "inline-flex"
    assert mobile[".topo .navegacao-principal"]["display"] == "none"
    assert mobile['.topo[data-ui-nav-open="true"] .navegacao-principal']["display"] == "flex"
    assert mobile[".topo .navegacao-principal a"]["white-space"] == "normal"
    assert mobile[".topo .usuario-topo"]["grid-row"] == "2"
    assert mobile[".topo .navegacao-principal"]["grid-row"] == "3"

    compacto = _estilos_em_media(visual, "(max-width: 900px)")
    assert compacto[".topo .usuario-topo > span"]["display"] == "none"


def test_desktop_preserva_navegacao_e_botao_mobile_oculto():
    geral = (CSS / "geral.css").read_text(encoding="utf-8")
    visual = (CSS / "visual-global-10c5.css").read_text(encoding="utf-8")
    assert ".navegacao-principal {\n    display: flex;" in geral
    assert ".ui-mobile-nav-toggle { display: none; }" in visual


def test_toggle_e_css_versionados_no_template_base():
    base = (RAIZ / "templates/base.html").read_text(encoding="utf-8")
    script = (RAIZ / "static/js/visual-navegacao-10c5.js").read_text(encoding="utf-8")
    assert 'data-ui-nav-toggle aria-controls="ui-navegacao-principal"' in base
    assert 'data-ui-navegacao aria-label="Navegação principal"' in base
    # Valida cache busting sem congelar o identificador de versões futuras.
    assert "filename='css/sistema-ui.css', v='ui2-20261121-" in base
    assert "filename='css/visual-global-10c5.css', v='ui2-20261121-nav-10f1'" in base
    for trecho in ("aria-expanded", "Escape", "pointerdown", "max-width: 1100px"):
        assert trecho in script


def test_css_editados_continuam_parseaveis():
    for arquivo in ("sistema-ui.css", "visual-global-10c5.css"):
        conteudo = (CSS / arquivo).read_text(encoding="utf-8")
        erros = [
            regra for regra in tinycss2.parse_stylesheet(
                conteudo, skip_comments=True, skip_whitespace=True
            ) if regra.type == "error"
        ]
        assert not erros, (arquivo, erros)
