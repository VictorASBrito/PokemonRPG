"""Flask real em porta efêmera e banco SQLite isolado para o Playwright.

Nunca inicia o servidor da campanha nem usa o túnel/credenciais de produção.
"""
from __future__ import annotations

import json
import threading
import uuid

import pytest
from werkzeug.serving import make_server

from app.extensions import db
from app.models.db import FormaPokemon, Pokemon


@pytest.fixture()
def app_visual(app_db, tmp_path):
    # Um sprite de verdade, pertencente ao login fictício da fixture app_db.
    configuracao = tmp_path / "entrada_personagens_visual.json"
    configuracao.write_text(
        json.dumps(
            {
                "habilitado": True,
                "slots": [
                    {
                        "login": "bartz-db" if numero == 1 else f"visual-vazio-{numero}",
                        "sprite": f"img/login-personagens/slot-{numero:02}.png",
                    }
                    for numero in range(1, 10)
                ],
            }
        ),
        encoding="utf-8",
    )
    app_db.config["LOGIN_PERSONAGENS_ARQUIVO"] = str(configuracao)

    # O painel expandido precisa de ao menos um Pokémon da equipe.
    with app_db.app_context():
        forma = db.session.get(
            FormaPokemon, uuid.UUID(app_db.config["TEST_IDS"]["formas"]["bulbasaur"])
        )
        assert forma is not None
        # A fixture geral aponta para https://img/..., URL fictícia usada
        # em testes de serviço. Para verificar imagem em navegador real,
        # utilizar os sprites locais versionados do repositório.
        forma.imagem_url = "/static/img/pokemon-hd/bulbasaur.png"
        forma.imagem_shiny_url = "/static/img/pokemon-hd/bulbasaur-shiny.png"

        pokemon = Pokemon(
            personagem_id=uuid.UUID(app_db.config["TEST_IDS"]["personagem"]),
            forma_pokemon_id=uuid.UUID(
                app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
            ),
            apelido="Parceiro visual",
            genero="Macho",
            pv_atual=30,
            localizacao="equipe",
            posicao=1,
            ativo=True,
        )
        db.session.add(pokemon)
        db.session.commit()

    return app_db


@pytest.fixture()
def live_site_url(app_visual):
    servidor = make_server("127.0.0.1", 0, app_visual, threaded=True)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{servidor.server_port}"
    finally:
        servidor.shutdown()
        thread.join(timeout=10)
        servidor.server_close()
