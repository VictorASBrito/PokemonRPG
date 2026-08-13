from __future__ import annotations

import click
from flask import Blueprint
from sqlalchemy import select

from app.extensions import db
from app.models.db import FormaPokemon, Item, Personagem
from app.services.upload_service import (
    caminho_imagem_local,
    contar_referencias_imagem,
    listar_arquivos_upload,
    url_de_arquivo_local,
)

midia_cli = Blueprint("midia_cli", __name__)


@midia_cli.cli.group("midia")
def midia_group() -> None:
    """Diagnósticos e manutenção dos uploads de imagens."""


def _urls_catalogo() -> set[str]:
    urls: set[str] = set()
    for item in db.session.execute(select(Item.imagem_url)).scalars():
        if item:
            urls.add(item)
    for foto in db.session.execute(select(Personagem.foto_url)).scalars():
        if foto:
            urls.add(foto)
    for normal, shiny in db.session.execute(
        select(FormaPokemon.imagem_url, FormaPokemon.imagem_shiny_url)
    ):
        if normal:
            urls.add(normal)
        if shiny:
            urls.add(shiny)
    return urls


@midia_group.command("verificar")
def verificar() -> None:
    """Confere referências locais, arquivos ausentes e uploads órfãos."""
    urls = _urls_catalogo()
    urls_locais = {url for url in urls if caminho_imagem_local(url) is not None}
    ausentes = sorted(
        url
        for url in urls_locais
        if not (caminho_imagem_local(url) and caminho_imagem_local(url).is_file())
    )

    arquivos = listar_arquivos_upload()
    orfaos: list[str] = []
    for arquivo in arquivos:
        url = url_de_arquivo_local(arquivo)
        if url and contar_referencias_imagem(url) == 0:
            orfaos.append(url)

    click.echo(
        f"Mídia: {len(urls_locais)} referência(s) local(is), "
        f"{len(arquivos)} arquivo(s) enviado(s), {len(orfaos)} órfão(s)."
    )
    if orfaos:
        click.echo("Uploads órfãos podem ser removidos com 'midia limpar-orfaos --aplicar'.")
    if ausentes:
        for url in ausentes[:50]:
            click.echo(f"- Arquivo referenciado não encontrado: {url}", err=True)
        raise click.ClickException("Existem imagens locais referenciadas que não estão no disco.")
    click.echo("Referências de imagens locais estão consistentes.")


@midia_group.command("limpar-orfaos")
@click.option(
    "--aplicar",
    is_flag=True,
    help="Remove os arquivos. Sem esta opção, apenas simula a limpeza.",
)
def limpar_orfaos(aplicar: bool) -> None:
    """Localiza uploads que não são mais utilizados por nenhum registro."""
    orfaos = []
    for arquivo in listar_arquivos_upload():
        url = url_de_arquivo_local(arquivo)
        if url and contar_referencias_imagem(url) == 0:
            orfaos.append((arquivo, url))

    if not orfaos:
        click.echo("Nenhum upload órfão encontrado.")
        return

    for arquivo, url in orfaos:
        click.echo(f"{'REMOVER' if aplicar else 'SIMULAR'}: {url}")
        if aplicar:
            arquivo.unlink(missing_ok=True)
    click.echo(
        f"{len(orfaos)} arquivo(s) {'removido(s)' if aplicar else 'seria(m) removido(s)'}."
    )
