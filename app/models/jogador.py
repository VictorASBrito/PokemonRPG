from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def estrutura_jogador_padrao(
    *,
    jogador_id: str,
    usuario_id: str,
    campanha_id: str,
    nome: str,
    regras: dict[str, Any],
) -> dict[str, Any]:
    atributos = {
        atributo["id"]: int(atributo.get("valor_inicial", atributo.get("minimo", 1)))
        for atributo in regras.get("atributos", [])
    }

    saude = int(atributos.get("saude", 1))
    pv_por_saude = int(regras.get("pv_por_ponto_saude", 10))
    pv_maximo = saude * pv_por_saude
    horario = agora_iso()

    return {
        "schema_version": 3,
        "id": jogador_id,
        "usuario_id": usuario_id,
        "campanha_id": campanha_id,
        "criado_em": horario,
        "atualizado_em": horario,
        "treinador": {
            "nome": nome.strip(),
            "idade": None,
            "genero": "",
            "origem": "",
            "classe": "",
            "estilo_combate": "",
            "numeros_shiny": [],
            "pokedolares": 0,
            "pv_atual": pv_maximo,
            "pv_maximo": pv_maximo,
            "atributos": atributos,
            "beneficios_habilidades": "",
            "anotacoes": "",
        },
        "inventario": [],
        "insigneas": [],
        "pokemons": [],
        "equipe": [],
        "boxes": [
            {
                "id": "box_1",
                "nome": "Box 1",
                "limite": 10,
                "pokemon_ids": [],
            }
        ],
        "pokedex": {
            "vistos": [],
            "capturados": [],
        },
    }


def copiar_jogador(jogador: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(jogador)
