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

CAMINHO_MAPA = Path(__file__).resolve().parent.parent / "data" / "mapa_ankar_pontos.json"


@lru_cache(maxsize=1)
def carregar_mapa_ankar() -> dict:
    """Marcadores curados manualmente sobre a imagem do mapa, sem acessar o banco."""
    with CAMINHO_MAPA.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def ponto_no_mapa(slug: str) -> dict | None:
    return next((p for p in carregar_mapa_ankar()["pontos"] if p["id"] == slug), None)


def encontro_por_indices(local: dict, zona: int, tabela: int, indice: int) -> dict | None:
    """Encontro exato que já consta do JSON do atlas (não aceita nome arbitrário)."""
    try:
        if min(zona, tabela, indice) < 0:
            return None
        encontro = local["zonas"][zona]["tabelas"][tabela]["encontros"][indice]
    except (IndexError, KeyError, TypeError):
        return None
    if encontro.get("marcador") or not encontro.get("pokemon"):
        return None
    if str(encontro["pokemon"]).strip().casefold() in {"x", "random"}:
        return None
    return encontro


def formas_presentes_no_atlas(local: dict) -> dict[str, dict[str, str]]:
    """Relaciona espécies do local às artes e IDs do catálogo vivo em uma consulta.

    A escolha do primeiro ID em nome duplicado segue o comportamento atual de
    buscar_forma (ordenado por ID). Não gera arte artificial, nem faz imports.
    """
    from sqlalchemy import select
    from app.extensions import db
    from app.models.db import FormaPokemon

    nomes = {
        str(encontro.get("pokemon", "")).strip().casefold()
        for zona in local.get("zonas", [])
        for tabela in zona.get("tabelas", [])
        for encontro in tabela.get("encontros", [])
        if encontro.get("pokemon")
        and not encontro.get("marcador")
        and str(encontro["pokemon"]).strip().casefold() not in {"x", "random"}
    }
    if not nomes:
        return {}
    formas = db.session.execute(
        select(FormaPokemon).where(FormaPokemon.ativo.is_(True)).order_by(FormaPokemon.id)
    ).scalars()
    resultado: dict[str, dict[str, str]] = {}
    for forma in formas:
        chave = forma.nome.casefold()
        if chave in nomes and chave not in resultado:
            resultado[chave] = {
                "id": str(forma.id),
                "imagem": forma.imagem_url or forma.imagem_shiny_url or "",
                "nome": forma.nome,
            }
    return resultado


def paragrafos_da_descricao(descricao: str | None) -> list[str]:
    """Agrupa frases originais em parágrafos curtos sem resumir a lore."""
    import re
    original = str(descricao or "").strip()
    if not original or original == "-":
        return []
    resultado = []
    for paragrafo in re.split(r"\n\s*\n|\n", original):
        frases = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ])", paragrafo.strip())
        grupo = []
        for frase in frases:
            grupo.append(frase)
            if len(' '.join(grupo)) >= 260:
                resultado.append(' '.join(grupo))
                grupo = []
        if grupo:
            resultado.append(' '.join(grupo))
    return [p for p in resultado if p]
