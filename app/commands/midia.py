from __future__ import annotations

import click
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from flask import current_app
from flask import Blueprint
from sqlalchemy import select

from app.extensions import db
from app.models.db import FormaPokemon, Item, Personagem
from app.services.imagens_pokemon_hd import (
    imagem_do_catalogo_padrao,
    procurar_artes_hd,
    baixar_arte_hd,
    extensao_arte_hd,
)
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


def _formas_hd_pendentes(codigo: str | None = None):
    consulta = select(FormaPokemon).where(FormaPokemon.ativo.is_(True)).order_by(FormaPokemon.codigo)
    if codigo:
        consulta = consulta.where(FormaPokemon.codigo == codigo)
    return [forma for forma in db.session.execute(consulta).scalars()
            if (imagem_do_catalogo_padrao(forma.imagem_url)
                or imagem_do_catalogo_padrao(forma.imagem_shiny_url))]


@midia_group.command("pokemon-hd-pendentes")
def pokemon_hd_pendentes() -> None:
    """Lista imagens ainda não sincronizadas, separando normal e Shiny."""
    formas = _formas_hd_pendentes()
    click.echo(f"Restam {len(formas)} forma(s) com pelo menos uma imagem original pendente.")
    for forma in formas:
        tipos = []
        if imagem_do_catalogo_padrao(forma.imagem_url):
            tipos.append("normal")
        if imagem_do_catalogo_padrao(forma.imagem_shiny_url):
            tipos.append("shiny")
        click.echo(f"PENDENTE: {forma.codigo} — {', '.join(tipos)}")


@midia_group.command("pokemon-hd")
@click.option("--aplicar", is_flag=True, help="Baixa imagens HD e atualiza o catálogo no PostgreSQL.")
@click.option("--limite", type=click.IntRange(min=1), default=None,
              help="Quantidade máxima de formas a processar nesta execução.")
@click.option("--codigo", default=None, help="Executa somente para uma forma, ex.: deoxys-ataque.")
@click.option("--representativas", is_flag=True,
              help="Autoriza arte Shiny da espécie base para parceiros e núcleo vermelho para Minior.")
def pokemon_hd(aplicar: bool, limite: int | None, codigo: str | None,
               representativas: bool) -> None:
    """Retenta apenas imagens pendentes, sem trocar formas ou uploads manuais."""
    elegiveis = _formas_hd_pendentes(codigo)
    if limite is not None:
        elegiveis = elegiveis[:limite]
    click.echo(f"Imagens Pokémon HD: {len(elegiveis)} forma(s) com imagens pendentes.")
    if not aplicar:
        for forma in elegiveis[:20]:
            click.echo(f"SIMULAR: {forma.codigo}")
        if len(elegiveis) > 20:
            click.echo(f"... e mais {len(elegiveis) - 20}. Use --aplicar para executar.")
        click.echo("Nenhuma imagem foi baixada e nenhum dado foi modificado. Use --aplicar para começar.")
        return

    pasta = Path(current_app.static_folder) / "img" / "pokemon-hd"
    pasta.mkdir(parents=True, exist_ok=True)
    manifesto = pasta / "historico-sincronizacao.jsonl"
    relatorio = pasta / "relatorio-ultima-sincronizacao.json"
    sucessos_completos = 0
    sucessos_parciais = 0
    falhas = 0
    resultados = []
    for forma in elegiveis:
        erros: dict[str, str] = {}
        atualizados = {}
        antigos = {}
        try:
            if representativas:
                artes = procurar_artes_hd(forma.codigo, representativas=True)
            else:
                artes = procurar_artes_hd(forma.codigo)
            for campo, tipo, sufixo in (
                ("imagem_url", "normal", ""),
                ("imagem_shiny_url", "shiny", "-shiny"),
            ):
                url_antiga = getattr(forma, campo)
                if not imagem_do_catalogo_padrao(url_antiga):
                    continue
                # Uma arte ausente/inacessível não impede salvar a outra.
                candidatos = artes.candidatas(tipo)
                if not candidatos:
                    erros[tipo] = "Fonte HD indisponível para esta variante."
                    continue
                for origem in candidatos:
                    try:
                        dados = baixar_arte_hd(origem)
                    except Exception as erro:
                        erros[tipo] = f"{type(erro).__name__}: {erro}"
                        continue
                    extensao = extensao_arte_hd(dados)
                    nome = f"{forma.codigo}{sufixo}.{extensao}"
                    caminho = pasta / nome
                    temporario = pasta / f".{nome}.download"
                    temporario.write_bytes(dados)
                    os.replace(temporario, caminho)
                    novos = f"{current_app.static_url_path or '/static'}/img/pokemon-hd/{nome}"
                    antigos[campo] = url_antiga
                    atualizados[campo] = novos
                    erros.pop(tipo, None)
                    break
            if atualizados:
                for campo, novo in atualizados.items():
                    setattr(forma, campo, novo)
                db.session.commit()
                with manifesto.open("a", encoding="utf-8") as arquivo:
                    arquivo.write(json.dumps({
                        "em": datetime.now(timezone.utc).isoformat(),
                        "codigo": forma.codigo,
                        "fonte": artes.codigo_fonte,
                        "anteriores": antigos,
                        "novas": atualizados,
                    }, ensure_ascii=False) + "\n")
            if atualizados and not erros:
                sucessos_completos += 1
                click.echo(f"ATUALIZADO: {forma.codigo} — {', '.join(atualizados)}")
            elif atualizados:
                sucessos_parciais += 1
                click.echo(f"PARCIAL: {forma.codigo} — atualizado: {', '.join(atualizados)}; "
                           f"pendente: {', '.join(erros)}")
            else:
                falhas += 1
                click.echo(f"PENDENTE: {forma.codigo} — "
                           + "; ".join(f"{tipo}: {mensagem}" for tipo, mensagem in erros.items()))
        except Exception as erro:
            db.session.rollback()
            falhas += 1
            erros["consulta"] = f"{type(erro).__name__}: {erro}"
            click.echo(f"FALHOU: {forma.codigo} — {erros['consulta']}", err=True)
        equivalente = (forma.codigo in ("eevee-parceiro", "pikachu-parceiro", "minior-nucleo")
                       and representativas)
        if equivalente and atualizados:
            click.echo(f"OBSERVAÇÃO: {forma.codigo} usa arte representativa, não exclusiva da forma.")
        resultados.append({"codigo": forma.codigo, "atualizados": list(atualizados),
                           "representativa": bool(equivalente and atualizados), "erros": erros})
    relatorio.write_text(json.dumps({
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "total_processado": len(elegiveis),
        "completos": sucessos_completos,
        "parciais": sucessos_parciais,
        "sem_atualizacao": falhas,
        "formas": resultados,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    click.echo(f"Concluído: {sucessos_completos} completo(s), "
               f"{sucessos_parciais} parcial(is), {falhas} sem atualização.")
    click.echo(f"Relatório detalhado: {relatorio}")
    click.echo("Para listar pendências restantes: flask --app app.py midia pokemon-hd-pendentes")
