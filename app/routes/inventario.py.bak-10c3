from __future__ import annotations

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.inventario_apresentacao import BOLSAS, VERSAO_INTERFACE, preparar_equipe, preparar_itens
from app.services.inventario_service import (
    adicionar_item,
    ajustar_quantidade_item,
    carregar_contexto_inventario,
    desequipar_item_pokemon,
    equipar_item_pokemon,
    transferir_item,
    usar_item_consumivel,
)

inventario_bp = Blueprint("inventario", __name__)


def _erro_operacao(mensagem_log: str, mensagem_usuario: str = "Não foi possível concluir a operação no inventário.") -> None:
    db.session.rollback()
    current_app.logger.exception(mensagem_log)
    flash(mensagem_usuario, "erro")


def _personagem_jogador() -> str | None:
    valor = session.get("personagem_id")
    return str(valor) if valor else None


def _renderizar(personagem_id: str, *, modo_mestre: bool):
    try:
        contexto = carregar_contexto_inventario(
            personagem_id, campanha_id=session.get("campanha_id")
        )
    except SQLAlchemyError:
        _erro_operacao("Falha ao carregar inventário no PostgreSQL.")
        contexto = None
    if contexto is None:
        flash("Inventário ou personagem não encontrado.", "erro")
        destino = "mestre.dashboard" if modo_mestre else "jogadores.dashboard"
        return redirect(url_for(destino))
    resposta = make_response(render_template(
        "jogador/inventario.html",
        versao_inventario=VERSAO_INTERFACE,
        bolsas=BOLSAS,
        itens_visuais=preparar_itens(contexto.inventario),
        equipe_visual=preparar_equipe(contexto.pokemons, contexto.personagem),
        contexto=contexto,
        personagem=contexto.personagem,
        modo_mestre=modo_mestre,
        voltar_url=(
            url_for("mestre.dashboard")
            if modo_mestre
            else url_for("jogadores.dashboard")
        ),
    ))
    resposta.headers["X-PokemonRPG-Inventario"] = VERSAO_INTERFACE
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


def _executar(operacao, *, retorno: str, sucesso: str, **kwargs):
    try:
        operacao(
            **kwargs,
            usuario_id=session.get("usuario_id"),
            campanha_id=session.get("campanha_id"),
        )
    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), "erro")
    except SQLAlchemyError:
        _erro_operacao(f"Falha durante {operacao.__name__}.")
    else:
        flash(sucesso, "sucesso")
    return redirect(retorno)


