"""Entrada visual da campanha. Somente jogadores comuns, mediante allowlist."""
from __future__ import annotations

import hmac

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.services.entrada_personagens_service import personagem_para_entrada

entrada_personagens_bp = Blueprint("entrada_personagens", __name__)


@entrada_personagens_bp.get("/login/coringa")
def coringa():
    return render_template("login.html")


@entrada_personagens_bp.post("/login/personagem/<int:numero>")
def entrar_com_personagem(numero: int):
    esperado = session.get("entrada_personagens_csrf") or ""
    recebido = request.form.get("csrf_token") or ""
    if not esperado or not hmac.compare_digest(esperado, recebido):
        flash("Seleção expirada. Escolha o personagem novamente.", "erro")
        return redirect(url_for("auth.login")), 303

    try:
        autenticado = personagem_para_entrada(
            numero, campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"])
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha na entrada visual de Ankar.")
        flash("Não foi possível acessar a campanha agora.", "erro")
        return redirect(url_for("auth.login")), 303

    if autenticado is None:
        flash("Este personagem não está disponível para entrada direta.", "erro")
        return redirect(url_for("auth.login")), 303

    # FICHAS_POR_URL_10B3: a seleção não substitui a sessão de outra aba.
    from app.services.fichas_url_service import url_ficha_de_login, url_selecao
    usuario, _, _ = autenticado
    try:
        destino = url_ficha_de_login(usuario.login)
    except ValueError:
        flash("Este login não pode ser usado como URL de personagem.", "erro")
        return redirect(url_selecao()), 303
    return redirect(destino), 303
