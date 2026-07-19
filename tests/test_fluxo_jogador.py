from __future__ import annotations

import json
import shutil
from pathlib import Path

from app import create_app


def test_cadastro_e_edicao_da_ficha(tmp_path: Path) -> None:
    origem_dados = Path(__file__).resolve().parent.parent / "data"
    data_dir = tmp_path / "data"
    shutil.copytree(origem_dados, data_dir)

    app = create_app()
    app.config.update(TESTING=True, DATA_DIR=data_dir, SECRET_KEY="teste")
    client = app.test_client()

    resposta = client.post(
        "/login",
        data={"login": "mestre", "senha": "mestre123"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200

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
    jogador_id = usuario["jogador_id"]

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
            "numeros_shiny": "7, 42",
            "pokedolares": "300",
            "pv_atual": "30",
            "atributo_fisico": "3",
            "atributo_destreza": "2",
            "atributo_saude": "3",
            "atributo_conhecimento": "2",
            "atributo_comunicacao": "1",
            "atributo_espirito": "1",
            "beneficios_habilidades": "Teste",
            "anotacoes": "Teste 2",
            "item_nome": ["Poké Bola", "Poção"],
            "item_quantidade": ["6", "3"],
            "insignea_nome": ["Pedra"],
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    arquivo = data_dir / "campanhas" / "ankar" / "jogadores" / f"{jogador_id}.json"
    jogador = json.loads(arquivo.read_text(encoding="utf-8"))
    assert jogador["treinador"]["pv_maximo"] == 30
    assert jogador["treinador"]["nivel"] == 48
    assert jogador["treinador"]["numeros_shiny"] == [7, 42]
    assert len(jogador["inventario"]) == 2
