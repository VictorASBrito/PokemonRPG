from __future__ import annotations

from pathlib import Path

import click
from flask import Blueprint, current_app

from app.services.importacao import FontesImportacao, ImportacaoService


dados_cli = Blueprint("dados_cli", __name__)


def _fontes() -> FontesImportacao:
    return FontesImportacao(Path(current_app.config["DATA_DIR"]))


def _exibir_contagens(contagens: dict) -> None:
    rotulos = {
        "usuarios": "Usuários",
        "campanhas": "Campanhas",
        "jogadores": "Jogadores",
        "pokemon_jogadores": "Pokémon dos jogadores",
        "formas_pokemon": "Formas Pokémon",
        "golpes": "Golpes",
        "tipos": "Tipos",
        "categorias_golpe": "Categorias de golpe",
        "naturezas": "Naturezas",
        "status": "Status",
        "atributos": "Atributos",
    }
    for chave, rotulo in rotulos.items():
        click.echo(f"{rotulo}: {contagens.get(chave, 0)}")


@dados_cli.cli.group("dados")
def dados_group() -> None:
    """Analisa, importa e valida os arquivos JSON legados."""


@dados_group.command("analisar")
def analisar() -> None:
    """Lê os arquivos sem acessar ou modificar o banco."""
    resultado = _fontes().analisar()
    click.echo("Dados encontrados nos arquivos JSON:")
    _exibir_contagens(resultado)
    for aviso in resultado.get("avisos", []):
        click.echo(f"AVISO: {aviso}", err=True)


@dados_group.command("importar")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Executa todas as validações e desfaz a transação ao final.",
)
def importar(dry_run: bool) -> None:
    """Importa os catálogos e a campanha para o PostgreSQL."""
    fontes = _fontes()
    service = ImportacaoService(
        fontes,
        raiz_projeto=Path(current_app.root_path).parent,
    )
    resumo = service.importar(dry_run=dry_run)

    click.echo("Simulação concluída." if dry_run else "Importação concluída.")
    click.echo(f"Registros criados: {sum(resumo.criados.values())}")
    click.echo(f"Registros atualizados: {sum(resumo.atualizados.values())}")
    click.echo(f"Registros removidos: {sum(resumo.removidos.values())}")
    if resumo.relatorio:
        click.echo(f"Relatório: {resumo.relatorio}")

    for aviso in resumo.avisos:
        click.echo(f"AVISO: {aviso}", err=True)
    for erro in resumo.erros:
        click.echo(f"ERRO: {erro}", err=True)

    if resumo.erros:
        raise click.ClickException("A importação não foi concluída.")
    if not dry_run and resumo.validacao and not resumo.validacao.get("sucesso"):
        click.echo("A carga terminou, mas a validação encontrou divergências.", err=True)
        for item in resumo.validacao.get("divergencias", []):
            click.echo(f"- {item}", err=True)


@dados_group.command("validar")
def validar() -> None:
    """Compara as quantidades dos JSON com as quantidades do banco."""
    service = ImportacaoService(
        _fontes(),
        raiz_projeto=Path(current_app.root_path).parent,
    )
    resultado = service.validar()
    for chave, dados in resultado["comparacoes"].items():
        situacao = "OK" if dados["ok"] else "DIVERGENTE"
        click.echo(
            f"{chave}: JSON {dados['fonte']} | Banco {dados['banco']} | {situacao}"
        )
    click.echo(f"Relatório: {resultado['relatorio']}")
    if not resultado["sucesso"]:
        raise click.ClickException("A validação encontrou divergências.")
