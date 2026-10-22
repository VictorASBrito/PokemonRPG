"""Contrato de layout da equipe (sem depender de um banco de dados)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_cards_normais_e_espacos_vazios_compartilham_altura() -> None:
    css = (RAIZ / "static/css/dashboard.css").read_text(encoding="utf-8")
    assert "Padronização de proporções da grade Pokémon" in css
    assert "grid-auto-rows: clamp(255px, 30dvh, 285px)" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert ".pokemon-dashboard-vazio" in css


def test_retrato_atributos_e_golpes_tem_diretrizes_de_tamanho() -> None:
    css = (RAIZ / "static/css/dashboard.css").read_text(encoding="utf-8")
    assert "grid-template-columns: 112px minmax(0, 1fr)" in css
    assert "grid-template-rows: repeat(2, minmax(34px, 1fr))" in css
    assert "max-width: 44%" in css
    assert "min-width: 0" in css
    assert ".vida-pokemon-dashboard progress" in css


def test_textos_longos_informam_valores_inteiros_por_tooltip() -> None:
    template = (RAIZ / "templates/jogador/dashboard.html").read_text(encoding="utf-8")
    assert 'title="{{ nome_exibicao }}"' in template
    assert 'title="{{ golpe.get(\'nome\') }}"' in template
    assert "data-dashboard-pokemon-collapse" in template


def test_padronizacao_nao_altera_modo_expandido() -> None:
    css = (RAIZ / "static/css/dashboard.css").read_text(encoding="utf-8")
    parte_nova = css.split("Padronização de proporções da grade Pokémon")[-1]
    assert ".grade-pokemons-dashboard:not(.dashboard-pokemon-modo-foco)" in parte_nova
    assert ".dashboard-pokemon-em-foco" not in parte_nova
