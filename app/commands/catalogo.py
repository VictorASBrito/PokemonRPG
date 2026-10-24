from __future__ import annotations

import click
from flask import Blueprint
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Atributo,
    CategoriaGolpe,
    CategoriaItem,
    Campanha,
    HistoricoAlteracao,
    Natureza,
    Personagem,
    PersonagemItem,
    Pokemon,
    EspeciePokemon,
    FormaPokemon,
    FormaPokemonAtributo,
    FormaPokemonGolpe,
    FormaPokemonTipo,
    Golpe,
    Item,
    StatusCondicao,
    TipoPokemon,
)
from app.services.golpe_admin_service import METODOS_APRENDIZADO, TIPOS_EFEITO, efeitos_para_editor
from app.services.item_admin_service import TIPOS_EFEITO_ITEM, efeitos_item_para_editor
from app.services.auditoria_itens_service import auditar_itens
from app.services.reparo_natureza_importada import (
    campo_item_repetido_da_natureza,
    elegivel_para_desvincular,
)

catalogo_cli = Blueprint("catalogo_cli", __name__)


@catalogo_cli.cli.group("catalogo")
def catalogo_group() -> None:
    """Diagnósticos do catálogo administrável."""


@catalogo_group.command("verificar")
def verificar() -> None:
    """Confere espécies, formas, golpes, itens e seus relacionamentos."""
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

    problemas_itens: list[str] = []
    tipos_efeito_item_validos = {item[0] for item in TIPOS_EFEITO_ITEM}
    itens_catalogo = list(db.session.execute(select(Item)).scalars())
    for item in itens_catalogo:
        if item.preco < 0:
            problemas_itens.append(f"{item.nome}: preço negativo.")
        if item.categoria_id:
            categoria = db.session.get(CategoriaItem, item.categoria_id)
            if categoria is None:
                problemas_itens.append(f"{item.nome}: categoria inexistente.")
            elif item.ativo and not categoria.ativo:
                problemas_itens.append(f"{item.nome}: item ativo vinculado a categoria inativa.")
        efeitos = efeitos_item_para_editor(item.efeitos)
        if len(efeitos) > 20:
            problemas_itens.append(f"{item.nome}: possui mais de 20 efeitos.")
        for indice, efeito in enumerate(efeitos, start=1):
            tipo_efeito = efeito.get("tipo", "texto")
            if tipo_efeito not in tipos_efeito_item_validos:
                problemas_itens.append(
                    f"{item.nome}: efeito {indice} possui tipo desconhecido ({tipo_efeito})."
                )

    click.echo(f"Itens: {len(itens_catalogo)} registro(s) no catálogo.")
    if problemas_itens:
        for problema in problemas_itens[:50]:
            click.echo(f"- {problema}", err=True)
        if len(problemas_itens) > 50:
            click.echo(f"- ... e mais {len(problemas_itens) - 50} problema(s).", err=True)
        raise click.ClickException("Foram encontradas inconsistências no catálogo de itens.")
    click.echo("Catálogo de itens está consistente no PostgreSQL.")


@catalogo_group.command("auditar-itens")
@click.option(
    "--todos",
    is_flag=True,
    help="Exibe todos os achados, em vez dos primeiros 50.",
)
def auditar_itens_comando(todos: bool) -> None:
    """Auditoria detalhada e SOMENTE LEITURA do catálogo de itens PostgreSQL.

    Não apaga, atualiza, importa ou normaliza registros. Erros encerram
    com código diferente de zero; avisos exigem conferência humana.
    """
    categorias = list(db.session.execute(select(CategoriaItem)).scalars())
    itens = list(db.session.execute(select(Item)).scalars())
    status_ativos = set(
        str(valor)
        for valor in db.session.execute(
            select(StatusCondicao.id).where(StatusCondicao.ativo.is_(True))
        ).scalars()
    )
    atributos_ativos = set(
        db.session.execute(
            select(Atributo.codigo).where(Atributo.ativo.is_(True))
        ).scalars()
    )
    tipos_ativos = set(
        str(valor)
        for valor in db.session.execute(
            select(TipoPokemon.id).where(TipoPokemon.ativo.is_(True))
        ).scalars()
    )
    resultado = auditar_itens(
        (
            {
                "codigo": item.codigo,
                "nome": item.nome,
                "categoria_id": item.categoria_id,
                "preco": item.preco,
                "ativo": item.ativo,
                "consumivel": item.consumivel,
                "equipavel": item.equipavel,
                "uso_em_batalha": item.uso_em_batalha,
                "efeitos": item.efeitos,
            }
            for item in itens
        ),
        (
            {"id": categoria.id, "codigo": categoria.codigo,
             "nome": categoria.nome, "ativo": categoria.ativo}
            for categoria in categorias
        ),
        status_ativos=status_ativos,
        atributos_ativos=atributos_ativos,
        tipos_ativos=tipos_ativos,
    )
    click.echo(
        f"Auditoria (somente leitura): {resultado.total_itens} item(ns) "
        f"({resultado.ativos} ativo(s)), {resultado.total_categorias} categoria(s)."
    )
    click.echo("Quantidade de itens por categoria:")
    for categoria, quantidade in resultado.categorias.items():
        click.echo(f"  {categoria}: {quantidade}")
    click.echo(f"Resultado: {resultado.erros} erro(s), {resultado.avisos} aviso(s).")
    achados = resultado.achados if todos else resultado.achados[:50]
    for achado in achados:
        click.echo(
            f"- [{achado.nivel.upper()}] {achado.codigo}: {achado.mensagem}",
            err=True,
        )
    if len(resultado.achados) > len(achados):
        click.echo(
            f"- ... {len(resultado.achados) - len(achados)} achado(s) oculto(s); "
            "execute com --todos para ver tudo.", err=True
        )
    if resultado.erros:
        raise click.ClickException(
            "Foram encontrados erros no catálogo. A auditoria não modificou o banco."
        )
    if resultado.avisos:
        click.echo("Sem erros automáticos; avisos precisam de revisão humana.")
    else:
        click.echo("Nenhuma inconsistência identificada pelas verificações implementadas.")


