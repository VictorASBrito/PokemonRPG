"""Campo compartilhado para mestre e jogadores; separado de combate automático."""
from __future__ import annotations

import hmac
import secrets

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import login_obrigatorio
from app.services.campo_service import carregar_campo, limpar_campo, posicionar_pokemon, retirar_pokemon
from app.services.campo_npc_service import (
    criar_grupo_npc, adicionar_pokemons_npc, mover_grupo_npc, ajustar_pv_npc,
    retirar_pokemon_npc, remover_grupo_npc,
)
from app.services.permissoes_service import PERFIS_JOGADOR, PERFIS_MESTRE, perfil_usuario_atual

combates_bp = Blueprint("combates", __name__)


def _autorizacao() -> bool:
    """Retorna se é mestre; bloqueia perfis ou sessões inconsistentes."""
    perfil = perfil_usuario_atual(session.get("usuario_id"))
    if perfil in PERFIS_MESTRE and session.get("perfil") == "mestre":
        return True
    if perfil in PERFIS_JOGADOR and session.get("perfil") == "jogador" and session.get("personagem_id"):
        return False
    abort(403)


def _token() -> str:
    return session.setdefault("campo_csrf", secrets.token_urlsafe(32))


def _conferir_token() -> None:
    if not hmac.compare_digest(_token(), str(request.form.get("csrf_token", ""))):
        abort(400, description="Formulário expirado. Atualize a página.")


def _contexto(mestre: bool):
    return carregar_campo(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        mestre=mestre, personagem_id=session.get("personagem_id"),
    )


@combates_bp.get("/campo")
@login_obrigatorio
def painel():
    mestre = _autorizacao()
    try:
        contexto = _contexto(mestre)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar o campo compartilhado.")
        return ("Não foi possível acessar o campo no banco de dados.", 503)
    return render_template("campo/painel.html", contexto=contexto, mestre=mestre, csrf_token=_token())


@combates_bp.get("/campo/estado")
@login_obrigatorio
def estado():
    mestre = _autorizacao()
    try:
        contexto = _contexto(mestre)
    except SQLAlchemyError:
        db.session.rollback()
        return ("Campo indisponível.", 503)
    resposta = render_template("campo/_times.html", contexto=contexto, mestre=mestre, csrf_token=_token())
    return resposta, 200, {"Cache-Control": "no-store"}


@combates_bp.post("/campo/posicionar")
@login_obrigatorio
def posicionar():
    mestre = _autorizacao()
    _conferir_token()
    try:
        mensagem = posicionar_pokemon(
            campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
            pokemon_id=str(request.form.get("pokemon_id", "")),
            time_numero=request.form.get("time_numero", ""),
            mestre=mestre, personagem_id=session.get("personagem_id"),
            usuario_id=session.get("usuario_id"),
        )
        flash(mensagem, "sucesso")
    except PermissionError as exc:
        db.session.rollback()
        abort(403, description=str(exc))
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "erro")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao posicionar Pokémon no campo.")
        flash("Não foi possível posicionar o Pokémon.", "erro")
    return redirect(url_for("combates.painel"))


@combates_bp.post("/campo/pokemons/<pokemon_id>/retirar")
@login_obrigatorio
def retirar(pokemon_id: str):
    mestre = _autorizacao()
    _conferir_token()
    try:
        removido = retirar_pokemon(
            campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
            pokemon_id=pokemon_id, mestre=mestre, personagem_id=session.get("personagem_id"),
            usuario_id=session.get("usuario_id"),
        )
        flash("Pokémon retirado do campo." if removido else "Pokémon não encontrado no campo.",
              "sucesso" if removido else "aviso")
    except PermissionError as exc:
        db.session.rollback()
        abort(403, description=str(exc))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao retirar Pokémon do campo.")
        flash("Não foi possível retirar o Pokémon.", "erro")
    return redirect(url_for("combates.painel"))


