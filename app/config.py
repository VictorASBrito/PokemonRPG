from __future__ import annotations

import os
from pathlib import Path


class Config:
    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz

    def aplicar(self, app) -> None:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://pokemon_rpg:troque_a_senha@localhost:5432/pokemon_rpg",
        )

        app.config.update(
            SECRET_KEY=os.getenv(
                "POKEMON_RPG_SECRET_KEY",
                "troque-esta-chave-em-producao",
            ),
            SQLALCHEMY_DATABASE_URI=database_url,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "pool_pre_ping": True,
                "pool_recycle": 1800,
            },
            DATA_DIR=self.raiz / "data",
            CAMPANHA_PADRAO=os.getenv("POKEMON_RPG_CAMPANHA", "ankar"),
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
        )
