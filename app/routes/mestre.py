from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.painel_mestre_service import (
    ajustar_pv_personagem,
    ajustar_pv_pokemon,
    carregar_painel_mestre,
    salvar_ordem_jogadores_painel,
)
from app.services.personagem_service import (
    atualizar_ficha_personagem,
    carregar_contexto_ficha,
)
from app.services.pokemon_db_service import (
    carregar_contexto_pokemon,
    equipe_detalhada_db,
)
from app.services.usuario_service import (
    alterar_atividade_usuario,
    criar_jogador_postgresql,
    listar_jogadores_campanha,
)

mestre_bp = Blueprint("mestre", __name__, url_prefix="/mestre")


def _campanha_codigo() -> str:
    return str(current_app.config["CAMPANHA_PADRAO"])


def _dados_banco():
    return listar_jogadores_campanha(campanha_codigo=_campanha_codigo())


@mestre_bp.get("/dashboard")
@perfil_obrigatorio("mestre")
def dashboard():
    try:
        painel = carregar_painel_mestre(campanha_codigo=_campanha_codigo())
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar o painel geral do mestre.")
        flash("Não foi possível carregar os dados da campanha.", "erro")
        return render_template(
            "mestre/dashboard.html",
            campanha={"nome": "Campanha indisponível", "descricao": None},
            resumo={"jogadores": 0, "pokemons": 0, "equipe": 0, "box": 0, "alertas": 0},
            jogadores=[],
            fonte_dados="PostgreSQL",
        ), 503

    return render_template(
        "mestre/dashboard.html",
        campanha=painel.campanha,
        resumo=painel.resumo,
        jogadores=painel.jogadores,
        fonte_dados="PostgreSQL",
    )



@mestre_bp.post("/painel/ordem")
@perfil_obrigatorio("mestre")
def salvar_ordem_painel():
    payload = request.get_json(silent=True) or {}
    ordem = payload.get("ordem")
    if not isinstance(ordem, list) or not all(isinstance(item, str) for item in ordem):
        return jsonify({"erro": "Envie a ordem completa dos jogadores."}), 400
    try:
        resultado = salvar_ordem_jogadores_painel(
            campanha_codigo=_campanha_codigo(),
            personagem_ids=ordem,
            usuario_id=session.get("usuario_id"),
        )
    except ValueError as erro:
        db.session.rollback()
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao salvar a ordem dos jogadores no painel.")
        return jsonify({"erro": "Não foi possível salvar a ordem dos jogadores."}), 503
    return jsonify({"ordem": resultado})



def _delta_pv() -> int | None:
    try:
        delta = int(request.form.get("delta", "0"))
    except (TypeError, ValueError):
        return None
    return delta if -9999 <= delta <= 9999 and delta != 0 else None


