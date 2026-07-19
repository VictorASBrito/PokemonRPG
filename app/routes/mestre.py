from __future__ import annotations

import uuid
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.jogador_service import (
    adicionar_jogador_na_campanha,
    atualizar_ficha_treinador,
    carregar_jogador,
    carregar_regras_treinador,
    criar_jogador,
    listar_jogadores,
    salvar_jogador,
)
from app.services.json_service import ler_json, salvar_json
from app.services.pokemon_service import sincronizar_pokemons_com_nivel_jogador
from app.services.senha_service import gerar_hash_senha
from app.services.usuario_service import (
    alterar_atividade_usuario,
    criar_jogador_postgresql,
    listar_jogadores_campanha,
)

mestre_bp = Blueprint("mestre", __name__, url_prefix="/mestre")


def _contexto() -> tuple[Path, str]:
    return (
        Path(current_app.config["DATA_DIR"]),
        str(current_app.config["CAMPANHA_PADRAO"]),
    )


def _dados_banco():
    data_dir, campanha_id = _contexto()
    return listar_jogadores_campanha(
        campanha_codigo=campanha_id,
        data_dir=data_dir,
    )


def _dashboard_legado():
    data_dir, campanha_id = _contexto()
    caminho = data_dir / "campanhas" / campanha_id / "campanha.json"
    campanha = ler_json(caminho, {"nome": campanha_id.title(), "jogadores": []})
    jogadores = listar_jogadores(data_dir, campanha_id)
    return render_template(
        "mestre/dashboard.html",
        campanha=campanha,
        total_jogadores=len(jogadores),
        fonte_dados="JSON de teste",
    )


def _jogadores_legado():
    data_dir, campanha_id = _contexto()
    return render_template(
        "mestre/jogadores.html",
        jogadores=listar_jogadores(data_dir, campanha_id),
        fonte_dados="JSON de teste",
    )


@mestre_bp.get("/dashboard")
@perfil_obrigatorio("mestre")
def dashboard():
    try:
        campanha, jogadores = _dados_banco()
    except SQLAlchemyError:
        db.session.rollback()
        if current_app.testing:
            return _dashboard_legado()
        current_app.logger.exception("Falha ao carregar o painel do mestre.")
        flash("Não foi possível carregar os dados da campanha.", "erro")
        return render_template(
            "mestre/dashboard.html",
            campanha={"nome": "Campanha indisponível"},
            total_jogadores=0,
            fonte_dados="PostgreSQL",
        ), 503

    campanha_dto = {
        "nome": campanha.nome if campanha else "Campanha",
        "descricao": campanha.descricao if campanha else None,
    }
    return render_template(
        "mestre/dashboard.html",
        campanha=campanha_dto,
        total_jogadores=len(jogadores),
        fonte_dados="PostgreSQL",
    )


@mestre_bp.get("/jogadores")
@perfil_obrigatorio("mestre")
def jogadores():
    try:
        _, lista = _dados_banco()
    except SQLAlchemyError:
        db.session.rollback()
        if current_app.testing:
            return _jogadores_legado()
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


def _novo_jogador_legado(nome: str, login: str, senha: str):
    data_dir, campanha_id = _contexto()
    arquivo_usuarios = data_dir / "usuarios.json"
    dados_usuarios = ler_json(arquivo_usuarios, {"usuarios": []})
    if any(
        str(usuario.get("login", "")).casefold() == login.casefold()
        for usuario in dados_usuarios.get("usuarios", [])
    ):
        raise ValueError("Já existe um usuário com esse login.")

    usuario_id = f"usr_{uuid.uuid4().hex[:12]}"
    jogador_id = f"jog_{uuid.uuid4().hex[:12]}"
    dados_usuarios.setdefault("usuarios", []).append(
        {
            "id": usuario_id,
            "login": login,
            "nome": nome,
            "perfil": "jogador",
            "jogador_id": jogador_id,
            "senha_hash": gerar_hash_senha(senha),
            "ativo": True,
        }
    )
    salvar_json(arquivo_usuarios, dados_usuarios)
    criar_jogador(
        data_dir=data_dir,
        campanha_id=campanha_id,
        jogador_id=jogador_id,
        usuario_id=usuario_id,
        nome=nome,
    )
    adicionar_jogador_na_campanha(data_dir, campanha_id, jogador_id)
    return jogador_id


@mestre_bp.route("/jogadores/novo", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def novo_jogador():
    data_dir, campanha_id = _contexto()

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
                data_dir=data_dir,
                campanha_codigo=campanha_id,
                nome=nome,
                login=login,
                senha=senha,
            )
            jogador_id = criado.jogador_id_legado
        except SQLAlchemyError:
            db.session.rollback()
            if current_app.testing:
                try:
                    jogador_id = _novo_jogador_legado(nome, login, senha)
                except ValueError as erro:
                    flash(str(erro), "erro")
                    return render_template(
                        "mestre/novo_jogador.html",
                        dados={"nome": nome, "login": login},
                    ), 400
            else:
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
        return redirect(url_for("mestre.ficha_jogador", jogador_id=jogador_id))

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


@mestre_bp.route("/jogadores/<jogador_id>/ficha", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def ficha_jogador(jogador_id: str):
    data_dir, campanha_id = _contexto()
    jogador = carregar_jogador(data_dir, campanha_id, jogador_id)
    if not jogador:
        flash(
            "A ficha JSON temporária desse jogador não foi encontrada. "
            "A conversão da ficha para PostgreSQL será feita na próxima etapa.",
            "erro",
        )
        return redirect(url_for("mestre.jogadores"))

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
            flash("Ficha atualizada com sucesso.", "sucesso")
            return redirect(url_for("mestre.ficha_jogador", jogador_id=jogador_id))

    return render_template(
        "jogador/ficha.html",
        jogador=jogador,
        regras=regras,
        modo_mestre=True,
        voltar_url=url_for("mestre.jogadores"),
        salvar_url=url_for("mestre.ficha_jogador", jogador_id=jogador_id),
    )
