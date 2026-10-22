"""Execução local. Para compartilhar com jogadores, use servidor_teste.py."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Não publique o debugger interativo do Flask pela Internet.
    # Quem executar o aplicativo localmente ainda pode optar por FLASK_DEBUG=1.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "").strip() == "1",
    )
