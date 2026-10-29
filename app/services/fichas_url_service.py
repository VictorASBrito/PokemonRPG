"""Uma identidade isolada por URL de jogador, sem trocar a sessão das outras abas.

As nove contas configuradas na entrada visual podem usar /p/<login>/.
Somente os endpoints explicitamente permitidos do jogador são expostos nesse
contexto. O perfil é revalidado no PostgreSQL em cada requisição.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import quote

from flask import abort, current_app, g, redirect, request, session
from flask.sessions import SecureCookieSessionInterface
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.services.entrada_personagens_service import configuracao_login, personagem_para_entrada
from app.services.fichas_url_middleware import FichasURLMiddleware

LOGIN_VALIDO = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}$")

# A área do mestre e ações administrativas nunca entram pela URL de jogador.
ENDPOINTS_JOGADOR = frozenset({
    "inicio", "static", "auth.logout",
    "jogadores.dashboard", "jogadores.ficha",
    "pokemons.autocomplete_formas", "pokemons.autocomplete_golpes",
    "pokemons.equipe_jogador", "pokemons.novo_jogador",
    "pokemons.editar_jogador", "pokemons.excluir_jogador",
    "boxes.boxes_jogador", "boxes.mover_jogador", "boxes.renomear_jogador",
    "inventario.inventario_jogador", "inventario.usar_jogador",
    "inventario.equipar_jogador", "inventario.desequipar_jogador",
    "inventario.transferir_jogador",
    "combates.painel", "combates.estado", "combates.posicionar",
    "combates.retirar",
    "capturas.campo_jogador",
})


def url_selecao() -> str:
    """Volta à entrada visual sem herdar /p/<login> do SCRIPT_NAME."""
    return str(request.environ.get("ANKAR_SCRIPT_ROOT_ORIGINAL") or "") + "/selecionar"


def url_ficha_de_login(login: str) -> str:
    login = str(login).strip().lower()
    if not LOGIN_VALIDO.fullmatch(login):
        raise ValueError("Login incompatível com URL pública. Use letras minúsculas, números, _ ou -.")
    raiz = str(request.environ.get("ANKAR_SCRIPT_ROOT_ORIGINAL", request.script_root) or "").rstrip("/")
    return raiz + "/p/" + quote(login, safe="") + "/"


class SessaoPorFichaURL(SecureCookieSessionInterface):
    """Cada /p/login tem cookie próprio, separado da sessão principal do site."""

    def get_cookie_name(self, app):
        login = request.environ.get("ANKAR_FICHA_LOGIN")
        if login:
            codigo = hashlib.sha256(login.encode("utf-8")).hexdigest()[:20]
            return "ankar_ficha_" + codigo
        return super().get_cookie_name(app)

    def get_cookie_path(self, app):
        if request.environ.get("ANKAR_FICHA_LOGIN"):
            return request.script_root or "/"
        return super().get_cookie_path(app)


def _identificar_personagem_da_url() -> None:
    login = request.environ.get("ANKAR_FICHA_LOGIN")
    if not login:
        return
    if request.endpoint not in ENDPOINTS_JOGADOR:
        abort(404)
    if request.endpoint == "static":
        return

    configurados = configuracao_login()
    indice = next((i + 1 for i, item in enumerate(configurados) if item["login"] == login), None)
    if indice is None:
        abort(404)

    try:
        resultado = personagem_para_entrada(
            indice, campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"])
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao identificar personagem na URL.")
        abort(503)
    if resultado is None:
        abort(404)

    # 10B.3.1: finalizar apenas o cookie isolado da ficha. A sessão
    # tradicional em / (incluindo Mestre) não é acessada ou modificada.
    if request.endpoint == "auth.logout":
        session.clear()
        return redirect(url_selecao(), code=303)

    usuario, personagem, campanha = resultado
    # Se a vinculação dos slots mudar, nunca aproveitamos a identidade antiga.
    identidade = str(usuario.id)
    if session.get("usuario_id") != identidade or session.get("personagem_id") != str(personagem.id):
        session.clear()
    session["usuario_id"] = identidade
    session["nome"] = usuario.nome
    session["perfil"] = "jogador"
    session["perfil_conta"] = "jogador"
    session["campanha_id"] = str(campanha.id)
    session["personagem_id"] = str(personagem.id)
    session["entrada_visual"] = True
    session.pop("deve_alterar_senha", None)
    g.ficha_por_url = True
    g.ficha_url_login = login


def instalar_fichas_por_url(app) -> None:
    """Instala uma vez, antes das funções before_request normais do projeto."""
    if getattr(app, "_ankar_fichas_url_instalado", False):
        return
    if not isinstance(app.session_interface, SecureCookieSessionInterface):
        raise RuntimeError("Sessão Flask personalizada: revisar integração de fichas por URL.")
    app.session_interface = SessaoPorFichaURL()
    app.wsgi_app = FichasURLMiddleware(app.wsgi_app)
    app.before_request(_identificar_personagem_da_url)
    app._ankar_fichas_url_instalado = True
