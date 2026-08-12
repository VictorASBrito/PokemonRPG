from __future__ import annotations

import click
from flask import Blueprint
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import Item, PersonagemItem, Pokemon

inventario_cli = Blueprint("inventario_cli", __name__)


@inventario_cli.cli.group("inventario")
def inventario_group() -> None:
    """Diagnósticos do catálogo de itens e dos inventários."""


@inventario_group.command("verificar")
def verificar() -> None:
    problemas: list[str] = []
    registros = list(db.session.execute(select(PersonagemItem)).scalars())
    for registro in registros:
        if registro.quantidade <= 0:
            problemas.append(
                f"Inventário {registro.id}: quantidade inválida ({registro.quantidade})."
            )
        if db.session.get(Item, registro.item_id) is None:
            problemas.append(f"Inventário {registro.id}: item inexistente.")

    equipados = list(
        db.session.execute(
            select(Pokemon).where(Pokemon.item_equipado_id.is_not(None))
        ).scalars()
    )
    for pokemon in equipados:
        item = db.session.get(Item, pokemon.item_equipado_id)
        if item is None:
            problemas.append(f"Pokémon {pokemon.id}: item equipado inexistente.")
        elif not item.equipavel:
            problemas.append(
                f"Pokémon {pokemon.id}: {item.nome} não está marcado como equipável."
            )

    itens_negativos = int(
        db.session.scalar(select(func.count(Item.id)).where(Item.preco < 0)) or 0
    )
    if itens_negativos:
        problemas.append(f"{itens_negativos} item(ns) possui(em) preço negativo.")

    click.echo(
        f"Inventário: {len(registros)} registro(s), "
        f"{sum(item.quantidade for item in registros)} unidade(s), "
        f"{len(equipados)} item(ns) equipado(s)."
    )
    if problemas:
        for problema in problemas[:50]:
            click.echo(f"- {problema}", err=True)
        if len(problemas) > 50:
            click.echo(f"- ... e mais {len(problemas) - 50} problema(s).", err=True)
        raise click.ClickException("Foram encontradas inconsistências nos inventários.")
    click.echo("Itens, inventários e equipamentos estão consistentes no PostgreSQL.")
