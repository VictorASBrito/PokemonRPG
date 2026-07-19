from __future__ import annotations

import click
from flask import Blueprint, current_app

from app.extensions import db
from app.models.db import Campanha, ConjuntoRegras, Regra, RegraValor
from app.services.personagem_service import preparar_configuracoes_ficha
from sqlalchemy import select


ficha_cli = Blueprint("ficha_cli", __name__)


@ficha_cli.cli.group("ficha")
def ficha_group() -> None:
    """Prepara e verifica a ficha armazenada no PostgreSQL."""


@ficha_group.command("preparar")
@click.option(
    "--forcar",
    is_flag=True,
    help="Sobrescreve as configurações já existentes com a carga inicial legada.",
)
def preparar(forcar: bool) -> None:
    """Copia as opções iniciais da ficha para o conjunto de regras ativo."""
    try:
        resultado = preparar_configuracoes_ficha(
            data_dir=current_app.config["DATA_DIR"],
            campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
            sobrescrever=forcar,
        )
    except ValueError as erro:
        db.session.rollback()
        raise click.ClickException(str(erro)) from erro

    click.echo("Configurações da ficha preparadas no PostgreSQL.")
    click.echo(f"Criadas: {resultado['criadas']}")
    click.echo(f"Atualizadas: {resultado['atualizadas']}")
    click.echo(f"Mantidas: {resultado['ignoradas']}")


@ficha_group.command("verificar")
def verificar() -> None:
    """Confere se todas as configurações necessárias estão no banco."""
    campanha_codigo = str(current_app.config["CAMPANHA_PADRAO"])
    campanha = db.session.execute(
        select(Campanha).where(
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if campanha is None:
        raise click.ClickException(
            f'A campanha "{campanha_codigo}" não foi encontrada.'
        )

    conjunto = db.session.execute(
        select(ConjuntoRegras).where(
            ConjuntoRegras.campanha_id == campanha.id,
            ConjuntoRegras.em_uso.is_(True),
            ConjuntoRegras.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if conjunto is None:
        raise click.ClickException("Nenhum conjunto de regras ativo foi encontrado.")

    obrigatorias = {
        "pv-por-ponto-saude",
        "nivel-minimo",
        "nivel-maximo",
        "nivel-inicial",
        "limite-numeros-shiny",
        "tamanho-equipe",
        "atributos-personagem-config",
        "origens-personagem",
        "classes-personagem",
        "estilos-combate-personagem",
    }
    encontradas = set(
        db.session.execute(
            select(Regra.codigo)
            .join(RegraValor, RegraValor.regra_id == Regra.id)
            .where(
                RegraValor.conjunto_regras_id == conjunto.id,
                Regra.ativo.is_(True),
            )
        ).scalars()
    )
    ausentes = sorted(obrigatorias - encontradas)
    click.echo(f"Campanha: {campanha.nome}")
    click.echo(f"Conjunto de regras: {conjunto.nome} ({conjunto.versao})")
    click.echo(f"Configurações encontradas: {len(obrigatorias) - len(ausentes)}/{len(obrigatorias)}")
    if ausentes:
        for codigo in ausentes:
            click.echo(f"- Ausente: {codigo}")
        raise click.ClickException(
            "Execute 'flask --app app.py ficha preparar' antes de abrir a ficha."
        )
    click.echo("A ficha está pronta para usar exclusivamente o PostgreSQL.")
