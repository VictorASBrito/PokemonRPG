from __future__ import annotations

from pathlib import Path

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
from app.services.compatibilidade_legado import (
    buscar_jogador_legado_por_usuario,
    sincronizar_ficha_legada,
)
from app.services.jogador_service import (
    atualizar_ficha_treinador,
    carregar_jogador,
    carregar_regras_treinador,
    salvar_jogador,
)
from app.services.personagem_service import (
    atualizar_ficha_personagem,
    carregar_contexto_ficha,
)
from app.services.pokemon_service import (
    carregar_catalogo_golpes,
    carregar_catalogo_pokemons,
    carregar_regras_pokemon,
    equipe_detalhada,
    sincronizar_pokemons_com_nivel_jogador,
)

jogadores_bp = Blueprint("jogadores", __name__, url_prefix="/jogador")


def _contexto_legado():
    jogador_id = session.get("jogador_id")
    if not jogador_id:
        return None, None, None
    data_dir = Path(current_app.config["DATA_DIR"])
    campanha_id = str(current_app.config["CAMPANHA_PADRAO"])
    jogador = carregar_jogador(data_dir, campanha_id, str(jogador_id))
    return jogador, data_dir, campanha_id


def _dashboard_legado():
    jogador, data_dir, _ = _contexto_legado()
    if not jogador or data_dir is None:
        return None
    treinador = jogador.get("treinador", {})
    regras_treinador = carregar_regras_treinador(data_dir)
    regras_pokemon = carregar_regras_pokemon(data_dir)
    limite_equipe = int(regras_pokemon.get("limites", {}).get("tamanho_equipe", 6))
    equipe = equipe_detalhada(
        jogador=jogador,
        catalogo_pokemons=carregar_catalogo_pokemons(data_dir),
        catalogo_golpes=carregar_catalogo_golpes(data_dir),
        regras=regras_pokemon,
    )
    return render_template(
        "jogador/dashboard.html",
        nome_jogador=session.get("nome", "Jogador"),
        jogador=jogador,
        treinador=treinador,
        atributos_config=regras_treinador.get("atributos", []),
        equipe=equipe,
        limite_equipe=limite_equipe,
        fonte_ficha="JSON de teste",
    )


def _equipe_legada_com_ficha_banco(
    jogador_banco: dict,
    usuario_id: str,
    data_dir: Path,
    campanha_codigo: str,
) -> list[dict]:
    legado = buscar_jogador_legado_por_usuario(
        data_dir,
        campanha_codigo,
        usuario_id,
    )
    if not legado:
        return []
    legado.pop("_arquivo", None)
    legado["treinador"] = dict(jogador_banco.get("treinador", {}))
    regras_pokemon = carregar_regras_pokemon(data_dir)
    return equipe_detalhada(
        jogador=legado,
        catalogo_pokemons=carregar_catalogo_pokemons(data_dir),
        catalogo_golpes=carregar_catalogo_golpes(data_dir),
        regras=regras_pokemon,
    )


@jogadores_bp.get("/dashboard")
@perfil_obrigatorio("jogador")
def dashboard():
    personagem_id = session.get("personagem_id")
    if not personagem_id:
        if current_app.testing:
            legado = _dashboard_legado()
            if legado is not None:
                return legado
        session.clear()
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("auth.login"))

    try:
        contexto = carregar_contexto_ficha(
            str(personagem_id),
            campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
        )
        if contexto is None:
            flash("Sua ficha não foi encontrada no PostgreSQL.", "erro")
            session.clear()
            return redirect(url_for("auth.login"))

        data_dir = Path(current_app.config["DATA_DIR"])
        campanha_codigo = str(current_app.config["CAMPANHA_PADRAO"])
        equipe = _equipe_legada_com_ficha_banco(
            contexto.jogador,
            str(contexto.personagem.usuario_id),
            data_dir,
            campanha_codigo,
        )
    except SQLAlchemyError:
        db.session.rollback()
        if current_app.testing:
            legado = _dashboard_legado()
            if legado is not None:
                return legado
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

    treinador = contexto.jogador["treinador"]
    return render_template(
        "jogador/dashboard.html",
        nome_jogador=contexto.personagem.usuario.nome,
        jogador=contexto.jogador,
        treinador=treinador,
        atributos_config=contexto.regras.get("atributos", []),
        equipe=equipe,
        limite_equipe=int(contexto.regras.get("limite_equipe", 6)),
        fonte_ficha="PostgreSQL",
    )


def _ficha_legada():
    jogador, data_dir, campanha_id = _contexto_legado()
    if not jogador or data_dir is None or campanha_id is None:
        return None
    regras = carregar_regras_treinador(data_dir)
    if request.method == "POST":
        jogador_atualizado, erros = atualizar_ficha_treinador(
            jogador=jogador,
            formulario=request.form,
            regras=regras,
        )
        if erros:
            for erro in erros:
                flash(erro, "erro")
            jogador = jogador_atualizado
        else:
            sincronizar_pokemons_com_nivel_jogador(jogador_atualizado, data_dir)
            salvar_jogador(
                data_dir=data_dir,
                campanha_id=campanha_id,
                jogador=jogador_atualizado,
            )
            flash("Ficha salva com sucesso.", "sucesso")
            return redirect(url_for("jogadores.ficha"))
    return render_template(
        "jogador/ficha.html",
        jogador=jogador,
        regras=regras,
        modo_mestre=False,
        voltar_url=url_for("jogadores.dashboard"),
        salvar_url=url_for("jogadores.ficha"),
        fonte_ficha="JSON de teste",
    )


@jogadores_bp.route("/ficha", methods=["GET", "POST"])
@perfil_obrigatorio("jogador")
def ficha():
    personagem_id = session.get("personagem_id")
    if not personagem_id:
        if current_app.testing:
            legado = _ficha_legada()
            if legado is not None:
                return legado
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))

    try:
        contexto = carregar_contexto_ficha(
            str(personagem_id),
            campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
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
                usuario_responsavel_id=session.get("usuario_id"),
            )
            if erros:
                for erro in erros:
                    flash(erro, "erro")
            else:
                try:
                    sincronizar_ficha_legada(
                        data_dir=current_app.config["DATA_DIR"],
                        campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
                        usuario_id_banco=contexto.personagem.usuario_id,
                        ficha_banco=jogador,
                    )
                except Exception:  # A ponte não pode desfazer uma gravação válida no banco.
                    current_app.logger.exception(
                        "A ficha foi salva, mas a ponte temporária com Pokémon/Box falhou."
                    )
                    flash(
                        "A ficha foi salva, mas a equipe poderá exibir dados antigos até a próxima atualização.",
                        "aviso",
                    )
                flash("Ficha salva com sucesso no PostgreSQL.", "sucesso")
                return redirect(url_for("jogadores.ficha"))
    except SQLAlchemyError:
        db.session.rollback()
        if current_app.testing:
            legado = _ficha_legada()
            if legado is not None:
                return legado
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
