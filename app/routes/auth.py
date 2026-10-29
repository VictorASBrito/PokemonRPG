from __future__ import annotations

from functools import wraps
import hmac
import secrets
import uuid
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
from app.services.senha_service import gerar_hash_senha, verificar_senha
from app.models.db import Usuario

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
            from app.services.permissoes_service import (
                PERFIS_JOGADOR, PERFIS_MESTRE, perfil_usuario_atual,
            )
            nivel_banco = perfil_usuario_atual(session.get("usuario_id"))
            permitidos = PERFIS_MESTRE if perfil == "mestre" else PERFIS_JOGADOR
            if session.get("perfil") != perfil or nivel_banco not in permitidos:
                flash("Seu usuário não possui acesso a essa área.", "erro")
                session.clear()
                return redirect(url_for("auth.login"))
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



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and session.get("usuario_id"):
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
            current_app.logger.exception("Falha ao consultar usuários no PostgreSQL.")
            flash(
                "Não foi possível acessar o banco de dados. Tente novamente em instantes.",
                "erro",
            )
            return render_template("login.html", login=login_informado), 503

        if resultado is None:
            flash("Usuário ou senha inválidos.", "erro")
            return render_template("login.html", login=login_informado), 401

        usuario = resultado.usuario
        session.clear()
        session["usuario_id"] = str(usuario.id)
        session["nome"] = usuario.nome
        session["perfil"] = resultado.perfil_sessao
        session["perfil_conta"] = usuario.perfil
        session["campanha_id"] = (
            str(resultado.campanha.id) if resultado.campanha is not None else None
        )
        session["personagem_id"] = (
            str(resultado.personagem.id) if resultado.personagem is not None else None
        )
        # A senha 12345 foi solicitada apenas como credencial temporária.
        # Jogadores devem trocá-la no primeiro acesso público.
        if usuario.perfil in {"jogador", "tester"} and senha == "12345":
            session["deve_alterar_senha"] = True
            return redirect(url_for("auth.trocar_senha"))
        destino = _destino_seguro(request.args.get("proxima"))
        return redirect(destino or url_for("inicio"))

    # ENTRADA_PERSONAGENS_10B1: GET visual; POST de usuário/senha preservado.
    from app.services.entrada_personagens_service import listar_slots_visuais, slots_vazios
    try:
        slots = listar_slots_visuais(campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao listar personagens na entrada visual.")
        slots = slots_vazios()
    return render_template(
        "entrada_personagens.html",
        slots=slots,
        entrada_csrf=session.setdefault("entrada_personagens_csrf", secrets.token_urlsafe(32)),
    )


@auth_bp.post("/logout")
@login_obrigatorio
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/conta/senha", methods=["GET", "POST"])
@login_obrigatorio
def trocar_senha():
    """Permite trocar a senha pessoal, inclusive no primeiro acesso."""
    token = session.setdefault("troca_senha_token", secrets.token_urlsafe(32))
    if request.method == "POST":
        enviado = request.form.get("csrf_token", "")
        if not hmac.compare_digest(token, enviado):
            flash("Formulário expirado. Atualize a página e tente novamente.", "erro")
            return render_template("conta/trocar_senha.html", token=token), 400
        atual = request.form.get("senha_atual", "")
        nova = request.form.get("senha_nova", "")
        confirmar = request.form.get("confirmar_senha", "")
        usuario = db.session.get(Usuario, uuid.UUID(session["usuario_id"]))
        if usuario is None or not verificar_senha(atual, usuario.senha_hash):
            flash("Senha atual incorreta.", "erro")
        elif len(nova) < 10 or nova == "12345":
            flash("Escolha uma senha nova com pelo menos 10 caracteres.", "erro")
        elif nova != confirmar:
            flash("A confirmação da senha não corresponde.", "erro")
        else:
            usuario.senha_hash = gerar_hash_senha(nova)
            db.session.commit()
            session.pop("deve_alterar_senha", None)
            session.pop("troca_senha_token", None)
            flash("Sua senha foi atualizada com sucesso.", "sucesso")
            return redirect(url_for("inicio"))
    return render_template("conta/trocar_senha.html", token=token)
