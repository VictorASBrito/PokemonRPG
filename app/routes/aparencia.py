"""Preferências visuais sem alterações de gameplay."""
import secrets

from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.services.aparencia_service import MODOS, titular_aparencia, opcoes_aparencia

aparencia_bp = Blueprint("aparencia", __name__)


@aparencia_bp.app_context_processor
def contexto():
    from app.services.aparencia_service import contexto_aparencia
    dados = contexto_aparencia()
    if dados["autenticado"]:
        if not session.get("aparencia_csrf"):
            session["aparencia_csrf"] = secrets.token_urlsafe(32)
        dados["csrf"] = session["aparencia_csrf"]
    return {"aparencia": dados}


@aparencia_bp.post("/preferencias/aparencia")
def salvar():
    titular, usuario = titular_aparencia()
    if titular is None:
        return jsonify(erro="Sessão não autorizada."), 403
    token = session.get("aparencia_csrf")
    informado = request.headers.get("X-Aparencia-CSRF", "")
    if not token or not secrets.compare_digest(token, informado):
        return jsonify(erro="Sessão expirada. Atualize a página."), 403
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify(erro="Preferência inválida."), 400
    modo, paleta = dados.get("modo"), dados.get("paleta")
    if not isinstance(modo, str) or not isinstance(paleta, str) or modo not in MODOS or paleta not in opcoes_aparencia(titular, usuario):
        return jsonify(erro="Preferência inválida."), 400
    titular.aparencia_modo = modo
    titular.aparencia_paleta = paleta
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(erro="Não foi possível salvar a aparência."), 500
    return jsonify(ok=True)
