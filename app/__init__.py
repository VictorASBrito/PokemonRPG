from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, redirect, session, url_for


def create_app() -> Flask:
    raiz = Path(__file__).resolve().parent.parent

    app = Flask(
        __name__,
        template_folder=str(raiz / "templates"),
        static_folder=str(raiz / "static"),
    )

    app.config.update(
        SECRET_KEY=os.getenv("POKEMON_RPG_SECRET_KEY", "troque-esta-chave-em-producao"),
        DATA_DIR=raiz / "data",
        CAMPANHA_PADRAO=os.getenv("POKEMON_RPG_CAMPANHA", "ankar"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

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

    @app.get("/")
    def inicio():
        if not session.get("usuario_id"):
            return redirect(url_for("auth.login"))

        if session.get("perfil") == "mestre":
            return redirect(url_for("mestre.dashboard"))

        return redirect(url_for("jogadores.dashboard"))

    return app
