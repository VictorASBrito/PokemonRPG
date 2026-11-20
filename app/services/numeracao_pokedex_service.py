"""Número nacional para exibição de formas do catálogo legado.

A sequência `ordem_catalogo` enumera 1.064 formas, não 898 espécies.
A fonte original agrupa variantes sob o mesmo nome de espécie, permitindo
recuperar os números nacionais sem regravar o PostgreSQL.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.importacao.utils import nome_especie

if TYPE_CHECKING:
    from app.models.db import FormaPokemon


@lru_cache(maxsize=1)
def _numeros_da_fonte() -> tuple[dict[str, int], dict[str, int]]:
    """Retorna mapas por código da forma e nome exato da espécie.

    Não utiliza `slug` para identificar Nidoran♀/Nidoran♂, pois
    a normalização legada une indevidamente esses nomes.
    """
    arquivo = Path(__file__).resolve().parents[2] / "data" / "catalogo" / "pokemons.json"
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, {}

    por_forma: dict[str, int] = {}
    por_especie: dict[str, int] = {}
    for registro in dados.get("pokemons", []):
        nome = str(registro.get("nome") or "").strip()
        codigo = str(registro.get("id") or "").strip()
        if not nome or not codigo:
            continue
        especie = nome_especie(nome)
        if especie not in por_especie:
            por_especie[especie] = len(por_especie) + 1
        por_forma[codigo] = por_especie[especie]
    return por_forma, por_especie


def numero_nacional_forma(forma: FormaPokemon) -> int | None:
    """Resolve o número exibido sem alterar espécies nem Pokémon existentes.

    Formas da fonte oficial prevalecem sobre associações legadas incorretas
    (inclusive Nidoran♂). Formas criadas pelo mestre respeitam o número da
    espécie personalizada; variantes novas de espécies oficiais usam o mesmo
    número de sua espécie.
    """
    por_forma, por_especie = _numeros_da_fonte()
    if forma.codigo in por_forma:
        return por_forma[forma.codigo]

    if forma.especie.personalizada:
        return forma.especie.numero

    numero_nome = por_especie.get(nome_especie(forma.nome))
    if numero_nome is not None:
        return numero_nome
    if forma.especie.numero is not None:
        return forma.especie.numero
    return por_especie.get(forma.especie.nome)
