from __future__ import annotations

from pathlib import Path
from typing import Any

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

from app.routes.auth import perfil_obrigatorio
from app.services.box_service import (
    boxes_detalhadas,
    carregar_config_boxes,
    garantir_estrutura_boxes,
    mover_pokemon,
    renomear_box,
)
from app.services.jogador_service import carregar_jogador, salvar_jogador
from app.services.pokemon_service import (
    carregar_catalogo_golpes,
    carregar_catalogo_pokemons,
    carregar_regras_pokemon,
)

boxes_bp = Blueprint("boxes", __name__)


def _contexto() -> tuple[Path, str]:
    return (
        Path(current_app.config["DATA_DIR"]),
        str(current_app.config["CAMPANHA_PADRAO"]),
    )


def _carregar(jogador_id: str) -> tuple[dict[str, Any] | None, Path, str, dict[str, Any]]:
    data_dir, campanha_id = _contexto()
    regras = carregar_regras_pokemon(data_dir)
    jogador = carregar_jogador(data_dir, campanha_id, jogador_id)
    if jogador:
        garantir_estrutura_boxes(jogador, regras)
    return jogador, data_dir, campanha_id, regras


def _rota_boxes(modo_mestre: bool, jogador_id: str, *, ancora: str | None = None) -> str:
    endpoint = "boxes.boxes_mestre" if modo_mestre else "boxes.boxes_jogador"
    argumentos: dict[str, Any] = {"_anchor": ancora} if ancora else {}
    if modo_mestre:
        argumentos["jogador_id"] = jogador_id
    return url_for(endpoint, **argumentos)


def _render_boxes(jogador: dict[str, Any], regras: dict[str, Any], *, modo_mestre: bool):
    data_dir, _ = _contexto()
    catalogo_pokemons = carregar_catalogo_pokemons(data_dir)
    catalogo_golpes = carregar_catalogo_golpes(data_dir)
    equipe, boxes = boxes_detalhadas(
        jogador=jogador,
        catalogo_pokemons=catalogo_pokemons,
        catalogo_golpes=catalogo_golpes,
        regras=regras,
    )
    jogador_id = str(jogador["id"])

    return render_template(
        "jogador/boxes.html",
        jogador=jogador,
        equipe=equipe,
        box=boxes[0],
        config_boxes=carregar_config_boxes(regras),
        limite_equipe=int(regras.get("limites", {}).get("tamanho_equipe", 6)),
        modo_mestre=modo_mestre,
        voltar_url=(
            url_for("mestre.jogadores")
            if modo_mestre
            else url_for("jogadores.dashboard")
        ),
        equipe_url=(
            url_for("pokemons.equipe_mestre", jogador_id=jogador_id)
            if modo_mestre
            else url_for("pokemons.equipe_jogador")
        ),
        mover_url=(
            url_for("boxes.mover_mestre", jogador_id=jogador_id)
            if modo_mestre
            else url_for("boxes.mover_jogador")
        ),
        renomear_endpoint=(
            "boxes.renomear_mestre" if modo_mestre else "boxes.renomear_jogador"
        ),
        editar_endpoint=(
            "pokemons.editar_mestre" if modo_mestre else "pokemons.editar_jogador"
        ),
        novo_pokemon_endpoint=(
            "pokemons.novo_mestre" if modo_mestre else "pokemons.novo_jogador"
        ),
    )


def _mover(
    jogador: dict[str, Any],
    data_dir: Path,
    campanha_id: str,
    regras: dict[str, Any],
    *,
    modo_mestre: bool,
):
    pokemon_id = str(request.form.get("pokemon_id", "")).strip()
    destino = str(request.form.get("destino", "")).strip()
    erro = mover_pokemon(
        jogador,
        regras,
        pokemon_id=pokemon_id,
        destino=destino,
    )
    if erro:
        flash(erro, "erro")
    else:
        salvar_jogador(data_dir=data_dir, campanha_id=campanha_id, jogador=jogador)
        mensagem = (
            "Pokémon adicionado ao fim da equipe."
            if destino == "equipe"
            else "Pokémon enviado para o último espaço ocupado da Box."
        )
        flash(mensagem, "sucesso")
    ancora = "equipe-ativa" if destino == "equipe" else "box-pokemon"
    return redirect(_rota_boxes(modo_mestre, str(jogador["id"]), ancora=ancora))


def _renomear(
    jogador: dict[str, Any],
    data_dir: Path,
    campanha_id: str,
    box_id: str,
    *,
    modo_mestre: bool,
):
    erro = renomear_box(jogador, box_id, str(request.form.get("nome", "")))
    if erro:
        flash(erro, "erro")
    else:
        salvar_jogador(data_dir=data_dir, campanha_id=campanha_id, jogador=jogador)
        flash("Box renomeada com sucesso.", "sucesso")
    return redirect(_rota_boxes(modo_mestre, str(jogador["id"]), ancora="box-pokemon"))


@boxes_bp.get("/jogador/boxes")
@perfil_obrigatorio("jogador")
def boxes_jogador():
    jogador_id = str(session.get("jogador_id", ""))
    jogador, _, _, regras = _carregar(jogador_id)
    if not jogador:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _render_boxes(jogador, regras, modo_mestre=False)


@boxes_bp.post("/jogador/boxes/mover")
@perfil_obrigatorio("jogador")
def mover_jogador():
    jogador_id = str(session.get("jogador_id", ""))
    jogador, data_dir, campanha_id, regras = _carregar(jogador_id)
    if not jogador:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _mover(jogador, data_dir, campanha_id, regras, modo_mestre=False)


@boxes_bp.post("/jogador/boxes/<box_id>/renomear")
@perfil_obrigatorio("jogador")
def renomear_jogador(box_id: str):
    jogador_id = str(session.get("jogador_id", ""))
    jogador, data_dir, campanha_id, _ = _carregar(jogador_id)
    if not jogador:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _renomear(jogador, data_dir, campanha_id, box_id, modo_mestre=False)


@boxes_bp.get("/mestre/jogadores/<jogador_id>/boxes")
@perfil_obrigatorio("mestre")
def boxes_mestre(jogador_id: str):
    jogador, _, _, regras = _carregar(jogador_id)
    if not jogador:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.jogadores"))
    return _render_boxes(jogador, regras, modo_mestre=True)


@boxes_bp.post("/mestre/jogadores/<jogador_id>/boxes/mover")
@perfil_obrigatorio("mestre")
def mover_mestre(jogador_id: str):
    jogador, data_dir, campanha_id, regras = _carregar(jogador_id)
    if not jogador:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.jogadores"))
    return _mover(jogador, data_dir, campanha_id, regras, modo_mestre=True)


@boxes_bp.post("/mestre/jogadores/<jogador_id>/boxes/<box_id>/renomear")
@perfil_obrigatorio("mestre")
def renomear_mestre(jogador_id: str, box_id: str):
    jogador, data_dir, campanha_id, _ = _carregar(jogador_id)
    if not jogador:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.jogadores"))
    return _renomear(jogador, data_dir, campanha_id, box_id, modo_mestre=True)
