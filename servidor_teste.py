"""Servidor HTTP local para testes externos através do Cloudflare Tunnel.

Execute na pasta do projeto: python servidor_teste.py
O processo fica acessível SOMENTE a partir de 127.0.0.1:5000.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from waitress import serve


def main() -> int:
    load_dotenv()
    chave = os.getenv("POKEMON_RPG_SECRET_KEY", "").strip()
    if len(chave) < 32 or chave == "troque-por-uma-chave-grande-e-aleatoria":
        print(
            "[ERRO] Configure POKEMON_RPG_SECRET_KEY no .env com "
            "uma chave aleatória de pelo menos 32 caracteres.\n"
            'Para gerar: python -c "import secrets; print(secrets.token_urlsafe(48))"',
            file=sys.stderr,
        )
        return 2

    os.environ["POKEMON_RPG_TESTE_REMOTO"] = "1"
    os.environ.pop("FLASK_DEBUG", None)

    from app import create_app

    aplicativo = create_app()
    print("[Pokémon RPG] Servidor de teste ativo SOMENTE em http://127.0.0.1:5000")
    print("[Pokémon RPG] Abra um SEGUNDO terminal para executar scripts/2_tunel_cloudflare.ps1")
    print("[Pokémon RPG] O acesso dos jogadores será feito pela URL HTTPS do túnel.")
    serve(aplicativo, host="127.0.0.1", port=5000, threads=8)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