@catalogo_group.command("revisar-naturezas-importadas")
@click.option(
    "--aplicar", is_flag=True,
    help="Desvincula APENAS equipamentos fictícios identificados; padrão é simulação.",
)
def revisar_naturezas_importadas(aplicar: bool) -> None:
    """Verifica o erro da importação de fichas que equipou naturezas como itens.

    O reparo é restrito à campanha Ankar e a itens criados pelo importador,
    sem categoria/efeitos/preço e sem unidades registradas em inventários.
    Não apaga itens nem modifica quantidades, naturezas ou personagens.
    """
    equipados = list(db.session.execute(
        select(Pokemon)
        .join(Pokemon.personagem)
        .join(Personagem.campanha)
        .where(Campanha.codigo == "ankar", Pokemon.item_equipado_id.is_not(None))
        .options(selectinload(Pokemon.item_equipado), selectinload(Pokemon.natureza))
    ).scalars())
    ids_inventario = set(db.session.execute(select(PersonagemItem.item_id)).scalars())
    candidatos = []
    suspeitos_nao_elegiveis = []
    for pokemon in equipados:
        item = pokemon.item_equipado
        natureza = pokemon.natureza
        if item is None or natureza is None:
            continue
        if not campo_item_repetido_da_natureza(item.nome, natureza.nome):
            continue
        if elegivel_para_desvincular(
            codigo_item=item.codigo, nome_item=item.nome,
            nome_natureza=natureza.nome, personalizado=item.personalizado,
            equipavel=item.equipavel, categoria_id=item.categoria_id,
            preco=item.preco, consumivel=item.consumivel,
            uso_em_batalha=item.uso_em_batalha, efeitos=item.efeitos,
            aparece_em_inventario=item.id in ids_inventario,
        ):
            candidatos.append((pokemon, item))
        else:
            suspeitos_nao_elegiveis.append(item.codigo)

    click.echo(f"Equipamentos vinculados na campanha Ankar: {len(equipados)}.")
    click.echo(f"Naturezas importadas elegíveis à correção: {len(candidatos)}.")
    click.echo(f"Coincidências não elegíveis, mantidas para revisão: {len(suspeitos_nao_elegiveis)}.")
    from collections import Counter
    for nome_item, quantidade in sorted(Counter(item.nome for _, item in candidatos).items()):
        click.echo(f"  {nome_item}: {quantidade} vínculo(s)")
    if suspeitos_nao_elegiveis:
        click.echo("Registros ignorados por segurança: " + ", ".join(sorted(set(suspeitos_nao_elegiveis))))
    if not aplicar:
        click.echo("SIMULAÇÃO: nenhuma alteração no banco. Faça backup e revise os resultados antes de usar --aplicar.")
        return
    if not candidatos:
        click.echo("Nenhuma mudança necessária; banco preservado.")
        return
    for pokemon, item in candidatos:
        db.session.add(HistoricoAlteracao(
            usuario_id=None, entidade="pokemon", registro_id=pokemon.id,
            acao="correcao_importacao",
            dados_anteriores={"item_equipado_id": str(item.id), "codigo_item": item.codigo},
            dados_novos={"item_equipado_id": None, "motivo": "natureza_repetida_como_item_na_ficha"},
        ))
        pokemon.item_equipado_id = None
    db.session.commit()
    click.echo(
        f"Corrigidos {len(candidatos)} vínculo(s) em uma transação; "
        "itens do catálogo e inventários não foram modificados."
    )
