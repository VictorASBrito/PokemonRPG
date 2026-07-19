from __future__ import annotations

import hashlib
import hmac
import secrets
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

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

from app.services.json_service import ler_json

auth_bp = Blueprint("auth", __name__)
F = TypeVar("F", bound=Callable)



def gerar_hash_senha(senha: str, iteracoes: int = 600_000) -> str:
    salt = secrets.token_hex(16)
    hash_senha = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        iteracoes,
    ).hex()
    return f"pbkdf2_sha256${iteracoes}${salt}${hash_senha}"

def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        algoritmo, iteracoes, salt, hash_esperado = senha_hash.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False

        hash_recebido = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt.encode("utf-8"),
            int(iteracoes),
        ).hex()
        return hmac.compare_digest(hash_recebido, hash_esperado)
    except (TypeError, ValueError):
        return False


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


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("usuario_id"):
        return redirect(url_for("inicio"))

    if request.method == "POST":
        login_informado = request.form.get("login", "").strip().lower()
        senha = request.form.get("senha", "")

        caminho = Path(current_app.config["DATA_DIR"]) / "usuarios.json"
        dados = ler_json(caminho, {"usuarios": []})

        usuario = next(
            (
                item
                for item in dados.get("usuarios", [])
                if item.get("login", "").lower() == login_informado
                and item.get("ativo", True)
            ),
            None,
        )

        if not usuario or not verificar_senha(senha, usuario.get("senha_hash", "")):
            flash("Usuário ou senha inválidos.", "erro")
            return render_template("login.html", login=login_informado), 401

        session.clear()
        session["usuario_id"] = usuario["id"]
        session["nome"] = usuario.get("nome", usuario["login"])
        session["perfil"] = usuario.get("perfil", "jogador")
        session["jogador_id"] = usuario.get("jogador_id")

        return redirect(url_for("inicio"))

    return render_template("login.html")


@auth_bp.post("/logout")
@login_obrigatorio
def logout():
    session.clear()
    flash("Sessão encerrada.", "sucesso")
    return redirect(url_for("auth.login"))
