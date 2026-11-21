"""Contrato do painel Pokémon em notebooks de pouca altura, sem PostgreSQL.

Os estilos são compartilhados pelos dashboards do jogador e do NPC.
"""
from pathlib import Path

import tinycss2

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static/css/dashboard.css"
MEDIA_CURTA = ("(min-width: 901px) and (max-height: 820px), "
               "(min-width: 901px) and (max-width: 1450px)")
MEDIA_DESKTOP = "(min-width: 901px)"


def _media_declaracoes(texto: str, consulta: str) -> dict[str, dict[str, str]]:
    resultado = {}
    for no in tinycss2.parse_stylesheet(
        texto, skip_whitespace=True, skip_comments=True
    ):
        if no.type != "at-rule" or no.at_keyword != "media":
            continue
        if tinycss2.serialize(no.prelude).strip() != consulta:
            continue
        for regra in tinycss2.parse_rule_list(
            no.content, skip_whitespace=True, skip_comments=True
        ):
            if regra.type != "qualified-rule":
                continue
            nome = tinycss2.serialize(regra.prelude).strip()
            props = resultado.setdefault(nome, {})
            for declaracao in tinycss2.parse_declaration_list(
                regra.content, skip_comments=True, skip_whitespace=True
            ):
                if declaracao.type == "declaration":
                    props[declaracao.lower_name] = tinycss2.serialize(
                        declaracao.value
                    ).strip()
    return resultado


def test_desktop_alto_conserva_layout_expandido_original():
    css = CSS.read_text(encoding="utf-8")
    desktop = _media_declaracoes(css, MEDIA_DESKTOP)
    assert desktop["body.dashboard-foco-aberto"]["overflow"] == "hidden"
    assert (
        desktop[".grade-pokemons-dashboard.dashboard-pokemon-modo-foco"]["overflow"]
        == "hidden"
    )


def test_janela_baixa_permite_rolagem_da_pagina_e_da_equipe():
    css = CSS.read_text(encoding="utf-8")
    curto = _media_declaracoes(css, MEDIA_CURTA)
    corpo = curto["body.dashboard-foco-aberto"]
    assert corpo["overflow-y"] == "auto"
    assert corpo["overflow-x"] == "hidden"
    assert curto["body.dashboard-foco-aberto .dashboard-jogador"]["height"] == "auto"
    assert curto["body.dashboard-foco-aberto .coluna-treinador"]["position"] == "static"
    grade = curto[".grade-pokemons-dashboard.dashboard-pokemon-modo-foco"]
    assert grade["height"] == "auto"
    assert grade["overflow"] == "visible"
    assert grade["grid-auto-rows"] == "minmax(96px, auto)"


def test_ficha_em_foco_nao_oculta_acoes_golpes_ou_anotacoes():
    css = CSS.read_text(encoding="utf-8")
    curto = _media_declaracoes(css, MEDIA_CURTA)
    base = ".dashboard-pokemon-modo-foco .pokemon-dashboard-em-foco"
    assert curto[base]["height"] == "auto"
    assert curto[base]["overflow"] == "visible"
    assert curto[base + " .pokemon-dashboard-detalhes-expandidos"]["overflow"] == "visible"
    assert curto[base + " .pokemon-dashboard-detalhes-expandidos"]["height"] == "auto"
    assert curto[base + " .pokemon-dashboard-golpes-detalhados"]["overflow"] == "visible"
    assert curto[base + " .pokemon-dashboard-lista-golpes-detalhados"]["height"] == "auto"
    assert (
        curto[base + " .pokemon-dashboard-lista-golpes-detalhados"]["grid-auto-rows"]
        == "minmax(48px, auto)"
    )
    assert curto[base + " .pokemon-dashboard-anotacoes p"]["overflow"] == "visible"
    assert curto[base + " .pokemon-dashboard-anotacoes p"]["display"] == "block"


def test_companheiros_npc_jogador_e_menus_continuam_no_fluxo():
    css = CSS.read_text(encoding="utf-8")
    curto = _media_declaracoes(css, MEDIA_CURTA)
    assert curto[".dashboard-pokemon-modo-foco .pokemon-dashboard-lateral"]["overflow"] == "visible"
    assert curto[".dashboard-pokemon-modo-foco .pokemon-dashboard-lateral"]["height"] == "auto"

    jogador = (ROOT / "templates/jogador/dashboard.html").read_text(encoding="utf-8")
    npc = (ROOT / "templates/mestre/catalogo/npc_painel.html").read_text(encoding="utf-8")
    versao = "filename='css/dashboard.css', v='10f9-tipos-atributos-r3'"
    assert versao in jogador and versao in npc
    assert "data-dashboard-pokemon-grid" in jogador and "data-dashboard-pokemon-grid" in npc
    assert "data-dashboard-pokemon-collapse" in jogador and "data-dashboard-pokemon-collapse" in npc
    assert "data-pokemon-confirmacao-modal" in jogador and "data-pokemon-confirmacao-modal" in npc


def test_css_valido_e_regra_de_excecao_vem_apos_regra_original():
    css = CSS.read_text(encoding="utf-8")
    assert not [
        regra for regra in tinycss2.parse_stylesheet(css) if regra.type == "error"
    ]
    assert css.index("10F.4 — Acesso aos detalhes") > css.index(
        "Modo expandido sem rolagem da página (desktop)"
    )
    assert css.index("10F.4 — Acesso aos detalhes") < css.index(
        "Padronização de proporções da grade Pokémon"
    )
