from __future__ import annotations

import json
import shutil
from pathlib import Path

from app import create_app
from app.services.box_service import garantir_estrutura_boxes, mover_pokemon
from app.services.pokemon_service import carregar_regras_pokemon


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
    return client, data_dir, arquivo, jogador_id


def _ler(arquivo: Path) -> dict:
    return json.loads(arquivo.read_text(encoding="utf-8"))


def _criar_na_box(client, arquivo: Path, jogador_id: str, especie: str) -> str:
    jogador = _ler(arquivo)
    box_id = jogador["boxes"][0]["id"]
    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:{box_id}",
        data={"especie_nome": especie},
    )
    assert resposta.status_code == 302
    jogador = _ler(arquivo)
    return jogador["boxes"][0]["pokemon_ids"][-1]


def test_box_unica_tem_cem_espacos_e_nao_possui_compra(tmp_path: Path) -> None:
    client, _, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)
    jogador = _ler(arquivo)

    assert jogador["schema_version"] == 5
    assert len(jogador["boxes"]) == 1
    assert jogador["boxes"][0]["limite"] == 100

    resposta = client.get(f"/mestre/jogadores/{jogador_id}/boxes")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "100 espaços" in texto
    assert "Comprar Box" not in texto
    assert "/boxes/novo" not in texto


def test_pokemon_so_pode_ser_criado_em_espaco_da_box(tmp_path: Path) -> None:
    client, _, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo",
        data={"especie_nome": "Bulbasaur"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "só podem ser criados em um espaço vazio da Box" in resposta.get_data(as_text=True)
    jogador = _ler(arquivo)
    assert jogador["pokemons"] == []
    assert jogador["equipe"] == []

    pokemon_id = _criar_na_box(client, arquivo, jogador_id, "Bulbasaur")
    jogador = _ler(arquivo)
    assert pokemon_id in jogador["boxes"][0]["pokemon_ids"]
    assert pokemon_id not in jogador["equipe"]


def test_movimentacao_adiciona_ao_fim_da_equipe_e_da_box(tmp_path: Path) -> None:
    client, _, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)
    bulbasaur = _criar_na_box(client, arquivo, jogador_id, "Bulbasaur")
    charmander = _criar_na_box(client, arquivo, jogador_id, "Charmander")

    for pokemon_id in (bulbasaur, charmander):
        assert client.post(
            f"/mestre/jogadores/{jogador_id}/boxes/mover",
            data={"pokemon_id": pokemon_id, "destino": "equipe"},
        ).status_code == 302

    jogador = _ler(arquivo)
    assert jogador["equipe"] == [bulbasaur, charmander]
    assert jogador["boxes"][0]["pokemon_ids"] == []

    box_id = jogador["boxes"][0]["id"]
    assert client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": bulbasaur, "destino": f"box:{box_id}"},
    ).status_code == 302
    assert client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": charmander, "destino": f"box:{box_id}"},
    ).status_code == 302

    jogador = _ler(arquivo)
    assert jogador["equipe"] == []
    assert jogador["boxes"][0]["pokemon_ids"] == [bulbasaur, charmander]


def test_equipe_cheia_impede_adicao_vinda_da_box(tmp_path: Path) -> None:
    client, _, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)
    especies = ["Bulbasaur", "Charmander", "Squirtle", "Caterpie", "Weedle", "Pidgey", "Rattata"]
    ids = [_criar_na_box(client, arquivo, jogador_id, especie) for especie in especies]

    for pokemon_id in ids[:6]:
        assert client.post(
            f"/mestre/jogadores/{jogador_id}/boxes/mover",
            data={"pokemon_id": pokemon_id, "destino": "equipe"},
        ).status_code == 302

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/boxes/mover",
        data={"pokemon_id": ids[6], "destino": "equipe"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "limite de 6" in resposta.get_data(as_text=True)
    jogador = _ler(arquivo)
    assert len(jogador["equipe"]) == 6
    assert ids[6] in jogador["boxes"][0]["pokemon_ids"]


def test_migracao_reune_boxes_antigas_preservando_ordem() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    regras = carregar_regras_pokemon(data_dir)
    jogador = {
        "schema_version": 4,
        "treinador": {"nivel": 1},
        "pokemons": [
            {"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}
        ],
        "equipe": ["a"],
        "boxes": [
            {"id": "box_antiga", "nome": "Primeira", "limite": 10, "pokemon_ids": ["b"]},
            {"id": "box_2", "nome": "Segunda", "limite": 10, "pokemon_ids": ["c"]},
        ],
    }

    garantir_estrutura_boxes(jogador, regras)

    assert jogador["schema_version"] == 5
    assert len(jogador["boxes"]) == 1
    assert jogador["boxes"][0]["id"] == "box_antiga"
    assert jogador["boxes"][0]["limite"] == 100
    assert jogador["boxes"][0]["pokemon_ids"] == ["b", "c", "d"]


def test_box_renderiza_pesquisa_dinamica_com_ordem(tmp_path: Path) -> None:
    client, _, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)
    _criar_na_box(client, arquivo, jogador_id, "Bulbasaur")
    _criar_na_box(client, arquivo, jogador_id, "Pikachu")

    resposta = client.get(f"/mestre/jogadores/{jogador_id}/boxes")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert 'id="filtro-box-nome"' in texto
    assert "data-box-pokemon-card" in texto
    assert "data-ordem=" in texto
    assert "Adicionar ao time" in texto
    assert "Criar Pokémon" in texto
