from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

ATRIBUTOS_BONUS = (
    "pv",
    "ataque",
    "defesa",
    "ataque_especial",
    "defesa_especial",
    "velocidade",
)


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def estrutura_pokemon_padrao(
    *,
    especie_id: str,
    pv_maximo: int,
    natureza: str = "Dócil",
) -> dict[str, Any]:
    horario = agora_iso()
    return {
        "id": f"pkm_{uuid.uuid4().hex[:12]}",
        "especie_id": especie_id,
        "apelido": "",
        "genero": "Ø",
        "shiny": False,
        "natureza": natureza,
        "status": "Nenhum",
        "item_carregado": "",
        "pv_atual": pv_maximo,
        "bonus": {atributo: 0 for atributo in ATRIBUTOS_BONUS},
        "golpes": [],
        "anotacoes": "",
        "criado_em": horario,
        "atualizado_em": horario,
    }
