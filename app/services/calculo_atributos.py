from __future__ import annotations

import math
from typing import Any

ATRIBUTOS_COMBATE = (
    "ataque",
    "defesa",
    "ataque_especial",
    "defesa_especial",
    "velocidade",
)


def _inteiro(valor: Any, padrao: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _faixa(valor_base: int, faixas: list[dict[str, Any]]) -> dict[str, Any]:
    for faixa in faixas:
        minimo = _inteiro(faixa.get("minimo"))
        maximo = _inteiro(faixa.get("maximo"), 9999)
        if minimo <= valor_base <= maximo:
            return faixa
    return {"par": 0, "impar": 0}


def calcular_progressao(
    valor_base: int,
    nivel: int,
    faixas: list[dict[str, Any]],
) -> int:
    """Recalcula um atributo desde o nível 1 usando a faixa do valor base."""
    nivel = max(1, nivel)
    faixa = _faixa(valor_base, faixas)
    bonus_par = _inteiro(faixa.get("par"))
    bonus_impar = _inteiro(faixa.get("impar"))

    total = valor_base
    for nivel_atual in range(2, nivel + 1):
        total += bonus_par if nivel_atual % 2 == 0 else bonus_impar
    return total


def aplicar_aumento(valor: int, percentual: float) -> int:
    if percentual <= 0:
        return valor
    return math.ceil(valor * (1 + percentual))


def aplicar_diminuicao(valor: int, percentual: float) -> int:
    if percentual <= 0:
        return valor
    return math.floor(valor * (1 - percentual))


def _natureza_por_nome(regras: dict[str, Any], nome: str) -> dict[str, Any]:
    return next(
        (
            natureza
            for natureza in regras.get("naturezas", [])
            if str(natureza.get("nome", "")).casefold() == nome.casefold()
        ),
        {"nome": nome, "aumenta": None, "diminui": None},
    )


def calcular_atributos_pokemon(
    *,
    pokemon: dict[str, Any],
    especie: dict[str, Any],
    regras: dict[str, Any],
    nivel_jogador: int = 1,
    estilo_combate: str = "",
    golpes_catalogo: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calcula a ficha do Pokémon usando sempre o nível atual do jogador."""
    nivel = max(1, _inteiro(nivel_jogador, 1))
    shiny = bool(pokemon.get("shiny", False))
    bonus_manual = pokemon.get("bonus", {}) if isinstance(pokemon.get("bonus"), dict) else {}
    bonus_shiny = regras.get("bonus_shiny", {})
    base_catalogo = especie.get("atributos_base", {})

    bases: dict[str, int] = {}
    for atributo in ("pv", *ATRIBUTOS_COMBATE):
        bases[atributo] = _inteiro(base_catalogo.get(atributo)) + (
            _inteiro(bonus_shiny.get(atributo)) if shiny else 0
        )

    valores: dict[str, int] = {
        "pv": calcular_progressao(
            bases["pv"], nivel, regras.get("progressao_pv", [])
        )
    }
    for atributo in ATRIBUTOS_COMBATE:
        valores[atributo] = calcular_progressao(
            bases[atributo], nivel, regras.get("progressao_atributos", [])
        )

    natureza = _natureza_por_nome(regras, str(pokemon.get("natureza", "")))
    aumenta = natureza.get("aumenta")
    diminui = natureza.get("diminui")
    if aumenta in valores:
        valores[aumenta] = aplicar_aumento(valores[aumenta], 0.10)
    if diminui in valores:
        valores[diminui] = aplicar_diminuicao(valores[diminui], 0.10)

    modificadores_estilo = regras.get("estilos_combate", {}).get(estilo_combate, {})
    for atributo, percentual in modificadores_estilo.items():
        if atributo in valores:
            valores[atributo] = aplicar_aumento(valores[atributo], float(percentual))

    status = str(pokemon.get("status", "Nenhum"))
    if status == "Dormindo":
        valores["velocidade"] = 0
    elif status == "Paralisado":
        valores["velocidade"] = aplicar_diminuicao(valores["velocidade"], 0.50)
    if status == "Queimando":
        valores["ataque"] = aplicar_diminuicao(valores["ataque"], 0.50)

    for atributo in ("pv", *ATRIBUTOS_COMBATE):
        valores[atributo] = max(
            0, valores[atributo] + _inteiro(bonus_manual.get(atributo))
        )

    golpes_por_id = golpes_catalogo or {}
    golpes_detalhados: list[dict[str, Any]] = []
    for registro in pokemon.get("golpes", []):
        if not isinstance(registro, dict):
            continue
        golpe = golpes_por_id.get(str(registro.get("golpe_id", "")))
        if golpe:
            golpes_detalhados.append(golpe)

    velocidade = valores["velocidade"]
    dados_defesa = 0 if velocidade <= 0 else math.ceil(velocidade / 10)

    return {
        "nivel": nivel,
        "bases": bases,
        "totais": valores,
        "dados_defesa": dados_defesa,
        "dados_defesa_texto": f"{dados_defesa}d6",
        "golpes": golpes_detalhados,
        "natureza": natureza,
        "status": status,
    }
