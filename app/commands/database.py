from __future__ import annotations

import click
from flask import Blueprint
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


banco_cli = Blueprint("banco_cli", __name__)


@banco_cli.cli.group("banco")
def banco_group() -> None:
    """Comandos auxiliares para validar o PostgreSQL."""


@banco_group.command("verificar")
def verificar_banco() -> None:
    """Valida a conexão, o usuário e as extensões necessárias."""
    try:
        conexao = db.session.execute(
            text(
                """
                SELECT
                    current_user AS usuario,
                    current_database() AS banco,
                    current_setting('TimeZone') AS timezone,
                    version() AS versao
                """
            )
        ).mappings().one()

        extensoes = set(
            db.session.execute(
                text(
                    """
                    SELECT extname
                    FROM pg_extension
                    WHERE extname IN ('pg_trgm', 'unaccent')
                    ORDER BY extname
                    """
                )
            ).scalars()
        )
    except SQLAlchemyError as exc:
        raise click.ClickException(f"Não foi possível acessar o banco: {exc}") from exc

    click.echo("Conexão com o PostgreSQL realizada com sucesso.")
    click.echo(f"Banco: {conexao['banco']}")
    click.echo(f"Usuário: {conexao['usuario']}")
    click.echo(f"Timezone: {conexao['timezone']}")
    click.echo(f"Versão: {conexao['versao']}")

    ausentes = {"pg_trgm", "unaccent"} - extensoes
    if ausentes:
        click.echo(
            "Extensões ausentes: " + ", ".join(sorted(ausentes)),
            err=True,
        )
        raise click.ClickException(
            "Instale as extensões antes de aplicar a migration inicial."
        )

    click.echo("Extensões: pg_trgm e unaccent instaladas.")


@banco_group.command("tabelas")
def listar_tabelas() -> None:
    """Lista as tabelas existentes no schema public."""
    try:
        tabelas = inspect(db.engine).get_table_names(schema="public")
    except SQLAlchemyError as exc:
        raise click.ClickException(f"Não foi possível consultar as tabelas: {exc}") from exc

    if not tabelas:
        click.echo("Nenhuma tabela da aplicação foi encontrada.")
        return

    click.echo(f"{len(tabelas)} tabela(s) encontrada(s):")
    for tabela in sorted(tabelas):
        click.echo(f"- {tabela}")
