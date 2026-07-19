from __future__ import annotations

import click
from flask import Blueprint, current_app
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import Campanha, FormaPokemon, Golpe, Personagem, Pokemon, TipoPokemon
from app.services.pokemon_db_service import carregar_regras_pokemon_db

pokemon_cli = Blueprint("pokemon_cli", __name__)


@pokemon_cli.cli.group("pokemon")
def pokemon_group() -> None:
    """Diagnósticos dos Pokémon, da equipe e da Box no PostgreSQL."""


@pokemon_group.command("verificar")
def verificar() -> None:
    """Confere catálogos, posições, limites da equipe e capacidade da Box."""
    campanha_codigo = str(current_app.config["CAMPANHA_PADRAO"])
    campanha = db.session.execute(
        select(Campanha).where(
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if campanha is None:
        raise click.ClickException(
            f'A campanha "{campanha_codigo}" não foi encontrada no PostgreSQL.'
        )

    regras = carregar_regras_pokemon_db(campanha.id)
    limite_equipe = int(regras.get("limites", {}).get("tamanho_equipe", 6))
    limite_box = int(regras.get("boxes", {}).get("espacos", 100))

    formas = db.session.scalar(
        select(func.count(FormaPokemon.id)).where(FormaPokemon.ativo.is_(True))
    ) or 0
    golpes = db.session.scalar(
        select(func.count(Golpe.id)).where(Golpe.ativo.is_(True))
    ) or 0
    tipos = db.session.scalar(
        select(func.count(TipoPokemon.id)).where(TipoPokemon.ativo.is_(True))
    ) or 0

    personagens = list(
        db.session.execute(
            select(Personagem)
            .where(
                Personagem.campanha_id == campanha.id,
                Personagem.ativo.is_(True),
            )
            .options(selectinload(Personagem.pokemons))
            .order_by(func.lower(Personagem.nome))
        ).scalars()
    )

    total = equipe_total = box_total = 0
    problemas: list[str] = []

    for personagem in personagens:
        ativos = [pokemon for pokemon in personagem.pokemons if pokemon.ativo]
        equipe = sorted(
            (pokemon for pokemon in ativos if pokemon.localizacao == "equipe"),
            key=lambda pokemon: pokemon.posicao or 0,
        )
        box = sorted(
            (pokemon for pokemon in ativos if pokemon.localizacao == "box"),
            key=lambda pokemon: pokemon.posicao or 0,
        )
        sem_local = [
            pokemon
            for pokemon in ativos
            if pokemon.localizacao not in {"equipe", "box"}
        ]

        total += len(ativos)
        equipe_total += len(equipe)
        box_total += len(box)

        if len(equipe) > limite_equipe:
            problemas.append(
                f"{personagem.nome}: equipe com {len(equipe)} Pokémon "
                f"(limite {limite_equipe})."
            )
        if len(box) > limite_box:
            problemas.append(
                f"{personagem.nome}: Box com {len(box)} Pokémon "
                f"(limite {limite_box})."
            )
        if sem_local:
            problemas.append(
                f"{personagem.nome}: {len(sem_local)} Pokémon ativo(s) sem "
                "localização válida."
            )

        for nome_local, registros in (("equipe", equipe), ("Box", box)):
            posicoes = [pokemon.posicao for pokemon in registros]
            esperadas = list(range(1, len(registros) + 1))
            if posicoes != esperadas:
                problemas.append(
                    f"{personagem.nome}: posições da {nome_local} não são "
                    f"sequenciais ({posicoes})."
                )

    click.echo(f"Campanha: {campanha.nome} ({campanha.codigo})")
    click.echo(
        f"Catálogo: {formas} forma(s), {golpes} golpe(s), {tipos} tipo(s)."
    )
    click.echo(
        f"Pokémon ativos: {total} | equipe: {equipe_total} | Box: {box_total}"
    )
    click.echo(f"Limites atuais: equipe {limite_equipe} | Box {limite_box}")

    if problemas:
        for problema in problemas:
            click.echo(f"- {problema}", err=True)
        raise click.ClickException(
            "Foram encontradas inconsistências nos Pokémon ou nas posições."
        )

    click.echo("Pokémon, equipes e Boxes estão consistentes no PostgreSQL.")
