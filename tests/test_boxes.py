from __future__ import annotations

import json
import shutil
from pathlib import Path

from app import create_app


def _criar_cliente_com_jogador(tmp_path: Path):
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
            "nome": "Claire",
            "login": "claire",
            "senha": "abc123",
            "confirmar_senha": "abc123",
        },
    ).status_code == 302

    usuarios = json.loads((data_dir / "usuarios.json").read_text(encoding="utf-8"))
    jogador_id = next(
        item["jogador_id"] for item in usuarios["usuarios"] if item["login"] == "claire"
    )
    arquivo = data_dir / "campanhas" / "ankar" / "jogadores" / f"{jogador_id}.json"
    return client, arquivo, jogador_id


def _ler(arquivo: Path) -> dict:
    return json.loads(arquivo.read_text(encoding="utf-8"))


def test_mover_pokemon_entre_equipe_e_box(tmp_path: Path) -> None:
    client, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)

    assert client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo",
        data={"especie_nome": "Bulbasaur"},
    ).status_code == 302
    jogador = _ler(arquivo)
    pokemon_id = jogador["equipe"][0]
    box_id = jogador["boxes"][0]["id"]

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": pokemon_id, "destino": f"box:{box_id}"},
    )
    assert resposta.status_code == 302
    jogador = _ler(arquivo)
    assert pokemon_id not in jogador["equipe"]
    assert pokemon_id in jogador["boxes"][0]["pokemon_ids"]

    resposta = client.get(f"/mestre/jogadores/{jogador_id}/boxes")
    assert resposta.status_code == 200
    assert "Bulbasaur" in resposta.get_data(as_text=True)

    assert client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": pokemon_id, "destino": "equipe"},
    ).status_code == 302
    jogador = _ler(arquivo)
    assert pokemon_id in jogador["equipe"]
    assert pokemon_id not in jogador["boxes"][0]["pokemon_ids"]


def test_comprar_renomear_e_excluir_box(tmp_path: Path) -> None:
    client, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)
    jogador = _ler(arquivo)
    jogador["treinador"]["pokedolares"] = 250
    arquivo.write_text(json.dumps(jogador, ensure_ascii=False, indent=2), encoding="utf-8")

    assert client.post(f"/mestre/jogadores/{jogador_id}/boxes/novo").status_code == 302
    jogador = _ler(arquivo)
    assert len(jogador["boxes"]) == 2
    assert jogador["treinador"]["pokedolares"] == 150
    box_id = jogador["boxes"][1]["id"]

    assert client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/{box_id}/renomear",
        data={"nome": "Parceiros de Água"},
    ).status_code == 302
    jogador = _ler(arquivo)
    assert jogador["boxes"][1]["nome"] == "Parceiros de Água"

    assert client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/{box_id}/excluir"
    ).status_code == 302
    jogador = _ler(arquivo)
    assert len(jogador["boxes"]) == 1


def test_adicionar_diretamente_ao_box_e_respeitar_equipe_cheia(tmp_path: Path) -> None:
    client, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)
    especies = ["Bulbasaur", "Charmander", "Squirtle", "Caterpie", "Weedle", "Pidgey"]
    for especie in especies:
        assert client.post(
            f"/mestre/jogadores/{jogador_id}/equipe/novo",
            data={"especie_nome": especie},
        ).status_code == 302

    jogador = _ler(arquivo)
    box_id = jogador["boxes"][0]["id"]
    assert client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:{box_id}",
        data={"especie_nome": "Rattata"},
    ).status_code == 302

    jogador = _ler(arquivo)
    pokemon_box = jogador["boxes"][0]["pokemon_ids"][0]
    assert len(jogador["equipe"]) == 6

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": pokemon_box, "destino": "equipe"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "limite de 6" in resposta.get_data(as_text=True)
    jogador = _ler(arquivo)
    assert pokemon_box in jogador["boxes"][0]["pokemon_ids"]
    assert len(jogador["equipe"]) == 6