@combates_bp.post("/campo/limpar")
@login_obrigatorio
def limpar():
    mestre = _autorizacao()
    if not mestre:
        abort(403)
    _conferir_token()
    try:
        quantidade = limpar_campo(
            campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
            usuario_id=session.get("usuario_id"),
        )
        flash(f"Campo limpo: {quantidade} Pokémon retirado(s).", "sucesso")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao limpar campo compartilhado.")
        flash("Não foi possível limpar o campo.", "erro")
    return redirect(url_for("combates.painel"))


# 10D.4 — NPCs e hordas são exclusivos do mestre; validação no servidor.
def _executar_npc(operacao):
    if not _autorizacao():
        abort(403)
    _conferir_token()
    try:
        flash(operacao(), "sucesso")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "erro")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao gerenciar adversários do Campo.")
        flash("Não foi possível atualizar os adversários.", "erro")
    return redirect(url_for("combates.painel"))


@combates_bp.post("/campo/npcs/criar")
@login_obrigatorio
def criar_npc():
    return _executar_npc(lambda: criar_grupo_npc(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        nome=request.form.get("nome"), tipo=request.form.get("tipo"),
        time_numero=request.form.get("time_numero"),
        forma_id=request.form.get("forma_id"), nivel=request.form.get("nivel"),
        quantidade=request.form.get("quantidade"),
        usuario_id=session.get("usuario_id"),
    ))


@combates_bp.post("/campo/npcs/<grupo_id>/adicionar")
@login_obrigatorio
def adicionar_npc(grupo_id):
    return _executar_npc(lambda: adicionar_pokemons_npc(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        grupo_id=grupo_id, forma_id=request.form.get("forma_id"),
        nivel=request.form.get("nivel"), quantidade=request.form.get("quantidade"),
        usuario_id=session.get("usuario_id"),
    ))


@combates_bp.post("/campo/npcs/<grupo_id>/mover")
@login_obrigatorio
def mover_npc(grupo_id):
    return _executar_npc(lambda: mover_grupo_npc(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        grupo_id=grupo_id, time_numero=request.form.get("time_numero"),
        usuario_id=session.get("usuario_id"),
    ))


@combates_bp.post("/campo/npcs/<grupo_id>/retirar")
@login_obrigatorio
def remover_npc(grupo_id):
    return _executar_npc(lambda: remover_grupo_npc(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        grupo_id=grupo_id, usuario_id=session.get("usuario_id"),
    ))


@combates_bp.post("/campo/npcs/pokemons/<pokemon_id>/pv")
@login_obrigatorio
def pv_npc(pokemon_id):
    return _executar_npc(lambda: ajustar_pv_npc(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        pokemon_id=pokemon_id, quantidade=request.form.get("quantidade"),
        operacao=request.form.get("operacao"),
        usuario_id=session.get("usuario_id"),
    ))


@combates_bp.post("/campo/npcs/pokemons/<pokemon_id>/retirar")
@login_obrigatorio
def retirar_npc(pokemon_id):
    return _executar_npc(lambda: retirar_pokemon_npc(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        pokemon_id=pokemon_id, usuario_id=session.get("usuario_id"),
    ))


@combates_bp.post("/campo/npcs/adicionar")
@login_obrigatorio
def adicionar_npc_selecionado():
    """Formulário estável fora do HTML atualizado por polling."""
    grupo_id = request.form.get("grupo_id", "")
    return _executar_npc(lambda: adicionar_pokemons_npc(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        grupo_id=grupo_id, forma_id=request.form.get("forma_id"),
        nivel=request.form.get("nivel"), quantidade=request.form.get("quantidade"),
        usuario_id=session.get("usuario_id"),
    ))


@combates_bp.post("/campo/npcs/pokemons/<pokemon_id>/capturavel")
@login_obrigatorio
def enviar_horda_capturaveis(pokemon_id):
    from app.services.hordas_captura_service import encaminhar_horda
    return _executar_npc(lambda: encaminhar_horda(
        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        pokemon_id=pokemon_id,
        encontrador_id=request.form.get("encontrador_id"),
        usuario_id=session.get("usuario_id"),
    ))
