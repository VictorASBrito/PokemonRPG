"""Numeração nacional da Pokédex a partir da fonte original do catálogo.

O arquivo legado contém formas misturadas às espécies; ordem_catalogo
representa a posição da forma, não o número nacional da espécie.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any


def _slug_especie(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-") or "registro"


def _nome_especie(nome_forma: str) -> str:
    return str(nome_forma).split(" (", 1)[0].strip()


def codigo_especie_pokedex(nome_forma: str) -> str:
    """Mantém os códigos legados, separando a exceção Nidoran macho."""
    nome = _nome_especie(nome_forma)
    if nome == "Nidoran♂":
        return "nidoran-m"
    return _slug_especie(nome)


def mapear_numeros_pokedex(registros: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Atribui um número por espécie distinta na ordem da fonte original.

    Formas Mega, regionais e alternativas compartilham o número de sua espécie.
    Não atribui numeração a espécies personalizadas fora da fonte oficial.
    """
    linhas = list(registros)

    def chave(item: tuple[int, Mapping[str, Any]]) -> tuple[int, int]:
        indice, registro = item
        bruto = str(registro.get("ordem_catalogo") or "")
        return (int(bruto) if bruto.isdigit() and int(bruto) > 0 else 10**9, indice)

    numeros: dict[str, int] = {}
    for _, registro in sorted(enumerate(linhas), key=chave):
        nome = str(registro.get("nome") or "").strip()
        if not nome:
            continue
        codigo = codigo_especie_pokedex(nome)
        if codigo not in numeros:
            numeros[codigo] = len(numeros) + 1
    return numeros
