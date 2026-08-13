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
from app.services.personagem_service import (
    atualizar_ficha_personagem,
    carregar_contexto_ficha,
)
from app.services.pokemon_db_service import (
    carregar_contexto_pokemon,
    equipe_detalhada_db,
)

jogadores_bp = Blueprint("jogadores", __name__, url_prefix="/jogador")


def _campanha_codigo() -> str:
    return str(current_app.config["CAMPANHA_PADRAO"])


@jogadores_bp.get("/dashboard")
@perfil_obrigatorio("jogador")
def dashboard():
    personagem_id = session.get("personagem_id")
    if not personagem_id:
        session.clear()
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("auth.login"))

    try:
        ficha = carregar_contexto_ficha(
            str(personagem_id),
            campanha_codigo=_campanha_codigo(),
        )
        contexto_pokemon = carregar_contexto_pokemon(
            str(personagem_id),
            campanha_codigo=_campanha_codigo(),
        )
        if ficha is None or contexto_pokemon is None:
            flash("Sua ficha não foi encontrada no PostgreSQL.", "erro")
            session.clear()
            return redirect(url_for("auth.login"))
        equipe = equipe_detalhada_db(contexto_pokemon)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar o dashboard no PostgreSQL.")
        flash("Não foi possível carregar sua ficha no banco de dados.", "erro")
        return render_template(
            "jogador/dashboard.html",
            nome_jogador=session.get("nome", "Jogador"),
            jogador={"treinador": {}},
            treinador={},
            atributos_config=[],
            equipe=[],
            limite_equipe=6,
            fonte_ficha="PostgreSQL",
        ), 503

    treinador = ficha.jogador["treinador"]
    return render_template(
        "jogador/dashboard.html",
        nome_jogador=ficha.personagem.usuario.nome,
        jogador=ficha.jogador,
        treinador=treinador,
        atributos_config=ficha.regras.get("atributos", []),
        equipe=equipe,
        limite_equipe=int(contexto_pokemon.regras["limites"]["tamanho_equipe"]),
        fonte_ficha="PostgreSQL",
    )


@jogadores_bp.route("/ficha", methods=["GET", "POST"])
@perfil_obrigatorio("jogador")
def ficha():
    personagem_id = session.get("personagem_id")
    if not personagem_id:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))

    try:
        contexto = carregar_contexto_ficha(
            str(personagem_id),
            campanha_codigo=_campanha_codigo(),
        )
        if contexto is None:
            flash("Sua ficha não foi encontrada no PostgreSQL.", "erro")
            return redirect(url_for("jogadores.dashboard"))

        jogador = contexto.jogador
        if request.method == "POST":
            jogador, erros = atualizar_ficha_personagem(
                personagem=contexto.personagem,
                formulario=request.form,
                regras=contexto.regras,
                arquivo_foto=request.files.get("foto_arquivo"),
                remover_foto=request.form.get("remover_foto") == "1",
                usuario_responsavel_id=session.get("usuario_id"),
            )
            if erros:
                for erro in erros:
                    flash(erro, "erro")
            else:
                flash("Ficha salva com sucesso no PostgreSQL.", "sucesso")
                return redirect(url_for("jogadores.ficha"))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao acessar a ficha no PostgreSQL.")
        flash("Não foi possível acessar a ficha no banco de dados.", "erro")
        return redirect(url_for("jogadores.dashboard"))

    return render_template(
        "jogador/ficha.html",
        jogador=jogador,
        regras=contexto.regras,
        modo_mestre=False,
        voltar_url=url_for("jogadores.dashboard"),
        salvar_url=url_for("jogadores.ficha"),
        fonte_ficha="PostgreSQL",
    )
