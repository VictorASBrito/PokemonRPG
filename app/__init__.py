from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, session, url_for

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

    db.init_app(app)
    migrate.init_app(app, db)

    # Garante que todos os modelos relacionais façam parte do metadata usado
    # pelo Alembic. Os JSON permanecem apenas como fonte de importação legada.
    from app import models as _models  # noqa: F401

    from app.commands import banco_cli, dados_cli, usuarios_cli, ficha_cli, pokemon_cli
    from app.routes.auth import auth_bp
    from app.routes.boxes import boxes_bp
    from app.routes.jogadores import jogadores_bp
    from app.routes.mestre import mestre_bp
    from app.routes.pokemons import pokemons_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(jogadores_bp)
    app.register_blueprint(mestre_bp)
    app.register_blueprint(pokemons_bp)
    app.register_blueprint(boxes_bp)
    app.register_blueprint(banco_cli, cli_group=None)
    app.register_blueprint(dados_cli, cli_group=None)
    app.register_blueprint(usuarios_cli, cli_group=None)
    app.register_blueprint(ficha_cli, cli_group=None)
    app.register_blueprint(pokemon_cli, cli_group=None)

    @app.get("/")
    def inicio():
        if not session.get("usuario_id"):
            return redirect(url_for("auth.login"))

        if session.get("perfil") == "mestre":
            return redirect(url_for("mestre.dashboard"))

        return redirect(url_for("jogadores.dashboard"))

    return app
