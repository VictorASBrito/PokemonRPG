from __future__ import annotations

import json
import shutil
from pathlib import Path

from app import create_app


def test_dashboard_exibe_treinador_e_equipe(tmp_path: Path) -> None:
    origem_dados = Path(__file__).resolve().parent.parent / "data"
    data_dir = tmp_path / "data"
    shutil.copytree(origem_dados, data_dir)

    app = create_app()
    app.config.update(TESTING=True, DATA_DIR=data_dir, SECRET_KEY="teste")
    client = app.test_client()

    assert client.post(
        "/login", data={"login": "mestre", "senha": "mestre123"}
    ).status_code == 302
    assert client.post(
        "/mestre/jogadores/novo",
        data={
            "nome": "Victor",
            "login": "victor",
            "senha": "abc123",
            "confirmar_senha": "abc123",
        },
    ).status_code == 302

    usuarios = json.loads((data_dir / "usuarios.json").read_text(encoding="utf-8"))
    jogador_id = next(
        item["jogador_id"]
        for item in usuarios["usuarios"]
        if item["login"] == "victor"
    )

    assert client.post(
        f"/mestre/jogadores/{jogador_id}/ficha",
        data={
            "nome": "Victor",
            "nivel": "48",
            "idade": "20",
            "genero": "Masculino",
            "origem": "Atleta",
            "classe": "Treinador(a)",
            "estilo_combate": "Agressivo",
            "numeros_shiny": "7",
            "pokedolares": "100",
            "pv_atual": "10",
            "atributo_fisico": "1",
            "atributo_destreza": "1",
            "atributo_saude": "1",
            "atributo_conhecimento": "1",
            "atributo_comunicacao": "1",
            "atributo_espirito": "1",
        },
    ).status_code == 302

    arquivo = data_dir / "campanhas" / "ankar" / "jogadores" / f"{jogador_id}.json"
    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    box_id = jogador["boxes"][0]["id"]
    assert client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:{box_id}",
        data={"especie_nome": "Bulbasaur"},
    ).status_code == 302
    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    pokemon_id = jogador["boxes"][0]["pokemon_ids"][0]
    assert client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": pokemon_id, "destino": "equipe"},
    ).status_code == 302

    client.post("/logout")
    assert client.post(
        "/login", data={"login": "victor", "senha": "abc123"}
    ).status_code == 302

    resposta = client.get("/jogador/dashboard")
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Jogador" in texto
    assert "Personagem" in texto
    assert "Atributos base" in texto
    assert "Bulbasaur" in texto
    assert "Pontos de Vida" in texto
    assert "Nv. 48" in texto
    assert "PP" not in texto
