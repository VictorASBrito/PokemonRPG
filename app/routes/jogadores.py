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

from app.routes.auth import perfil_obrigatorio
from app.services.jogador_service import (
    atualizar_ficha_treinador,
    carregar_jogador,
    carregar_regras_treinador,
    salvar_jogador,
)

jogadores_bp = Blueprint("jogadores", __name__, url_prefix="/jogador")


def _carregar_jogador_da_sessao():
    jogador_id = session.get("jogador_id")
    if not jogador_id:
        return None, None, None

    data_dir = Path(current_app.config["DATA_DIR"])
    campanha_id = str(current_app.config["CAMPANHA_PADRAO"])
    jogador = carregar_jogador(data_dir, campanha_id, str(jogador_id))
    return jogador, data_dir, campanha_id


@jogadores_bp.get("/dashboard")
@perfil_obrigatorio("jogador")
def dashboard():
    jogador, _, _ = _carregar_jogador_da_sessao()
    if not jogador:
        session.clear()
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("auth.login"))

    treinador = jogador.get("treinador", {})
    return render_template(
        "jogador/dashboard.html",
        nome=treinador.get("nome") or session.get("nome", "Jogador"),
        jogador=jogador,
    )


@jogadores_bp.route("/ficha", methods=["GET", "POST"])
@perfil_obrigatorio("jogador")
def ficha():
    jogador, data_dir, campanha_id = _carregar_jogador_da_sessao()
    if not jogador or data_dir is None or campanha_id is None:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))

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
    )
