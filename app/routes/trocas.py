"""Central de Trocas na Box; cada ação usa a identidade da sessão."""
import secrets

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.db import Personagem, Pokemon, TrocaPokemon
from app.routes.auth import perfil_obrigatorio
from app.services import trocas_service as s

trocas_bp = Blueprint("trocas", __name__, url_prefix="/jogador/boxes/trocas")


def _autor():
    try:
        return s.titular(session)
    except s.ErroTroca:
        abort(403)


def _token():
    if not session.get("troca_csrf"):
        session["troca_csrf"] = secrets.token_urlsafe(32)
    return session["troca_csrf"]


def _validar_token():
    token = session.get("troca_csrf")
    if not token or not secrets.compare_digest(token, request.form.get("csrf_token", "")):
        abort(403)


def _render(**dados):
    return render_template("jogador/trocas.html", csrf=_token(), **dados)


@trocas_bp.get("/")
@perfil_obrigatorio("jogador")
def central():
    autor = _autor()
    jogadores = db.session.scalars(s.jogadores(autor.campanha_id).where(
        Personagem.id != autor.id).order_by(Personagem.nome)).all()
    trocas = db.session.scalars(s.consulta(autor).order_by(
        TrocaPokemon.atualizado_em.desc())).all()
    nomes = {p.id: p.nome for p in db.session.scalars(select(Personagem).where(
        Personagem.campanha_id == autor.campanha_id)).all()}
    return _render(autor=autor, jogadores=jogadores, trocas=trocas, nomes=nomes)


@trocas_bp.post("/nova")
@perfil_obrigatorio("jogador")
def nova():
    autor = _autor()
    _validar_token()
    try:
        troca = s.criar(autor, request.form.get("destinatario"))
        codigo = troca.id
        db.session.commit()
    except (s.ErroTroca, SQLAlchemyError) as erro:
        db.session.rollback()
        flash(str(erro) if isinstance(erro, s.ErroTroca) else "Não foi possível criar a troca.", "erro")
        return redirect(url_for("trocas.central"), code=303)
    flash("Convite enviado. Aguarde o outro jogador aceitar.", "sucesso")
    return redirect(url_for("trocas.detalhe", troca_id=codigo), code=303)


@trocas_bp.get("/<uuid:troca_id>")
@perfil_obrigatorio("jogador")
def detalhe(troca_id):
    autor = _autor()
    troca = s.buscar(autor, troca_id)
    if troca is None:
        abort(404)
    a = autor.id == troca.proponente_id
    outro = db.session.get(Personagem, troca.destinatario_id if a else troca.proponente_id)
    registros = db.session.scalars(select(Pokemon).where(
        Pokemon.personagem_id == autor.id, Pokemon.localizacao == "box",
        Pokemon.ativo.is_(True)).order_by(Pokemon.posicao, Pokemon.id)).all()
    campo = s.campo_ids([p.id for p in registros])
    disponiveis = [p for p in registros if s.elegivel(p, campo)]
    ids = [s.uuid_valido(i) for i in troca.oferta_a + troca.oferta_b]
    oferecidos = {str(p.id): p for p in db.session.scalars(select(Pokemon).where(
        Pokemon.id.in_(ids))).all()}
    return _render(autor=autor, outro=outro, troca=troca, a=a, disponiveis=disponiveis,
                   oferecidos=oferecidos, minha_oferta=troca.oferta_a if a else troca.oferta_b,
                   oferta_outro=troca.oferta_b if a else troca.oferta_a,
                   confirmei=troca.confirmou_a if a else troca.confirmou_b,
                   outro_confirmou=troca.confirmou_b if a else troca.confirmou_a)


@trocas_bp.post("/<uuid:troca_id>/acao")
@perfil_obrigatorio("jogador")
def agir(troca_id):
    autor = _autor()
    _validar_token()
    troca = s.buscar(autor, troca_id, bloquear=True)
    if troca is None:
        abort(404)
    try:
        s.agir(troca, autor, request.form.get("acao"), request.form.get("revisao"),
               request.form.getlist("pokemon_id"))
        concluida = troca.estado == "concluida"
        db.session.commit()
        flash("Troca concluída! Os Pokémon já estão nas Boxes." if concluida else "Negociação atualizada.", "sucesso")
    except s.ErroTroca as erro:
        db.session.rollback()
        flash(str(erro), "erro")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha transacional na troca de Pokémon.")
        flash("A troca não foi concluída. Nenhum Pokémon foi transferido; atualize e tente novamente.", "erro")
    return redirect(url_for("trocas.detalhe", troca_id=troca_id), code=303)
