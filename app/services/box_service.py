from __future__ import annotations

import uuid
from typing import Any

from app.services.calculo_atributos import calcular_atributos_pokemon
from app.services.pokemon_service import indexar_catalogo


def _inteiro(valor: Any, padrao: int = 0) -> int:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return padrao


CONFIG_BOX_PADRAO = {
    "espacos": 100,
    "nome": "Box Pokémon",
}


def carregar_config_boxes(regras: dict[str, Any]) -> dict[str, Any]:
    configuracao = dict(CONFIG_BOX_PADRAO)
    configuracao.update(regras.get("boxes", {}))
    configuracao["espacos"] = max(1, int(configuracao.get("espacos", 100)))
    configuracao["nome"] = str(configuracao.get("nome", "Box Pokémon")).strip() or "Box Pokémon"
    return configuracao


def _box_unica(config: dict[str, Any], *, box_id: str | None = None, nome: str | None = None) -> dict[str, Any]:
    return {
        "id": box_id or f"box_{uuid.uuid4().hex[:10]}",
        "nome": (nome or config["nome"])[:60],
        "limite": int(config["espacos"]),
        "pokemon_ids": [],
    }


def garantir_estrutura_boxes(
    jogador: dict[str, Any],
    regras: dict[str, Any],
) -> dict[str, Any]:
    """Normaliza qualquer estrutura antiga para uma única Box de 100 espaços.

    A ordem já existente é preservada: primeiro os Pokémon da primeira Box,
    depois os das Boxes seguintes e, por fim, qualquer Pokémon sem localização.
    """
    config = carregar_config_boxes(regras)
    jogador.setdefault("pokemons", [])
    jogador.setdefault("equipe", [])
    jogador.setdefault("boxes", [])
    jogador["schema_version"] = max(5, int(jogador.get("schema_version", 1)))

    ids_validos_ordenados = [
        str(pokemon.get("id"))
        for pokemon in jogador.get("pokemons", [])
        if isinstance(pokemon, dict) and pokemon.get("id")
    ]
    ids_validos = set(ids_validos_ordenados)

    equipe: list[str] = []
    limite_equipe = int(regras.get("limites", {}).get("tamanho_equipe", 6))
    for pokemon_id in jogador.get("equipe", []):
        pokemon_id = str(pokemon_id)
        if (
            pokemon_id in ids_validos
            and pokemon_id not in equipe
            and len(equipe) < limite_equipe
        ):
            equipe.append(pokemon_id)
    jogador["equipe"] = equipe

    boxes_antigas = [
        box for box in jogador.get("boxes", []) if isinstance(box, dict)
    ]
    primeira_box = boxes_antigas[0] if boxes_antigas else {}
    box = _box_unica(
        config,
        box_id=str(primeira_box.get("id", "")).strip() or None,
        nome=str(primeira_box.get("nome", "")).strip() or None,
    )

    ocupados = set(equipe)
    pokemon_ids: list[str] = []

    for box_antiga in boxes_antigas:
        for pokemon_id in box_antiga.get("pokemon_ids", []):
            pokemon_id = str(pokemon_id)
            if (
                pokemon_id in ids_validos
                and pokemon_id not in ocupados
                and len(pokemon_ids) < box["limite"]
            ):
                pokemon_ids.append(pokemon_id)
                ocupados.add(pokemon_id)

    # Preserva fichas antigas que não possuíam localização registrada.
    for pokemon_id in ids_validos_ordenados:
        if pokemon_id not in ocupados and len(pokemon_ids) < box["limite"]:
            pokemon_ids.append(pokemon_id)
            ocupados.add(pokemon_id)

    box["pokemon_ids"] = pokemon_ids
    jogador["boxes"] = [box]
    return jogador


def encontrar_box(jogador: dict[str, Any], box_id: str) -> dict[str, Any] | None:
    return next(
        (
            box
            for box in jogador.get("boxes", [])
            if str(box.get("id")) == str(box_id)
        ),
        None,
    )


def box_unica(jogador: dict[str, Any]) -> dict[str, Any] | None:
    boxes = jogador.get("boxes", [])
    return boxes[0] if boxes else None


def localizar_pokemon(jogador: dict[str, Any], pokemon_id: str) -> tuple[str, str | None]:
    pokemon_id = str(pokemon_id)
    if pokemon_id in [str(item) for item in jogador.get("equipe", [])]:
        return "equipe", None
    box = box_unica(jogador)
    if box and pokemon_id in [str(item) for item in box.get("pokemon_ids", [])]:
        return "box", str(box.get("id"))
    return "sem_local", None


def primeiro_box_com_espaco(jogador: dict[str, Any]) -> dict[str, Any] | None:
    box = box_unica(jogador)
    if box and len(box.get("pokemon_ids", [])) < int(box.get("limite", 100)):
        return box
    return None


