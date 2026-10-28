"""Leitura do catálogo visual pré-gerado de Ankar; não consulta ou altera o DB."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

CAMINHO_CATALOGO = Path(__file__).resolve().parent.parent / "data" / "catalogo_ankar_visual.json"


@lru_cache(maxsize=1)
def carregar_catalogo_ankar() -> dict:
    """Dados são publicados manualmente como JSON versionado; reinicie para atualizar."""
    with CAMINHO_CATALOGO.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def localizar_ankar(slug: str) -> dict | None:
    for local in carregar_catalogo_ankar().get("locais", []):
        if local["id"] == slug:
            return local
    return None
