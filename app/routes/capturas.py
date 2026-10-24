from __future__ import annotations

import hmac
import secrets

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.capturaveis_service import (
    atribuir_capturavel_box,
    carregar_painel_capturaveis_mestre,
    criar_capturavel_campo,
    listar_capturaveis_campo,
    remover_capturavel_campo,
)

capturas_bp = Blueprint("capturas", __name__)


def _campanha_codigo() -> str:
    return str(current_app.config["CAMPANHA_PADRAO"])


@capturas_bp.route("/mestre/capturaveis", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def campo_mestre():
    if request.method == "POST":
        try:
            criar_capturavel_campo(
                campanha_codigo=_campanha_codigo(),
                forma_id=request.form.get("forma_id"),
                forma_nome=request.form.get("forma_nome"),
                encontrado_por_personagem_id=request.form.get("encontrado_por_personagem_id"),
                usuario_responsavel_id=session.get("usuario_id"),
            )
        except ValueError as erro:
            db.session.rollback()
            flash(str(erro), "erro")
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Falha ao registrar Pokémon capturável.")
            flash("Não foi possível registrar o Pokémon capturável no banco de dados.", "erro")
        else:
            flash("Pokémon capturável adicionado ao campo.", "sucesso")
        return redirect(url_for("capturas.campo_mestre"))

    try:
        painel = carregar_painel_capturaveis_mestre(campanha_codigo=_campanha_codigo())
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar capturáveis em campo.")
        flash("Não foi possível carregar os capturáveis em campo.", "erro")
        painel = carregar_painel_capturaveis_mestre(campanha_codigo="")
    return render_template(
        "capturas/mestre.html", painel=painel,
        csrf_token=session.setdefault("capturaveis_atribuir_csrf", secrets.token_urlsafe(32)),
    )


@capturas_bp.post("/mestre/capturaveis/<capturavel_id>/remover")
@perfil_obrigatorio("mestre")
def remover_mestre(capturavel_id: str):
    try:
        removido = remover_capturavel_campo(
            campanha_codigo=_campanha_codigo(),
            capturavel_id=capturavel_id,
            usuario_responsavel_id=session.get("usuario_id"),
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao remover Pokémon capturável.")
        flash("Não foi possível remover o Pokémon capturável.", "erro")
    else:
        flash(
            "Pokémon capturável removido do campo." if removido else "Pokémon capturável não encontrado.",
            "sucesso" if removido else "erro",
        )
    return redirect(url_for("capturas.campo_mestre"))


@capturas_bp.post("/mestre/capturaveis/<capturavel_id>/atribuir")
@perfil_obrigatorio("mestre")
def atribuir_mestre(capturavel_id: str):
    token_esperado = str(session.get("capturaveis_atribuir_csrf") or "")
    token_enviado = str(request.form.get("csrf_token") or "")
    if not token_esperado or not hmac.compare_digest(token_esperado, token_enviado):
        flash("Formulário de atribuição expirado. Atualize a página e tente novamente.", "erro")
        return redirect(url_for("capturas.campo_mestre"))
    try:
        pokemon, destinatario = atribuir_capturavel_box(
            campanha_codigo=_campanha_codigo(),
            capturavel_id=capturavel_id,
            personagem_id=str(request.form.get("personagem_id", "")),
            usuario_responsavel_id=session.get("usuario_id"),
        )
    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), "erro")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao atribuir capturável à Box.")
        flash("Não foi possível atribuir o Pokémon à Box.", "erro")
    else:
        flash(f"Pokémon atribuído à Box de {destinatario} com sucesso.", "sucesso")
    return redirect(url_for("capturas.campo_mestre"))


@capturas_bp.get("/jogador/capturaveis")
@perfil_obrigatorio("jogador")
def campo_jogador():
    try:
        capturaveis = listar_capturaveis_campo(campanha_codigo=_campanha_codigo())
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar a lista de capturáveis para o jogador.")
        flash("Não foi possível carregar os Pokémon capturáveis agora.", "erro")
        capturaveis = []
    return render_template("capturas/jogador.html", capturaveis=capturaveis, limite=15)
