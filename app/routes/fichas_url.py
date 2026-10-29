"""Escolha de personagem independente da sessão principal do navegador."""
from __future__ import annotations

import secrets

from flask import Blueprint, current_app, redirect, render_template, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.services.entrada_personagens_service import listar_slots_visuais, slots_vazios

fichas_url_bp = Blueprint("fichas_url", __name__)


@fichas_url_bp.get("/selecionar")
def selecionar():
    """Mostra o círculo mesmo quando outra aba já usa a conta Mestre."""
    try:
        slots = listar_slots_visuais(campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao listar entrada visual.")
        slots = slots_vazios()
    return render_template(
        "entrada_personagens.html",
        slots=slots,
        entrada_csrf=session.setdefault("entrada_personagens_csrf", secrets.token_urlsafe(32)),
    )
