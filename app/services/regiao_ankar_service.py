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


def formas_presentes_no_atlas(local: dict) -> dict[str, dict]:
    """Lê o catálogo vivo e associa por código/forma explícita, sem inventar variantes."""
    from sqlalchemy import select
    from app.extensions import db
    from app.models.db import FormaPokemon
    from app.services.ankar_formas_service import indices_formas_locais, chave_nome

    nomes = {
        str(encontro.get("pokemon", "")).strip()
        for zona in local.get("zonas", [])
        for tabela in zona.get("tabelas", [])
        for encontro in tabela.get("encontros", [])
        if encontro.get("pokemon") and not encontro.get("marcador")
        and chave_nome(encontro["pokemon"]) not in {"x", "random"}
    }
    if not nomes:
        return {}
    formas = db.session.execute(
        select(FormaPokemon).where(FormaPokemon.ativo.is_(True)).order_by(FormaPokemon.id)
    ).scalars()
    return indices_formas_locais(nomes, formas)


def catalogo_com_busca_pokemon(catalogo: dict) -> dict:
    """Enriquece a lista visual com nomes das formas e locais de encontro, sem DB."""
    from app.services.ankar_formas_service import apelidos_pesquisa
    locais = []
    for local in catalogo.get('locais', []):
        especies = {}
        for zona in local.get('zonas', []):
            for tabela in zona.get('tabelas', []):
                for encontro in tabela.get('encontros', []):
                    nome = str(encontro.get('pokemon') or '').strip()
                    if not nome or encontro.get('marcador') or nome.casefold() in {'x', 'random'}:
                        continue
                    especie = especies.setdefault(nome, {'nome': nome, 'ambientes': set(), 'aliases': apelidos_pesquisa(nome)})
                    especie['ambientes'].add(f"{zona['nome']} · {tabela['terreno']}")
        busca = [dict(nome=especie['nome'], ambientes=sorted(especie['ambientes']),
                      aliases=especie['aliases']) for especie in especies.values()]
        busca.sort(key=lambda item: item['nome'].casefold())
        locais.append(dict(local, pokemon_busca=busca,
                           pokemon_busca_termos=' '.join(a for e in busca for a in e['aliases'])))
    return dict(catalogo, locais=locais)


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
