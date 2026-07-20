from __future__ import annotations

import click
from flask import Blueprint
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    Atributo,
    CategoriaGolpe,
    EspeciePokemon,
    FormaPokemon,
    FormaPokemonAtributo,
    FormaPokemonGolpe,
    FormaPokemonTipo,
    Golpe,
    TipoPokemon,
)
from app.services.golpe_admin_service import METODOS_APRENDIZADO, TIPOS_EFEITO, efeitos_para_editor

catalogo_cli = Blueprint("catalogo_cli", __name__)


@catalogo_cli.cli.group("catalogo")
def catalogo_group() -> None:
    """Diagnósticos do catálogo administrável."""


@catalogo_group.command("verificar")
def verificar() -> None:
    """Confere formas sem espécie, tipos ou atributos base."""
    atributos_esperados = int(
        db.session.scalar(
            select(func.count(Atributo.id)).where(
                Atributo.ativo.is_(True),
                Atributo.escopo.in_(["pokemon", "ambos"]),
            )
        )
        or 0
    )
    formas = list(
        db.session.execute(
            select(FormaPokemon).where(FormaPokemon.ativo.is_(True))
        ).scalars()
    )
    problemas: list[str] = []
    for forma in formas:
        especie = db.session.get(EspeciePokemon, forma.especie_id)
        if especie is None:
            problemas.append(f"{forma.nome}: espécie inexistente.")
        elif not especie.ativo:
            problemas.append(f"{forma.nome}: forma ativa vinculada a espécie inativa.")

        quantidade_tipos = int(
            db.session.scalar(
                select(func.count(FormaPokemonTipo.id)).where(
                    FormaPokemonTipo.forma_pokemon_id == forma.id
                )
            )
            or 0
        )
        if quantidade_tipos not in {1, 2}:
            problemas.append(
                f"{forma.nome}: possui {quantidade_tipos} tipo(s), esperado 1 ou 2."
            )

        quantidade_atributos = int(
            db.session.scalar(
                select(func.count(FormaPokemonAtributo.id)).where(
                    FormaPokemonAtributo.forma_pokemon_id == forma.id
                )
            )
            or 0
        )
        if quantidade_atributos != atributos_esperados:
            problemas.append(
                f"{forma.nome}: possui {quantidade_atributos}/{atributos_esperados} "
                "atributos base ativos."
            )

    especies_total = int(db.session.scalar(select(func.count(EspeciePokemon.id))) or 0)
    formas_total = int(db.session.scalar(select(func.count(FormaPokemon.id))) or 0)
    click.echo(
        f"Catálogo: {especies_total} espécie(s), {formas_total} forma(s), "
        f"{atributos_esperados} atributo(s) Pokémon ativo(s)."
    )
    if problemas:
        for problema in problemas[:50]:
            click.echo(f"- {problema}", err=True)
        if len(problemas) > 50:
            click.echo(f"- ... e mais {len(problemas) - 50} problema(s).", err=True)
        raise click.ClickException("Foram encontradas inconsistências no catálogo.")
    click.echo("Catálogo de espécies e formas está consistente no PostgreSQL.")

    problemas_golpes: list[str] = []
    tipos_efeito_validos = {item[0] for item in TIPOS_EFEITO}
    metodos_validos = {item[0] for item in METODOS_APRENDIZADO}
    golpes = list(db.session.execute(select(Golpe)).scalars())
    for golpe in golpes:
        categoria = db.session.get(CategoriaGolpe, golpe.categoria_id)
        if categoria is None:
            problemas_golpes.append(f"{golpe.nome}: categoria inexistente.")
        elif golpe.ativo and not categoria.ativo:
            problemas_golpes.append(f"{golpe.nome}: golpe ativo vinculado a categoria inativa.")
        if golpe.tipo_id:
            tipo = db.session.get(TipoPokemon, golpe.tipo_id)
            if tipo is None:
                problemas_golpes.append(f"{golpe.nome}: tipo inexistente.")
            elif golpe.ativo and not tipo.ativo:
                problemas_golpes.append(f"{golpe.nome}: golpe ativo vinculado a tipo inativo.")
        efeitos = efeitos_para_editor(golpe.efeitos)
        if len(efeitos) > 20:
            problemas_golpes.append(f"{golpe.nome}: possui mais de 20 efeitos.")
        for indice, efeito in enumerate(efeitos, start=1):
            tipo_efeito = efeito.get("tipo", "texto")
            if tipo_efeito not in tipos_efeito_validos:
                problemas_golpes.append(
                    f"{golpe.nome}: efeito {indice} possui tipo desconhecido ({tipo_efeito})."
                )

    vinculos = list(db.session.execute(select(FormaPokemonGolpe)).scalars())
    for vinculo in vinculos:
        if vinculo.metodo not in metodos_validos:
            problemas_golpes.append(
                f"Vínculo {vinculo.id}: método de aprendizado inválido ({vinculo.metodo})."
            )
        if vinculo.nivel_requerido is not None and vinculo.nivel_requerido < 1:
            problemas_golpes.append(f"Vínculo {vinculo.id}: nível requerido inválido.")

    click.echo(
        f"Golpes: {len(golpes)} registro(s), {len(vinculos)} vínculo(s) com formas Pokémon."
    )
    if problemas_golpes:
        for problema in problemas_golpes[:50]:
            click.echo(f"- {problema}", err=True)
        if len(problemas_golpes) > 50:
            click.echo(
                f"- ... e mais {len(problemas_golpes) - 50} problema(s).",
                err=True,
            )
        raise click.ClickException("Foram encontradas inconsistências no catálogo de golpes.")
    click.echo("Catálogo de golpes está consistente no PostgreSQL.")