@inventario_bp.get("/jogador/inventario")
@perfil_obrigatorio("jogador")
def inventario_jogador():
    personagem_id = _personagem_jogador()
    if not personagem_id:
        flash("Sua ficha ainda não está vinculada a um personagem.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _renderizar(personagem_id, modo_mestre=False)


@inventario_bp.get("/mestre/jogadores/<personagem_id>/inventario")
@perfil_obrigatorio("mestre")
def inventario_mestre(personagem_id: str):
    return _renderizar(personagem_id, modo_mestre=True)


@inventario_bp.post("/mestre/jogadores/<personagem_id>/inventario/adicionar")
@perfil_obrigatorio("mestre")
def adicionar_mestre(personagem_id: str):
    retorno = url_for("inventario.inventario_mestre", personagem_id=personagem_id)
    return _executar(
        adicionar_item,
        retorno=retorno,
        sucesso="Item adicionado ao inventário.",
        personagem_id=personagem_id,
        item_id=request.form.get("item_id"),
        quantidade=request.form.get("quantidade"),
    )


@inventario_bp.post("/mestre/jogadores/<personagem_id>/inventario/ajustar")
@perfil_obrigatorio("mestre")
def ajustar_mestre(personagem_id: str):
    retorno = url_for("inventario.inventario_mestre", personagem_id=personagem_id)
    return _executar(
        ajustar_quantidade_item,
        retorno=retorno,
        sucesso="Quantidade atualizada.",
        personagem_id=personagem_id,
        item_id=request.form.get("item_id"),
        quantidade=request.form.get("quantidade"),
    )


def _usar(personagem_id: str, *, modo_mestre: bool):
    retorno = (
        url_for("inventario.inventario_mestre", personagem_id=personagem_id)
        if modo_mestre
        else url_for("inventario.inventario_jogador")
    )
    return _executar(
        usar_item_consumivel,
        retorno=retorno,
        sucesso="Uso do item registrado e quantidade atualizada.",
        personagem_id=personagem_id,
        item_id=request.form.get("item_id"),
        quantidade=request.form.get("quantidade", 1),
    )


@inventario_bp.post("/jogador/inventario/usar")
@perfil_obrigatorio("jogador")
def usar_jogador():
    personagem_id = _personagem_jogador()
    if not personagem_id:
        return redirect(url_for("jogadores.dashboard"))
    return _usar(personagem_id, modo_mestre=False)


@inventario_bp.post("/mestre/jogadores/<personagem_id>/inventario/usar")
@perfil_obrigatorio("mestre")
def usar_mestre(personagem_id: str):
    return _usar(personagem_id, modo_mestre=True)


def _equipar(personagem_id: str, *, modo_mestre: bool):
    retorno = (
        url_for("inventario.inventario_mestre", personagem_id=personagem_id)
        if modo_mestre
        else url_for("inventario.inventario_jogador")
    )
    return _executar(
        equipar_item_pokemon,
        retorno=retorno,
        sucesso="Item entregue ao Pokémon.",
        personagem_id=personagem_id,
        item_id=request.form.get("item_id"),
        pokemon_id=request.form.get("pokemon_id"),
    )


@inventario_bp.post("/jogador/inventario/equipar")
@perfil_obrigatorio("jogador")
def equipar_jogador():
    personagem_id = _personagem_jogador()
    if not personagem_id:
        return redirect(url_for("jogadores.dashboard"))
    return _equipar(personagem_id, modo_mestre=False)


@inventario_bp.post("/mestre/jogadores/<personagem_id>/inventario/equipar")
@perfil_obrigatorio("mestre")
def equipar_mestre(personagem_id: str):
    return _equipar(personagem_id, modo_mestre=True)


def _desequipar(personagem_id: str, *, modo_mestre: bool):
    retorno = (
        url_for("inventario.inventario_mestre", personagem_id=personagem_id)
        if modo_mestre
        else url_for("inventario.inventario_jogador")
    )
    return _executar(
        desequipar_item_pokemon,
        retorno=retorno,
        sucesso="Item devolvido ao inventário.",
        personagem_id=personagem_id,
        pokemon_id=request.form.get("pokemon_id"),
    )


@inventario_bp.post("/jogador/inventario/desequipar")
@perfil_obrigatorio("jogador")
def desequipar_jogador():
    personagem_id = _personagem_jogador()
    if not personagem_id:
        return redirect(url_for("jogadores.dashboard"))
    return _desequipar(personagem_id, modo_mestre=False)


@inventario_bp.post("/mestre/jogadores/<personagem_id>/inventario/desequipar")
@perfil_obrigatorio("mestre")
def desequipar_mestre(personagem_id: str):
    return _desequipar(personagem_id, modo_mestre=True)


def _transferir(personagem_id: str, *, modo_mestre: bool):
    retorno = (
        url_for("inventario.inventario_mestre", personagem_id=personagem_id)
        if modo_mestre
        else url_for("inventario.inventario_jogador")
    )
    return _executar(
        transferir_item,
        retorno=retorno,
        sucesso="Item transferido para o outro personagem.",
        personagem_origem_id=personagem_id,
        personagem_destino_id=request.form.get("personagem_destino_id"),
        item_id=request.form.get("item_id"),
        quantidade=request.form.get("quantidade"),
    )


@inventario_bp.post("/jogador/inventario/transferir")
@perfil_obrigatorio("jogador")
def transferir_jogador():
    personagem_id = _personagem_jogador()
    if not personagem_id:
        return redirect(url_for("jogadores.dashboard"))
    return _transferir(personagem_id, modo_mestre=False)


@inventario_bp.post("/mestre/jogadores/<personagem_id>/inventario/transferir")
@perfil_obrigatorio("mestre")
def transferir_mestre(personagem_id: str):
    return _transferir(personagem_id, modo_mestre=True)