@mestre_bp.post("/painel/personagens/<personagem_id>/pv")
@perfil_obrigatorio("mestre")
def ajustar_pv_personagem_painel(personagem_id: str):
    delta = _delta_pv()
    if delta is None:
        return jsonify({"erro": "Ajuste de PV inválido."}), 400
    try:
        resultado = ajustar_pv_personagem(
            campanha_codigo=_campanha_codigo(),
            personagem_id=personagem_id,
            delta=delta,
            usuario_id=session.get("usuario_id"),
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao ajustar PV do personagem pelo painel.")
        return jsonify({"erro": "Não foi possível atualizar os PV."}), 503
    if resultado is None:
        return jsonify({"erro": "Personagem não encontrado."}), 404
    return jsonify(resultado)


@mestre_bp.post("/painel/pokemons/<pokemon_id>/pv")
@perfil_obrigatorio("mestre")
def ajustar_pv_pokemon_painel(pokemon_id: str):
    delta = _delta_pv()
    if delta is None:
        return jsonify({"erro": "Ajuste de PV inválido."}), 400
    try:
        resultado = ajustar_pv_pokemon(
            campanha_codigo=_campanha_codigo(),
            pokemon_id=pokemon_id,
            delta=delta,
            usuario_id=session.get("usuario_id"),
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao ajustar PV do Pokémon pelo painel.")
        return jsonify({"erro": "Não foi possível atualizar os PV."}), 503
    if resultado is None:
        return jsonify({"erro": "Pokémon não encontrado."}), 404
    return jsonify(resultado)


@mestre_bp.get("/jogadores")
@perfil_obrigatorio("mestre")
def jogadores():
    try:
        _, lista = _dados_banco()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao listar jogadores no PostgreSQL.")
        flash("Não foi possível carregar os jogadores.", "erro")
        return render_template(
            "mestre/jogadores.html",
            jogadores=[],
            fonte_dados="PostgreSQL",
        ), 503

    return render_template(
        "mestre/jogadores.html",
        jogadores=lista,
        fonte_dados="PostgreSQL",
    )


def _validar_novo_jogador(nome: str, login: str, senha: str, confirmar: str) -> list[str]:
    erros: list[str] = []
    if not nome:
        erros.append("Informe o nome do jogador.")
    if len(login) < 3:
        erros.append("O usuário deve possuir pelo menos 3 caracteres.")
    if not login.replace("_", "").replace("-", "").isalnum():
        erros.append("Use apenas letras, números, hífen ou sublinhado no usuário.")
    if len(senha) < 6:
        erros.append("A senha inicial deve possuir pelo menos 6 caracteres.")
    if senha != confirmar:
        erros.append("A confirmação de senha não corresponde à senha informada.")
    return erros


@mestre_bp.route("/jogadores/novo", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def novo_jogador():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        login = request.form.get("login", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        erros = _validar_novo_jogador(nome, login, senha, confirmar_senha)

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template(
                "mestre/novo_jogador.html",
                dados={"nome": nome, "login": login},
            ), 400

        try:
            criado = criar_jogador_postgresql(
                campanha_codigo=_campanha_codigo(),
                nome=nome,
                login=login,
                senha=senha,
            )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Falha ao cadastrar jogador no PostgreSQL.")
            flash("Não foi possível cadastrar o jogador no banco de dados.", "erro")
            return render_template(
                "mestre/novo_jogador.html",
                dados={"nome": nome, "login": login},
            ), 503
        except ValueError as erro:
            db.session.rollback()
            flash(str(erro), "erro")
            return render_template(
                "mestre/novo_jogador.html",
                dados={"nome": nome, "login": login},
            ), 400

        flash(f"Jogador {nome} criado com sucesso no PostgreSQL.", "sucesso")
        return redirect(
            url_for("mestre.ficha_jogador", jogador_id=str(criado.personagem.id))
        )

    return render_template("mestre/novo_jogador.html", dados={})


@mestre_bp.post("/usuarios/<usuario_id>/atividade")
@perfil_obrigatorio("mestre")
def atividade_usuario(usuario_id: str):
    ativo = request.form.get("ativo") == "1"
    try:
        usuario = alterar_atividade_usuario(usuario_id, ativo)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao alterar situação do usuário.")
        flash("Não foi possível alterar a situação do usuário.", "erro")
        return redirect(url_for("mestre.jogadores"))

    if usuario is None:
        flash("Usuário não encontrado.", "erro")
    else:
        estado = "ativado" if ativo else "desativado"
        flash(f"Acesso de {usuario.nome} {estado} com sucesso.", "sucesso")
    return redirect(url_for("mestre.jogadores"))


@mestre_bp.get("/jogadores/<jogador_id>/preview")
@perfil_obrigatorio("mestre")
def preview_jogador(jogador_id: str):
    try:
        ficha = carregar_contexto_ficha(
            jogador_id,
            campanha_codigo=_campanha_codigo(),
        )
        contexto_pokemon = carregar_contexto_pokemon(
            jogador_id,
            campanha_codigo=_campanha_codigo(),
        )
        if ficha is None or contexto_pokemon is None:
            flash("A ficha desse jogador não foi encontrada no PostgreSQL.", "erro")
            return redirect(url_for("mestre.dashboard"))
        equipe = equipe_detalhada_db(contexto_pokemon)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar a prévia do jogador.")
        flash("Não foi possível carregar a visualização do jogador.", "erro")
        return redirect(url_for("mestre.dashboard"))

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
        modo_preview_mestre=True,
        preview_personagem_id=str(ficha.personagem.id),
        voltar_painel_url=url_for("mestre.dashboard"),
    )


@mestre_bp.route("/jogadores/<jogador_id>/ficha", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def ficha_jogador(jogador_id: str):
    try:
        contexto = carregar_contexto_ficha(
            jogador_id,
            campanha_codigo=_campanha_codigo(),
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar a ficha no PostgreSQL.")
        flash("Não foi possível carregar a ficha no banco de dados.", "erro")
        return redirect(url_for("mestre.dashboard"))

    if contexto is None:
        flash("A ficha desse jogador não foi encontrada no PostgreSQL.", "erro")
        return redirect(url_for("mestre.dashboard"))

    jogador = contexto.jogador
    if request.method == "POST":
        try:
            jogador, erros = atualizar_ficha_personagem(
                personagem=contexto.personagem,
                formulario=request.form,
                regras=contexto.regras,
                arquivo_foto=request.files.get("foto_arquivo"),
                remover_foto=request.form.get("remover_foto") == "1",
                usuario_responsavel_id=session.get("usuario_id"),
            )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Falha ao salvar a ficha no PostgreSQL.")
            flash("Não foi possível salvar a ficha no banco de dados.", "erro")
            return render_template(
                "jogador/ficha.html",
                jogador=contexto.jogador,
                regras=contexto.regras,
                modo_mestre=True,
                voltar_url=url_for("mestre.dashboard"),
                salvar_url=url_for("mestre.ficha_jogador", jogador_id=jogador_id),
                fonte_ficha="PostgreSQL",
            ), 503

        if erros:
            for erro in erros:
                flash(erro, "erro")
        else:
            flash("Ficha atualizada com sucesso no PostgreSQL.", "sucesso")
            return redirect(url_for("mestre.ficha_jogador", jogador_id=jogador_id))

    return render_template(
        "jogador/ficha.html",
        jogador=jogador,
        regras=contexto.regras,
        modo_mestre=True,
        voltar_url=url_for("mestre.dashboard"),
        salvar_url=url_for("mestre.ficha_jogador", jogador_id=jogador_id),
        fonte_ficha="PostgreSQL",
    )
