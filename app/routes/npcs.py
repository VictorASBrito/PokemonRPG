"""Catálogo permanente de NPCs e gerador regional, exclusivo do mestre."""
from __future__ import annotations

import hmac
import secrets

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.campo_npc_service import _campanha
from app.services.gerador_npcs_ankar import localidades_ankar
from app.services.npc_catalogo_service import (
    CHAVE_RASCUNHO, aplicar_rascunho, arquivar_modelo, colocar_modelo,
    encontrados_campanha, gerar_rascunho, modelos_campanha, rascunho_atual,
    refazer_pokemon_rascunho,
)

npcs_bp = Blueprint("npcs", __name__, url_prefix="/mestre/npcs")


def _codigo():
    return str(current_app.config["CAMPANHA_PADRAO"])


def _token():
    return session.setdefault("npc_catalogo_csrf", secrets.token_urlsafe(32))


def _verificar():
    if not hmac.compare_digest(_token(), str(request.form.get("csrf_token") or "")):
        abort(400, description="Formulário expirado. Atualize a página.")


def _operacao(funcao, *, destino="npcs.catalogo"):
    _verificar()
    try:
        mensagem = funcao()
        flash(mensagem, "sucesso")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "erro")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha no gerador regional de NPCs.")
        flash("O banco não pôde concluir esta operação.", "erro")
    return redirect(url_for(destino))


@npcs_bp.get("")
@perfil_obrigatorio("mestre")
def catalogo():
    try:
        campanha = _campanha(_codigo(), bloquear=False)
        modelos = modelos_campanha(campanha_codigo=_codigo())
        encontrados = encontrados_campanha(campanha.id)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar catálogo de NPCs.")
        return ("Catálogo de NPCs indisponível.", 503)
    try:
        rascunho = rascunho_atual(_codigo())
    except ValueError:
        rascunho = None
    return render_template(
        "mestre/npcs_catalogo.html",
        campanha=campanha, modelos=modelos,
        encontrados=encontrados, localidades=localidades_ankar(),
        rascunho=rascunho, csrf_token=_token(),
    )


@npcs_bp.post("/gerar")
@perfil_obrigatorio("mestre")
def gerar():
    _verificar()
    # Nunca deixar um rascunho anterior após nova tentativa inválida.
    session.pop(CHAVE_RASCUNHO, None)
    return _operacao(lambda: (
        gerar_rascunho(
            campanha_codigo=_codigo(), nome=request.form.get("nome"),
            tipo=request.form.get("tipo"), local_id=request.form.get("local_id"),
            zona_index=request.form.get("zona_index"),
            tabela_index=request.form.get("tabela_index"),
            quantidade=request.form.get("quantidade"),
            nivel=request.form.get("nivel"),
            modo=request.form.get("modo"),
            formas_manuais=request.form.getlist("forma_id_manual"),
            encontrador_id=request.form.get("encontrador_id"),
            permitir_repetidos=request.form.get("repeticoes") == "1",
        ) and "Equipe regional gerada. Revise os Pokémon antes de confirmar."
    ))


@npcs_bp.post("/refazer/<int:indice>")
@perfil_obrigatorio("mestre")
def refazer(indice):
    return _operacao(lambda: (
        refazer_pokemon_rascunho(campanha_codigo=_codigo(), indice=indice)
        and f"Integrante {indice + 1} sorteado novamente."
    ))


@npcs_bp.post("/confirmar")
@perfil_obrigatorio("mestre")
def confirmar():
    acao = request.form.get("acao")
    if acao == "colocar_campo" and not current_app.config.get("CAMPO_OPERACOES_ATIVAS", False):
        abort(403, description="O envio ao Campo está em pausa.")
    return _operacao(lambda: aplicar_rascunho(
        campanha_codigo=_codigo(), acao=acao,
        time_numero=request.form.get("time_numero"), modelo_id=request.form.get("modelo_id"),
        usuario_id=session.get("usuario_id"),
    ), destino="catalogo_admin.npcs" if acao in ("salvar_fixo", "atualizar_fixo") else "combates.painel")


@npcs_bp.post("/modelos/<modelo_id>/campo")
@perfil_obrigatorio("mestre")
def usar_modelo(modelo_id):
    if not current_app.config.get("CAMPO_OPERACOES_ATIVAS", False):
        abort(403, description="O envio ao Campo está em pausa.")
    return _operacao(lambda: colocar_modelo(
        campanha_codigo=_codigo(), modelo_id=modelo_id,
        time_numero=request.form.get("time_numero"),
        usuario_id=session.get("usuario_id"),
    ), destino="catalogo_admin.npcs")


@npcs_bp.post("/modelos/<modelo_id>/arquivar")
@perfil_obrigatorio("mestre")
def arquivar(modelo_id):
    return _operacao(lambda: arquivar_modelo(
        campanha_codigo=_codigo(), modelo_id=modelo_id,
        usuario_id=session.get("usuario_id"),
    ), destino="catalogo_admin.npcs")
