from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar
from urllib.parse import urljoin, urlparse

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
from app.services.auth_service import autenticar_usuario
from app.services.compatibilidade_legado import buscar_id_jogador_legado
from app.services.json_service import ler_json
from app.services.senha_service import gerar_hash_senha, verificar_senha

auth_bp = Blueprint("auth", __name__)
F = TypeVar("F", bound=Callable)


def login_obrigatorio(view: F) -> F:
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("usuario_id"):
            flash("Entre com seu usuário para continuar.", "aviso")
            return redirect(url_for("auth.login", proxima=request.path))
        return view(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def perfil_obrigatorio(perfil: str):
    def decorador(view: F) -> F:
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not session.get("usuario_id"):
                return redirect(url_for("auth.login"))
            if session.get("perfil") != perfil:
                flash("Seu usuário não possui acesso a essa área.", "erro")
                return redirect(url_for("inicio"))
            return view(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorador


def _destino_seguro(destino: str | None) -> str | None:
    if not destino:
        return None
    base = urlparse(request.host_url)
    alvo = urlparse(urljoin(request.host_url, destino))
    if alvo.scheme in {"http", "https"} and alvo.netloc == base.netloc:
        return alvo.path + (f"?{alvo.query}" if alvo.query else "")
    return None


def _login_legado_para_testes(login: str, senha: str) -> dict | None:
    """Mantém os testes antigos isolados enquanto eles ainda usam JSON.

    Em execução normal esta função nunca é usada: falhas de banco não fazem o
    sistema voltar silenciosamente ao JSON.
    """
    if not current_app.testing:
        return None

    caminho = Path(current_app.config["DATA_DIR"]) / "usuarios.json"
    dados = ler_json(caminho, {"usuarios": []})
    usuario = next(
        (
            item
            for item in dados.get("usuarios", [])
            if item.get("login", "").lower() == login and item.get("ativo", True)
        ),
        None,
    )
    if not usuario or not verificar_senha(senha, usuario.get("senha_hash", "")):
        return None
    return usuario


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("usuario_id"):
        return redirect(url_for("inicio"))

    if request.method == "POST":
        login_informado = request.form.get("login", "").strip().lower()
        senha = request.form.get("senha", "")

        try:
            resultado = autenticar_usuario(
                login_informado,
                senha,
                str(current_app.config["CAMPANHA_PADRAO"]),
            )
        except SQLAlchemyError:
            db.session.rollback()
            usuario_legado = _login_legado_para_testes(login_informado, senha)
            if usuario_legado is None:
                current_app.logger.exception("Falha ao consultar usuários no PostgreSQL.")
                flash(
                    "Não foi possível acessar o banco de dados. Tente novamente em instantes.",
                    "erro",
                )
                return render_template("login.html", login=login_informado), 503

            session.clear()
            session["usuario_id"] = usuario_legado["id"]
            session["nome"] = usuario_legado.get("nome", usuario_legado["login"])
            session["perfil"] = usuario_legado.get("perfil", "jogador")
            session["jogador_id"] = usuario_legado.get("jogador_id")
            return redirect(url_for("inicio"))

        if resultado is None:
            flash("Usuário ou senha inválidos.", "erro")
            return render_template("login.html", login=login_informado), 401

        usuario = resultado.usuario
        campanha_codigo = str(current_app.config["CAMPANHA_PADRAO"])
        jogador_id_legado = None
        if resultado.perfil_sessao == "jogador":
            jogador_id_legado = buscar_id_jogador_legado(
                current_app.config["DATA_DIR"],
                campanha_codigo,
                usuario.id,
            )

        session.clear()
        session["usuario_id"] = str(usuario.id)
        session["nome"] = usuario.nome
        session["perfil"] = resultado.perfil_sessao
        session["campanha_id"] = (
            str(resultado.campanha.id) if resultado.campanha is not None else None
        )
        session["personagem_id"] = (
            str(resultado.personagem.id) if resultado.personagem is not None else None
        )
        # Ponte temporária para as telas que ainda leem JSON.
        session["jogador_id"] = jogador_id_legado

        destino = _destino_seguro(request.args.get("proxima"))
        return redirect(destino or url_for("inicio"))

    return render_template("login.html")


@auth_bp.post("/logout")
@login_obrigatorio
def logout():
    session.clear()
    flash("Sessão encerrada.", "sucesso")
    return redirect(url_for("auth.login"))
