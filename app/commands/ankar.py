"""Comandos administrativos de geografia e encontros da campanha Ankar."""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

import click
from flask import Blueprint

from app.services.auditoria_ankar_service import auditar_planilhas

ankar_cli = Blueprint("ankar_cli", __name__)


@ankar_cli.cli.group("ankar")
def ankar_group() -> None:
    """Geografia e tabelas de encontro de Ankar (diagnosticos)."""


@ankar_group.command("auditar-planilhas")
@click.option("--rotas", type=click.Path(exists=True, dir_okay=False,
              readable=True, path_type=Path), required=True,
              help="Planilha XLSX de rotas da regiao de Ankar.")
@click.option("--cidades", type=click.Path(exists=True, dir_okay=False,
              readable=True, path_type=Path), required=True,
              help="Planilha XLSX de cidades e pontos de interesse.")
@click.option("--todos", is_flag=True,
              help="Exibe todos os achados (padrao: primeiros 50).")
@click.option("--formato", type=click.Choice(["texto", "json"]), default="texto",
              show_default=True, help="Formato do relatorio enviado ao terminal.")
def auditar_planilhas_comando(rotas: Path, cidades: Path, todos: bool,
                             formato: str) -> None:
    """Audita planilhas sem alterar XLSX, PostgreSQL ou outros arquivos."""
    try:
        resultado = auditar_planilhas(rotas, cidades)
    except (OSError, ValueError, KeyError, BadZipFile, InvalidFileException) as exc:
        raise click.ClickException(f"Nao foi possivel ler as planilhas: {exc}") from exc
    if formato == "json":
        click.echo(json.dumps(resultado.como_dict(), ensure_ascii=False, indent=2))
    else:
        click.echo(resultado.texto(limite=None if todos else 50))
    if resultado.erros:
        raise click.exceptions.Exit(1)
