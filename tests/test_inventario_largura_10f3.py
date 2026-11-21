"""Regressão contra recorte lateral da Bag e categorias no celular.

Base estática: não exige dados de jogadores, Flask nem PostgreSQL.
"""
from pathlib import Path

import tinycss2

ROOT = Path(__file__).resolve().parents[1]
VISUAL = ROOT / "static/css/visual-inventario-10c5.css"


def _regras_em_media(texto: str, expressao: str) -> dict[str, dict[str, str]]:
    resultado = {}
    for no in tinycss2.parse_stylesheet(
        texto, skip_whitespace=True, skip_comments=True
    ):
        if no.type != "at-rule" or no.at_keyword != "media":
            continue
        if tinycss2.serialize(no.prelude).strip() != expressao:
            continue
        regras = tinycss2.parse_rule_list(
            no.content, skip_whitespace=True, skip_comments=True
        )
        for regra in regras:
            if regra.type != "qualified-rule":
                continue
            seletor = tinycss2.serialize(regra.prelude).strip()
            propriedades = resultado.setdefault(seletor, {})
            for declaracao in tinycss2.parse_declaration_list(
                regra.content, skip_whitespace=True, skip_comments=True
            ):
                if declaracao.type == "declaration":
                    propriedades[declaracao.lower_name] = (
                        tinycss2.serialize(declaracao.value).strip()
                    )
    return resultado


def test_arte_decorativa_nao_expande_a_largura_do_documento():
    css = VISUAL.read_text(encoding="utf-8")
    tablet = _regras_em_media(css, "(max-width: 1199px)")
    assert tablet[".inventario-nds-bag"]["overflow"] == "visible"
    # O mesmo desenho nao pode escapar nem no desktop >=1200px.
    regra_raiz = [
        no for no in tinycss2.parse_stylesheet(
            css, skip_whitespace=True, skip_comments=True
        )
        if no.type == "qualified-rule"
        and tinycss2.serialize(no.prelude).strip() == ".inventario-nds-bag::after"
    ]
    assert len(regra_raiz) == 1
    arte = {
        dec.lower_name: tinycss2.serialize(dec.value).strip()
        for dec in tinycss2.parse_declaration_list(
            regra_raiz[0].content, skip_whitespace=True, skip_comments=True
        )
        if dec.type == "declaration"
    }
    assert arte["right"] == "0"
    assert arte["width"] == "min(380px, 100%)"
    assert "overflow: hidden" not in arte.values()


def test_todas_as_cinco_abas_cabem_sem_deslizamento_na_tela_de_celular():
    css = VISUAL.read_text(encoding="utf-8")
    telefone = _regras_em_media(css, "(max-width: 540px)")
    faixa = telefone[".inventario-nds-abas"]
    assert faixa["display"] == "grid"
    assert faixa["grid-template-columns"] == "repeat(2, minmax(0, 1fr))"
    assert faixa["width"] == "100%"
    assert faixa["overflow"] == "visible"
    assert faixa["scroll-snap-type"] == "none"
    botao = telefone[".inventario-nds-aba"]
    assert botao["width"] == "100%"
    assert botao["min-width"] == "0"
    assert botao["white-space"] == "normal"
    assert botao["min-height"] == "50px"
    texto = telefone[".inventario-nds-aba-nome"]
    assert texto["overflow"] == "visible"
    assert texto["overflow-wrap"] == "anywhere"

    template = (ROOT / "templates/jogador/inventario.html").read_text(
        encoding="utf-8"
    )
    assert 'class="inventario-nds-abas"' in template
    assert "{% for bolsa in bolsas %}" in template
    assert 'aria-pressed="false"' in template


def test_layout_desktop_e_rolagem_da_equipe_continuam_independentes():
    css = VISUAL.read_text(encoding="utf-8")
    telefone = _regras_em_media(css, "(max-width: 799px)")
    assert telefone[".inventario-nds-equipe-lista"]["overflow-x"] == "auto"
    assert telefone[".inventario-nds-treinador-pokemon"]["flex"] == "0 0 224px"
    tablet = _regras_em_media(css, "(max-width: 1199px)")
    assert tablet[".inventario-nds-abas"]["overflow-x"] == "auto"
    # Fora de 540px as abas seguem roláveis; só o telefone usa grade.


def test_css_valido_e_versao_de_cache_atualizada():
    css = VISUAL.read_text(encoding="utf-8")
    assert not [
        no for no in tinycss2.parse_stylesheet(css) if no.type == "error"
    ]
    template = (ROOT / "templates/jogador/inventario.html").read_text(
        encoding="utf-8"
    )
    assert (
        "filename='css/visual-inventario-10c5.css', v='10c5-ring-10f7'"
        in template
    )
