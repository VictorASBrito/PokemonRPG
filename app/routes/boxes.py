from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.pokemon_db_service import (
    BOX_ID,
    box_detalhada_db,
    carregar_contexto_pokemon,
    equipe_detalhada_db,
    mover_pokemon_db,
    renomear_box_db,
)

boxes_bp = Blueprint("boxes", __name__)


def _campanha_codigo() -> str:
    return str(current_app.config["CAMPANHA_PADRAO"])


def _carregar(referencia: str):
    return carregar_contexto_pokemon(
        referencia,
        campanha_codigo=_campanha_codigo(),
    )


def _rota_boxes(modo_mestre: bool, jogador_id: str, *, ancora: str | None = None) -> str:
    endpoint = "boxes.boxes_mestre" if modo_mestre else "boxes.boxes_jogador"
    parametros = {"jogador_id": jogador_id} if modo_mestre else {}
    return url_for(endpoint, **parametros, _anchor=ancora)


def _render_boxes(contexto, *, modo_mestre: bool):
    jogador_id = str(contexto.personagem.id)
    equipe = equipe_detalhada_db(contexto)
    box = box_detalhada_db(contexto)
    limite_equipe = int(contexto.regras["limites"]["tamanho_equipe"])

    if modo_mestre:
        voltar_url = url_for("mestre.dashboard")
        equipe_url = url_for("pokemons.equipe_mestre", jogador_id=jogador_id)
        mover_url = url_for("boxes.mover_mestre", jogador_id=jogador_id)
        editar_endpoint = "pokemons.editar_mestre"
        novo_endpoint = "pokemons.novo_mestre"
        renomear_endpoint = "boxes.renomear_mestre"
    else:
        voltar_url = url_for("jogadores.dashboard")
        equipe_url = url_for("pokemons.equipe_jogador")
        mover_url = url_for("boxes.mover_jogador")
        editar_endpoint = "pokemons.editar_jogador"
        novo_endpoint = "pokemons.novo_jogador"
        renomear_endpoint = "boxes.renomear_jogador"

    return render_template(
        "jogador/boxes.html",
        jogador=contexto.jogador,
        equipe=equipe,
        box=box,
        boxes=[box],
        config_boxes={"espacos": box["limite"]},
        limite_equipe=limite_equipe,
        modo_mestre=modo_mestre,
        voltar_url=voltar_url,
        equipe_url=equipe_url,
        mover_url=mover_url,
        editar_endpoint=editar_endpoint,
        novo_pokemon_endpoint=novo_endpoint,
        renomear_endpoint=renomear_endpoint,
        fonte_dados="PostgreSQL",
    )


def _mover(contexto, *, modo_mestre: bool):
    jogador_id = str(contexto.personagem.id)
    pokemon_id = str(request.form.get("pokemon_id", "")).strip()
    destino = str(request.form.get("destino", "")).strip()
    try:
        erro = mover_pokemon_db(
            contexto=contexto,
            pokemon_id=pokemon_id,
            destino=destino,
            usuario_responsavel_id=session.get("usuario_id"),
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao mover Pokémon no PostgreSQL.")
        erro = "Não foi possível mover o Pokémon no banco de dados."
    if erro:
        flash(erro, "erro")
    else:
        flash("Pokémon movido com sucesso.", "sucesso")
    return redirect(_rota_boxes(modo_mestre, jogador_id, ancora="box-pokemon"))


def _renomear(contexto, box_id: str, *, modo_mestre: bool):
    jogador_id = str(contexto.personagem.id)
    if box_id != BOX_ID:
        flash("Box não encontrada.", "erro")
        return redirect(_rota_boxes(modo_mestre, jogador_id, ancora="box-pokemon"))
    try:
        erro = renomear_box_db(
            contexto.personagem.campanha_id,
            str(request.form.get("nome", "")),
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao renomear Box no PostgreSQL.")
        erro = "Não foi possível renomear a Box no banco de dados."
    if erro:
        flash(erro, "erro")
    else:
        flash("Box renomeada com sucesso.", "sucesso")
    return redirect(_rota_boxes(modo_mestre, jogador_id, ancora="box-pokemon"))


@boxes_bp.get("/jogador/boxes")
@perfil_obrigatorio("jogador")
def boxes_jogador():
    contexto = _carregar(str(session.get("personagem_id", "")))
    if contexto is None:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _render_boxes(contexto, modo_mestre=False)


@boxes_bp.post("/jogador/boxes/mover")
@perfil_obrigatorio("jogador")
def mover_jogador():
    contexto = _carregar(str(session.get("personagem_id", "")))
    if contexto is None:
        return redirect(url_for("jogadores.dashboard"))
    return _mover(contexto, modo_mestre=False)


@boxes_bp.post("/jogador/boxes/<box_id>/renomear")
@perfil_obrigatorio("jogador")
def renomear_jogador(box_id: str):
    contexto = _carregar(str(session.get("personagem_id", "")))
    if contexto is None:
        return redirect(url_for("jogadores.dashboard"))
    return _renomear(contexto, box_id, modo_mestre=False)


@boxes_bp.get("/mestre/jogadores/<jogador_id>/boxes")
@perfil_obrigatorio("mestre")
def boxes_mestre(jogador_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.dashboard"))
    return _render_boxes(contexto, modo_mestre=True)


@boxes_bp.post("/mestre/jogadores/<jogador_id>/boxes/mover")
@perfil_obrigatorio("mestre")
def mover_mestre(jogador_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        return redirect(url_for("mestre.dashboard"))
    return _mover(contexto, modo_mestre=True)


@boxes_bp.post("/mestre/jogadores/<jogador_id>/boxes/<box_id>/renomear")
@perfil_obrigatorio("mestre")
def renomear_mestre(jogador_id: str, box_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        return redirect(url_for("mestre.dashboard"))
    return _renomear(contexto, box_id, modo_mestre=True)