def renomear_box(
    jogador: dict[str, Any],
    box_id: str,
    nome: str,
) -> str | None:
    box = encontrar_box(jogador, box_id)
    if not box:
        return "Box não encontrada."
    nome = nome.strip()
    if not nome:
        return "Informe um nome para a Box."
    if len(nome) > 60:
        return "O nome da Box deve possuir no máximo 60 caracteres."
    box["nome"] = nome
    return None


def mover_pokemon(
    jogador: dict[str, Any],
    regras: dict[str, Any],
    *,
    pokemon_id: str,
    destino: str,
) -> str | None:
    """Move Pokémon entre a equipe e a Box única.

    Ao sair da equipe, o Pokémon é sempre acrescentado no fim da Box. Ao sair
    da Box, ele é acrescentado diretamente ao fim da equipe, caso exista vaga.
    """
    garantir_estrutura_boxes(jogador, regras)
    pokemon_id = str(pokemon_id)
    ids_validos = {
        str(item.get("id"))
        for item in jogador.get("pokemons", [])
        if isinstance(item, dict) and item.get("id")
    }
    if pokemon_id not in ids_validos:
        return "Pokémon não encontrado na ficha."

    box = box_unica(jogador)
    if not box:
        return "A Box do jogador não foi encontrada."

    destino = str(destino).strip()
    if destino == "equipe":
        limite_equipe = int(regras.get("limites", {}).get("tamanho_equipe", 6))
        if pokemon_id in jogador["equipe"]:
            return None
        if len(jogador["equipe"]) >= limite_equipe:
            return f"A equipe já possui o limite de {limite_equipe} Pokémon."

        box["pokemon_ids"] = [
            item for item in box.get("pokemon_ids", []) if str(item) != pokemon_id
        ]
        jogador["equipe"].append(pokemon_id)
        return None

    destino_box_id = destino.split(":", 1)[1] if destino.startswith("box:") else ""
    if destino_box_id != str(box.get("id")):
        return "Selecione um destino válido."
    if pokemon_id in [str(item) for item in box.get("pokemon_ids", [])]:
        return None
    if len(box.get("pokemon_ids", [])) >= int(box.get("limite", 100)):
        return "A Box está cheia."

    jogador["equipe"] = [
        item for item in jogador.get("equipe", []) if str(item) != pokemon_id
    ]
    # append garante que o Pokémon retirado do time vá para o último lugar.
    box["pokemon_ids"].append(pokemon_id)
    return None


def _registro_detalhado(
    pokemon: dict[str, Any],
    *,
    especies: dict[str, dict[str, Any]],
    golpes: dict[str, dict[str, Any]],
    regras: dict[str, Any],
    nivel_jogador: int,
    estilo: str,
) -> dict[str, Any] | None:
    especie = especies.get(str(pokemon.get("especie_id")))
    if not especie:
        return None
    calculos = calcular_atributos_pokemon(
        pokemon=pokemon,
        especie=especie,
        regras=regras,
        nivel_jogador=nivel_jogador,
        estilo_combate=estilo,
        golpes_catalogo=golpes,
    )
    return {"pokemon": pokemon, "especie": especie, "calculos": calculos}


def boxes_detalhadas(
    *,
    jogador: dict[str, Any],
    catalogo_pokemons: dict[str, Any],
    catalogo_golpes: dict[str, Any],
    regras: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    garantir_estrutura_boxes(jogador, regras)
    especies = indexar_catalogo(catalogo_pokemons, "pokemons")
    golpes = indexar_catalogo(catalogo_golpes, "golpes")
    pokemons = {
        str(item.get("id")): item
        for item in jogador.get("pokemons", [])
        if isinstance(item, dict) and item.get("id")
    }
    treinador = jogador.get("treinador", {})
    estilo = str(treinador.get("estilo_combate", ""))
    nivel_jogador = max(1, _inteiro(treinador.get("nivel"), 1))

    equipe: list[dict[str, Any]] = []
    for pokemon_id in jogador.get("equipe", []):
        pokemon = pokemons.get(str(pokemon_id))
        if pokemon:
            registro = _registro_detalhado(
                pokemon,
                especies=especies,
                golpes=golpes,
                regras=regras,
                nivel_jogador=nivel_jogador,
                estilo=estilo,
            )
            if registro:
                equipe.append(registro)

    boxes: list[dict[str, Any]] = []
    for box in jogador.get("boxes", []):
        registros: list[dict[str, Any]] = []
        for indice, pokemon_id in enumerate(box.get("pokemon_ids", [])):
            pokemon = pokemons.get(str(pokemon_id))
            if pokemon:
                registro = _registro_detalhado(
                    pokemon,
                    especies=especies,
                    golpes=golpes,
                    regras=regras,
                    nivel_jogador=nivel_jogador,
                    estilo=estilo,
                )
                if registro:
                    registro["ordem_box"] = indice
                    registros.append(registro)
        boxes.append({**box, "registros": registros})

    return equipe, boxes
