from __future__ import annotations

import json
import shutil
from pathlib import Path

from app import create_app
from app.services.calculo_atributos import calcular_atributos_pokemon
from app.services.pokemon_service import (
    carregar_catalogo_golpes,
    carregar_catalogo_pokemons,
    carregar_regras_pokemon,
    indexar_catalogo,
)


def _criar_cliente_com_jogador(tmp_path: Path):
    origem_dados = Path(__file__).resolve().parent.parent / "data"
    data_dir = tmp_path / "data"
    shutil.copytree(origem_dados, data_dir)

    app = create_app()
    app.config.update(TESTING=True, DATA_DIR=data_dir, SECRET_KEY="teste")
    client = app.test_client()

    assert client.post(
        "/login",
        data={"login": "mestre", "senha": "mestre123"},
    ).status_code == 302

    resposta = client.post(
        "/mestre/jogadores/novo",
        data={
            "nome": "Bartz",
            "login": "bartz",
            "senha": "abc123",
            "confirmar_senha": "abc123",
        },
    )
    assert resposta.status_code == 302

    usuarios = json.loads((data_dir / "usuarios.json").read_text(encoding="utf-8"))
    usuario = next(item for item in usuarios["usuarios"] if item["login"] == "bartz")
    return client, data_dir, usuario["jogador_id"]


def test_calculo_de_atributos_por_nivel_e_estilo() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    catalogo = carregar_catalogo_pokemons(data_dir)
    regras = carregar_regras_pokemon(data_dir)
    bulbasaur = indexar_catalogo(catalogo, "pokemons")["bulbasaur"]

    calculos = calcular_atributos_pokemon(
        pokemon={
            "nivel": 2,
            "shiny": False,
            "natureza": "Dócil",
            "status": "Nenhum",
            "bonus": {},
            "golpes": [],
            "experiencia": 0,
        },
        especie=bulbasaur,
        regras=regras,
        estilo_combate="Agressivo",
    )

    assert calculos["totais"]["pv"] == 35
    assert calculos["totais"]["ataque"] == 7
    assert calculos["totais"]["ataque_especial"] == 9
    assert calculos["pp_maximo"] == 22


def test_adicionar_e_editar_pokemon_na_equipe(tmp_path: Path) -> None:
    client, data_dir, jogador_id = _criar_cliente_com_jogador(tmp_path)

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo",
        data={"especie_nome": "Bulbasaur"},
    )
    assert resposta.status_code == 302

    arquivo = data_dir / "campanhas" / "ankar" / "jogadores" / f"{jogador_id}.json"
    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    assert jogador["schema_version"] == 3
    assert len(jogador["pokemons"]) == 1
    assert len(jogador["equipe"]) == 1
    pokemon_id = jogador["equipe"][0]

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/pokemon/{pokemon_id}",
        data={
            "especie_nome": "Bulbasaur",
            "apelido": "Broto",
            "genero": "♂",
            "nivel": "2",
            "experiencia": "30",
            "amizade": "12",
            "natureza": "Dócil",
            "status": "Nenhum",
            "item_carregado": "",
            "pv_atual": "30",
            "bonus_pv": "0",
            "bonus_pp": "0",
            "bonus_ataque": "0",
            "bonus_defesa": "0",
            "bonus_ataque_especial": "0",
            "bonus_defesa_especial": "0",
            "bonus_velocidade": "0",
            "golpe_nome": ["Arranhão", "", "", ""],
            "golpe_usos": ["1", "0", "0", "0"],
            "anotacoes": "Inicial do Bartz",
        },
    )
    assert resposta.status_code == 302

    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    pokemon = jogador["pokemons"][0]
    assert pokemon["apelido"] == "Broto"
    assert pokemon["nivel"] == 2
    assert pokemon["golpes"][0]["golpe_id"] == "arranhao"

    resposta = client.get(f"/mestre/jogadores/{jogador_id}/equipe")
    assert resposta.status_code == 200
    assert b"Broto" in resposta.data

    resposta = client.get(f"/mestre/jogadores/{jogador_id}/pokemon/{pokemon_id}")
    assert resposta.status_code == 200
    assert b"Arranh" in resposta.data


def test_limite_de_seis_pokemons(tmp_path: Path) -> None:
    client, data_dir, jogador_id = _criar_cliente_com_jogador(tmp_path)
    especies = ["Bulbasaur", "Charmander", "Squirtle", "Caterpie", "Weedle", "Pidgey"]
    for especie in especies:
        resposta = client.post(
            f"/mestre/jogadores/{jogador_id}/equipe/novo",
            data={"especie_nome": especie},
        )
        assert resposta.status_code == 302

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo",
        data={"especie_nome": "Rattata"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "limite de 6" in resposta.get_data(as_text=True)

    arquivo = data_dir / "campanhas" / "ankar" / "jogadores" / f"{jogador_id}.json"
    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    assert len(jogador["equipe"]) == 6
