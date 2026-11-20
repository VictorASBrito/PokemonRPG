"""Faixas do Atlas: sorteio sem adulterar fonte ou confundir chances de captura."""
from __future__ import annotations

import random

import pytest

from app.services.gerador_npcs_ankar import rolagens_validas, sortear_especies


def _tabela():
    return {"encontros": [
        {"pokemon": "Bulbasaur", "d100": "1-60", "faixa_valida": True},
        {"pokemon": "Charmander", "d100": "60-100", "faixa_valida": True},
        {"pokemon": "Zubat", "d100": "1-1", "faixa_valida": True, "faixa_reconstituida": True},
        {"pokemon": "x", "d100": "", "marcador": True},
    ]}


def test_d100_sinaliza_sobreposicao_e_exclui_reconstrucao():
    slots, avisos = rolagens_validas(_tabela(), {"Bulbasaur", "Charmander"})
    assert slots[0] == "Bulbasaur"
    assert slots[59] is None  # Face 60 sobreposta entre duas espécies; não é corrigida.
    assert slots[99] == "Charmander"
    assert avisos["rolagens_ambiguas"] == 1
    assert avisos["reconstruidos"] == 1
    assert "Zubat" not in slots


def test_gerador_respeita_especies_e_quantidade():
    escolhas, avisos = sortear_especies(
        _tabela(), 2, nomes_habilitados={"Bulbasaur", "Charmander"},
        permitir_repetidos=False, rng=random.Random(81)
    )
    assert len(escolhas) == 2
    assert {e["pokemon"] for e in escolhas} == {"Bulbasaur", "Charmander"}
    assert all(1 <= e["d100"] <= 100 for e in escolhas)
    assert avisos["rolagens_ambiguas"] == 1


def test_gerador_impede_quantidade_invalida_e_tabela_nao_compatível():
    with pytest.raises(ValueError, match="1 a 6"):
        sortear_especies(_tabela(), 7, nomes_habilitados={"Bulbasaur"},
                         permitir_repetidos=True)
    with pytest.raises(ValueError, match="somente 1"):
        sortear_especies(_tabela(), 2, nomes_habilitados={"Bulbasaur"},
                         permitir_repetidos=False)
    with pytest.raises(ValueError, match="não possui encontros"):
        sortear_especies(_tabela(), 1, nomes_habilitados=set(),
                         permitir_repetidos=True)
