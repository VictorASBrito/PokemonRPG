from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models.db import Pokemon


def test_dashboard_exibe_treinador_e_equipe_do_postgresql(app_db, client_db) -> None:
    # Cria um Pokémon pela área do mestre.
    assert client_db.post(
        "/login", data={"login": "mestre-db", "senha": "senha-db"}
    ).status_code == 302
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica",
        data={"especie_nome": "Bulbasaur"},
    ).status_code == 302

    with app_db.app_context():
        pokemon = db.session.execute(select(Pokemon)).scalar_one()
        pokemon_id = str(pokemon.id)

    assert client_db.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": pokemon_id, "destino": "equipe"},
    ).status_code == 302
    client_db.post("/logout")

    assert client_db.post(
        "/login", data={"login": "bartz-db", "senha": "abc123"}
    ).status_code == 302
    resposta = client_db.get("/jogador/dashboard")
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Painel de Bartz" in texto
    assert "Victor" in texto
    assert "Nível" in texto
    assert "48" in texto
    assert "Bulbasaur" in texto
    assert "Atributos base" in texto
    assert "PostgreSQL" not in texto  # informação técnica não precisa aparecer no painel
