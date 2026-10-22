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
        upload_imagem_max_bytes = int(
            os.getenv("POKEMON_RPG_UPLOAD_IMAGEM_MAX_BYTES", str(8 * 1024 * 1024))
        )
        teste_remoto = os.getenv("POKEMON_RPG_TESTE_REMOTO", "").strip().lower() in {
            "1", "true", "sim", "yes"
        }
        # Um túnel rápido publica um subdomínio novo de trycloudflare.com a cada sessão.
        # O modo local não restringe hosts para preservar os testes e ferramentas existentes.
        hosts_adicionais = [
            host.strip()
            for host in os.getenv("POKEMON_RPG_HOSTS_ADICIONAIS", "").split(",")
            if host.strip()
        ]
        hosts_permitidos = (
            ["127.0.0.1", "localhost", ".trycloudflare.com", *hosts_adicionais]
            if teste_remoto
            else None
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
            UPLOAD_IMAGENS_DIR=self.raiz / "static" / "uploads",
            UPLOAD_IMAGEM_MAX_BYTES=upload_imagem_max_bytes,
            # O formulário de uma forma Pokémon pode enviar duas imagens de uma vez.
            MAX_CONTENT_LENGTH=max(20 * 1024 * 1024, upload_imagem_max_bytes * 2 + 1024 * 1024),
            CAMPANHA_PADRAO=os.getenv("POKEMON_RPG_CAMPANHA", "ankar"),
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
            SESSION_COOKIE_SECURE=teste_remoto,
            PREFERRED_URL_SCHEME="https" if teste_remoto else "http",
            TRUSTED_HOSTS=hosts_permitidos,
        )
