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

from app.routes.auth import gerar_hash_senha, perfil_obrigatorio
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

mestre_bp = Blueprint("mestre", __name__, url_prefix="/mestre")


def _contexto() -> tuple[Path, str]:
    return (
        Path(current_app.config["DATA_DIR"]),
        str(current_app.config["CAMPANHA_PADRAO"]),
    )


@mestre_bp.get("/dashboard")
@perfil_obrigatorio("mestre")
def dashboard():
    data_dir, campanha_id = _contexto()
    caminho = data_dir / "campanhas" / campanha_id / "campanha.json"
    campanha = ler_json(caminho, {"nome": campanha_id.title(), "jogadores": []})
    jogadores = listar_jogadores(data_dir, campanha_id)
    return render_template(
        "mestre/dashboard.html",
        campanha=campanha,
        total_jogadores=len(jogadores),
    )


@mestre_bp.get("/jogadores")
@perfil_obrigatorio("mestre")
def jogadores():
    data_dir, campanha_id = _contexto()
    return render_template(
        "mestre/jogadores.html",
        jogadores=listar_jogadores(data_dir, campanha_id),
    )


@mestre_bp.route("/jogadores/novo", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def novo_jogador():
    data_dir, campanha_id = _contexto()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        login = request.form.get("login", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        erros: list[str] = []

        if not nome:
            erros.append("Informe o nome do jogador ou treinador.")
        if len(login) < 3:
            erros.append("O usuário deve possuir pelo menos 3 caracteres.")
        if not login.replace("_", "").replace("-", "").isalnum():
            erros.append("Use apenas letras, números, hífen ou sublinhado no usuário.")
        if len(senha) < 6:
            erros.append("A senha inicial deve possuir pelo menos 6 caracteres.")
        if senha != confirmar_senha:
            erros.append("A confirmação de senha não corresponde à senha informada.")

        arquivo_usuarios = data_dir / "usuarios.json"
        dados_usuarios = ler_json(arquivo_usuarios, {"usuarios": []})
        if any(
            str(usuario.get("login", "")).casefold() == login.casefold()
            for usuario in dados_usuarios.get("usuarios", [])
        ):
            erros.append("Já existe um usuário com esse login.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template(
                "mestre/novo_jogador.html",
                dados={"nome": nome, "login": login},
            ), 400

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

        flash(f"Jogador {nome} criado com sucesso.", "sucesso")
        return redirect(url_for("mestre.ficha_jogador", jogador_id=jogador_id))

    return render_template("mestre/novo_jogador.html", dados={})


@mestre_bp.route("/jogadores/<jogador_id>/ficha", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def ficha_jogador(jogador_id: str):
    data_dir, campanha_id = _contexto()
    jogador = carregar_jogador(data_dir, campanha_id, jogador_id)
    if not jogador:
        flash("Jogador não encontrado.", "erro")
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
