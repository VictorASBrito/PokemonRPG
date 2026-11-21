"""Regressão da Bag em telas pequenas, sem Flask ou banco de dados."""
from pathlib import Path

import tinycss2

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static/css"


def _declaracoes(conteudo, seletor, media=None):
    """Extrai declarações de um seletor em um @media exato ou no nível raiz."""
    encontrados = []
    for node in tinycss2.parse_stylesheet(
        conteudo, skip_comments=True, skip_whitespace=True
    ):
        if media is None and node.type == "qualified-rule":
            blocos = [node]
        elif node.type == "at-rule" and node.at_keyword == "media":
            consulta = tinycss2.serialize(node.prelude).strip()
            if consulta != media:
                continue
            blocos = tinycss2.parse_rule_list(
                node.content, skip_comments=True, skip_whitespace=True
            )
        else:
            continue
        for regra in blocos:
            if regra.type != "qualified-rule":
                continue
            if tinycss2.serialize(regra.prelude).strip() != seletor:
                continue
            declaracoes = {}
            for decl in tinycss2.parse_declaration_list(
                regra.content, skip_comments=True, skip_whitespace=True
            ):
                if decl.type == "declaration":
                    declaracoes[decl.lower_name] = tinycss2.serialize(
                        decl.value
                    ).strip()
            encontrados.append(declaracoes)
    return encontrados


def test_camadas_globais_nao_impedem_rolagem_da_equipe():
    sistema = (CSS / "sistema-ui.css").read_text(encoding="utf-8")
    assert "body.app-shell .inventario-nds-equipe-lista {" not in sistema
    assert "scrollbar-gutter: stable" not in sistema
    # A densidade dos cards não pode sobrescrever os 224px móveis.
    assert "@media (min-width: 1200px)" in sistema
    assert "@media (min-width: 1200px) and (max-width: 1450px)" in sistema
    assert "grid-template-columns: 66px minmax(0,1fr)" not in sistema
    assert "body.app-shell .inventario-nds-treinador-foto { width: 66px" not in sistema


def test_carrossel_equipe_movel_e_rolavel_e_cards_nao_encolhem():
    visual = (CSS / "visual-inventario-10c5.css").read_text(encoding="utf-8")
    equipe = _declaracoes(
        visual, ".inventario-nds-equipe-lista", "(max-width: 799px)"
    )
    assert equipe
    assert equipe[0]["display"] == "flex"
    assert equipe[0]["flex-direction"] == "row"
    assert equipe[0]["overflow-x"] == "auto"
    assert equipe[0]["scroll-snap-type"] == "x proximity"
    cards = _declaracoes(
        visual, ".inventario-nds-treinador-pokemon", "(max-width: 799px)"
    )
    assert cards
    assert cards[0]["flex"] == "0 0 224px"
    assert cards[0]["min-width"] == "224px"


def test_abas_selecionadas_sao_trazidas_para_a_area_visivel():
    script = (ROOT / "static/js/inventario.js").read_text(encoding="utf-8")
    assert "function revealSelectedBag(tab)" in script
    assert "tabStrip.scrollWidth <= tabStrip.clientWidth" in script
    assert "tabStrip.scrollLeft +=" in script
    assert "revealSelectedBag(selectedTab)" in script
    assert script.index("revealSelectedBag(selectedTab)") < script.index(
        "if (filter) filter.value = ''"
    )
    # As teclas esquerda/direita seguem selecionando a categoria.
    assert "ArrowLeft" in script and "ArrowRight" in script
    assert "selectBag(next.dataset.abaBotao)" in script


def test_tela_mobile_mantem_viewport_e_assets_sem_cache_antigo():
    base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    pagina = (ROOT / "templates/jogador/inventario.html").read_text(
        encoding="utf-8"
    )
    assert 'name="viewport" content="width=device-width, initial-scale=1"' in base
    assert "filename='css/sistema-ui.css', v='ui2-20261121-inv-10f2'" in base
    assert "filename='js/inventario.js', v=versao_inventario ~ '-mobile-10f2'" in pagina
    assert "visual-inventario-10c5.css" in pagina


def test_css_de_inventario_e_sistema_continua_valido():
    for nome in ("sistema-ui.css", "visual-inventario-10c5.css", "inventario.css"):
        regras = tinycss2.parse_stylesheet(
            (CSS / nome).read_text(encoding="utf-8")
        )
        assert not [regra for regra in regras if regra.type == "error"], nome
