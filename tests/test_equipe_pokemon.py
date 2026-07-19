from __future__ import annotations

import json
import shutil
from pathlib import Path

from app import create_app
from app.services.calculo_atributos import calcular_atributos_pokemon
from app.services.pokemon_service import (
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
    arquivo = data_dir / "campanhas" / "ankar" / "jogadores" / f"{usuario['jogador_id']}.json"
    return client, data_dir, arquivo, usuario["jogador_id"]


def _criar_na_box(client, arquivo: Path, jogador_id: str, especie: str) -> str:
    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    box_id = jogador["boxes"][0]["id"]
    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:{box_id}",
        data={"especie_nome": especie},
    )
    assert resposta.status_code == 302
    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    return jogador["boxes"][0]["pokemon_ids"][-1]


def test_calculo_usa_nivel_do_jogador() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    catalogo = carregar_catalogo_pokemons(data_dir)
    regras = carregar_regras_pokemon(data_dir)
    bulbasaur = indexar_catalogo(catalogo, "pokemons")["bulbasaur"]

    calculos = calcular_atributos_pokemon(
        pokemon={
            "shiny": False,
            "natureza": "Dócil",
            "status": "Nenhum",
            "bonus": {},
            "golpes": [],
        },
        especie=bulbasaur,
        regras=regras,
        nivel_jogador=48,
        estilo_combate="Agressivo",
    )

    assert calculos["nivel"] == 48
    assert calculos["totais"]["pv"] == 81
    assert calculos["totais"]["ataque"] == 58
    assert calculos["totais"]["ataque_especial"] == 85
    assert "pp_maximo" not in calculos
    assert "experiencia_proximo_nivel" not in calculos
    assert "dados_luta" not in calculos


def test_adicionar_na_box_e_editar_pokemon_sem_pp_xp_ou_amizade(tmp_path: Path) -> None:
    client, data_dir, arquivo, jogador_id = _criar_cliente_com_jogador(tmp_path)

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/ficha",
        data={
            "nome": "Bartz",
            "nivel": "48",
            "idade": "17",
            "genero": "Masculino",
            "origem": "Atleta",
            "classe": "Treinador(a)",
            "estilo_combate": "Agressivo",
            "numeros_shiny": "7",
            "pokedolares": "300",
            "pv_atual": "10",
            "atributo_fisico": "1",
            "atributo_destreza": "1",
            "atributo_saude": "1",
            "atributo_conhecimento": "1",
            "atributo_comunicacao": "1",
            "atributo_espirito": "1",
        },
    )
    assert resposta.status_code == 302

    pokemon_id = _criar_na_box(client, arquivo, jogador_id, "Bulbasaur")
    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    assert jogador["schema_version"] == 5
    assert jogador["treinador"]["nivel"] == 48
    assert pokemon_id in jogador["boxes"][0]["pokemon_ids"]
    assert pokemon_id not in jogador["equipe"]

    resposta = client.post(
        f"/mestre/jogadores/{jogador_id}/pokemon/{pokemon_id}?retorno=boxes",
        data={
            "retorno": "boxes",
            "especie_nome": "Bulbasaur",
            "apelido": "Broto",
            "genero": "♂",
            "natureza": "Dócil",
            "status": "Nenhum",
            "item_carregado": "",
            "pv_atual": "70",
            "bonus_pv": "0",
            "bonus_ataque": "0",
            "bonus_defesa": "0",
            "bonus_ataque_especial": "0",
            "bonus_defesa_especial": "0",
            "bonus_velocidade": "0",
            "golpe_nome": ["Arranhão", "", "", ""],
            "anotacoes": "Inicial do Bartz",
        },
    )
    assert resposta.status_code == 302

    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    pokemon = jogador["pokemons"][0]
    assert pokemon["apelido"] == "Broto"
    assert pokemon["golpes"][0] == {"golpe_id": "arranhao"}
    assert "nivel" not in pokemon
    assert "experiencia" not in pokemon
    assert "amizade" not in pokemon
    assert "pp" not in pokemon["bonus"]


def test_tela_da_equipe_direciona_espacos_vazios_para_box(tmp_path: Path) -> None:
    client, _, _, jogador_id = _criar_cliente_com_jogador(tmp_path)
    resposta = client.get(f"/mestre/jogadores/{jogador_id}/equipe")
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Gerenciar pela Box" in texto
    assert "Adicione um Pokémon pela Box" in texto
    assert f"/mestre/jogadores/{jogador_id}/boxes" in texto
    assert "Adicionar Pokémon" not in texto
