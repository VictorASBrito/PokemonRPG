"""Ordenação estável da Pokédex para listas de espécies e formas.

A carga da Ficha Editável v2.5 guarda a sequência original de 1 a 1064
em FormaPokemon.configuracoes["ordem_catalogo"], mas deixou os números
de EspeciePokemon vazios. A ordem original conserva formas alternativas
e Megas junto à espécie. Espécies criadas depois aparecem no final,
com número de catálogo quando presente e nome como desempate.

Este helper é somente de leitura; nunca renumera Pokémon de jogadores.
"""
from __future__ import annotations

from sqlalchemy import case, func, select

from app.models.db import EspeciePokemon, FormaPokemon


def _indice_original():
    return FormaPokemon.configuracoes["ordem_catalogo"].as_integer()


def ordem_formas_pokedex():
    """Expressões SQL; exige JOIN com EspeciePokemon."""
    indice = _indice_original()
    return (
        case((indice.is_not(None), 0), else_=1),
        indice.asc().nullslast(),
        EspeciePokemon.numero.asc().nullslast(),
        func.lower(EspeciePokemon.nome),
        func.lower(FormaPokemon.nome),
        FormaPokemon.id,
    )


def ordem_especies_pokedex():
    """Ordem de primeira ocorrência de espécie, sem multiplicar por formas."""
    primeiro_indice = (
        select(func.min(_indice_original()))
        .where(FormaPokemon.especie_id == EspeciePokemon.id)
        .correlate(EspeciePokemon)
        .scalar_subquery()
    )
    return (
        case((primeiro_indice.is_not(None), 0), else_=1),
        primeiro_indice.asc().nullslast(),
        EspeciePokemon.numero.asc().nullslast(),
        func.lower(EspeciePokemon.nome),
        EspeciePokemon.id,
    )
