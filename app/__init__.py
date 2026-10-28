from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, request, session, url_for

from app.config import Config
from app.extensions import db, migrate


def create_app() -> Flask:
    load_dotenv()

    raiz = Path(__file__).resolve().parent.parent

    app = Flask(
        __name__,
        template_folder=str(raiz / "templates"),
        static_folder=str(raiz / "static"),
    )

    Config(raiz).aplicar(app)
    from app.services.tipos_visual import tipo_visual
    app.jinja_env.filters["tipo_visual"] = tipo_visual

    db.init_app(app)
    migrate.init_app(app, db)

    # Garante que todos os modelos relacionais façam parte do metadata usado
    # pelo Alembic. Os JSON permanecem apenas como fonte de importação legada.
    from app import models as _models  # noqa: F401

    from app.commands import banco_cli, dados_cli, usuarios_cli, ficha_cli, pokemon_cli, catalogo_cli, inventario_cli, midia_cli, planilhas_jogadores_cli, ankar_cli
    from app.routes.auth import auth_bp
    from app.routes.catalogo_admin import catalogo_admin_bp
    from app.routes.capturas import capturas_bp
    from app.routes.combates import combates_bp
    from app.routes.boxes import boxes_bp
    from app.routes.regiao import regiao_bp
    from app.routes.jogadores import jogadores_bp
    from app.routes.inventario import inventario_bp
    from app.routes.mestre import mestre_bp
    from app.routes.pokemons import pokemons_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(catalogo_admin_bp)
    app.register_blueprint(capturas_bp)
    app.register_blueprint(combates_bp)
    app.register_blueprint(jogadores_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(mestre_bp)
    app.register_blueprint(pokemons_bp)
    app.register_blueprint(boxes_bp)
    app.register_blueprint(regiao_bp)
    app.register_blueprint(banco_cli, cli_group=None)
    app.register_blueprint(dados_cli, cli_group=None)
    app.register_blueprint(usuarios_cli, cli_group=None)
    app.register_blueprint(ficha_cli, cli_group=None)
    app.register_blueprint(pokemon_cli, cli_group=None)
    app.register_blueprint(catalogo_cli, cli_group=None)
    app.register_blueprint(inventario_cli, cli_group=None)
    app.register_blueprint(midia_cli, cli_group=None)
    app.register_blueprint(planilhas_jogadores_cli, cli_group=None)
    app.register_blueprint(ankar_cli, cli_group=None)

    @app.before_request
    def exigir_troca_senha():
        if session.get("deve_alterar_senha") and request.endpoint not in {
            "auth.trocar_senha", "auth.logout", "static",
        }:
            return redirect(url_for("auth.trocar_senha"))

    @app.errorhandler(413)
    def requisicao_muito_grande(_erro):
        flash(
            "O envio excedeu o limite permitido. Cada imagem pode ter até "
            f"{app.config['UPLOAD_IMAGEM_MAX_BYTES'] // (1024 * 1024)} MB.",
            "erro",
        )
        return redirect(request.referrer or url_for("inicio"))

    @app.get("/")
    def inicio():
        if not session.get("usuario_id"):
            return redirect(url_for("auth.login"))

        if session.get("perfil") == "mestre":
            return redirect(url_for("mestre.dashboard"))

        return redirect(url_for("jogadores.dashboard"))

    return app
