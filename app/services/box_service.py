from __future__ import annotations

import uuid
from typing import Any

from app.services.calculo_atributos import calcular_atributos_pokemon
from app.services.pokemon_service import indexar_catalogo


CONFIG_BOX_PADRAO = {
    "espacos_por_box": 10,
    "quantidade_inicial": 1,
    "custo_novo_box": 100,
    "permitir_boxes_ilimitados": True,
    "limite_boxes": None,
}


def carregar_config_boxes(regras: dict[str, Any]) -> dict[str, Any]:
    configuracao = dict(CONFIG_BOX_PADRAO)
    configuracao.update(regras.get("boxes", {}))
    configuracao["espacos_por_box"] = max(
        1, int(configuracao.get("espacos_por_box", 10))
    )
    configuracao["quantidade_inicial"] = max(
        1, int(configuracao.get("quantidade_inicial", 1))
    )
    configuracao["custo_novo_box"] = max(
        0, int(configuracao.get("custo_novo_box", 100))
    )
    limite = configuracao.get("limite_boxes")
    configuracao["limite_boxes"] = int(limite) if limite not in (None, "") else None
    configuracao["permitir_boxes_ilimitados"] = bool(
        configuracao.get("permitir_boxes_ilimitados", True)
    )
    return configuracao


def _novo_box(indice: int, limite: int) -> dict[str, Any]:
    return {
        "id": f"box_{uuid.uuid4().hex[:10]}",
        "nome": f"Box {indice}",
        "limite": limite,
        "pokemon_ids": [],
    }


def garantir_estrutura_boxes(
    jogador: dict[str, Any],
    regras: dict[str, Any],
) -> dict[str, Any]:
    config = carregar_config_boxes(regras)
    jogador.setdefault("pokemons", [])
    jogador.setdefault("equipe", [])
    jogador.setdefault("boxes", [])
    jogador["schema_version"] = max(3, int(jogador.get("schema_version", 1)))

    ids_validos = {
        str(pokemon.get("id"))
        for pokemon in jogador.get("pokemons", [])
        if isinstance(pokemon, dict) and pokemon.get("id")
    }

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

    boxes_normalizados: list[dict[str, Any]] = []
    ids_boxes: set[str] = set()
    ocupados = set(equipe)

    for indice, box_atual in enumerate(jogador.get("boxes", []), start=1):
        if not isinstance(box_atual, dict):
            continue
        box_id = str(box_atual.get("id", "")).strip()
        if not box_id or box_id in ids_boxes:
            box_id = f"box_{uuid.uuid4().hex[:10]}"
        ids_boxes.add(box_id)

        limite = box_atual.get("limite", config["espacos_por_box"])
        try:
            limite = max(1, int(limite))
        except (TypeError, ValueError):
            limite = config["espacos_por_box"]

        nome = str(box_atual.get("nome", "")).strip() or f"Box {indice}"
        pokemon_ids: list[str] = []
        for pokemon_id in box_atual.get("pokemon_ids", []):
            pokemon_id = str(pokemon_id)
            if (
                pokemon_id in ids_validos
                and pokemon_id not in ocupados
                and len(pokemon_ids) < limite
            ):
                pokemon_ids.append(pokemon_id)
                ocupados.add(pokemon_id)

        boxes_normalizados.append(
            {
                "id": box_id,
                "nome": nome[:60],
                "limite": limite,
                "pokemon_ids": pokemon_ids,
            }
        )

    while len(boxes_normalizados) < config["quantidade_inicial"]:
        boxes_normalizados.append(
            _novo_box(len(boxes_normalizados) + 1, config["espacos_por_box"])
        )

    # Preserva qualquer Pokémon antigo que ainda não possua localização.
    sem_local = [pokemon_id for pokemon_id in ids_validos if pokemon_id not in ocupados]
    for pokemon_id in sem_local:
        destino = next(
            (
                box
                for box in boxes_normalizados
                if len(box["pokemon_ids"]) < int(box["limite"])
            ),
            None,
        )
        if destino is None:
            destino = _novo_box(
                len(boxes_normalizados) + 1, config["espacos_por_box"]
            )
            boxes_normalizados.append(destino)
        destino["pokemon_ids"].append(pokemon_id)
        ocupados.add(pokemon_id)

    jogador["boxes"] = boxes_normalizados
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


def localizar_pokemon(jogador: dict[str, Any], pokemon_id: str) -> tuple[str, str | None]:
    pokemon_id = str(pokemon_id)
    if pokemon_id in [str(item) for item in jogador.get("equipe", [])]:
        return "equipe", None
    for box in jogador.get("boxes", []):
        if pokemon_id in [str(item) for item in box.get("pokemon_ids", [])]:
            return "box", str(box.get("id"))
    return "sem_local", None


def primeiro_box_com_espaco(jogador: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            box
            for box in jogador.get("boxes", [])
            if len(box.get("pokemon_ids", [])) < int(box.get("limite", 10))
        ),
        None,
    )


def criar_box(
    jogador: dict[str, Any],
    regras: dict[str, Any],
    *,
    cobrar: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    garantir_estrutura_boxes(jogador, regras)
    config = carregar_config_boxes(regras)

    limite_boxes = config.get("limite_boxes")
    if (
        not config["permitir_boxes_ilimitados"]
        and limite_boxes is not None
        and len(jogador["boxes"]) >= limite_boxes
    ):
        return None, f"O limite de {limite_boxes} Boxes já foi alcançado."

    custo = config["custo_novo_box"] if cobrar else 0
    treinador = jogador.setdefault("treinador", {})
    saldo = int(treinador.get("pokedolares", 0))
    if saldo < custo:
        return None, (
            f"São necessários ₽ {custo} para comprar um novo Box. "
            f"Saldo atual: ₽ {saldo}."
        )

    if custo:
        treinador["pokedolares"] = saldo - custo

    box = _novo_box(len(jogador["boxes"]) + 1, config["espacos_por_box"])
    jogador["boxes"].append(box)
    return box, None


def renomear_box(
    jogador: dict[str, Any],
    box_id: str,
    nome: str,
) -> str | None:
    box = encontrar_box(jogador, box_id)
    if not box:
        return "Box não encontrado."
    nome = nome.strip()
    if not nome:
        return "Informe um nome para o Box."
    if len(nome) > 60:
        return "O nome do Box deve possuir no máximo 60 caracteres."
    box["nome"] = nome
    return None


def excluir_box(jogador: dict[str, Any], box_id: str) -> str | None:
    box = encontrar_box(jogador, box_id)
    if not box:
        return "Box não encontrado."
    if len(jogador.get("boxes", [])) <= 1:
        return "É necessário manter pelo menos um Box."
    if box.get("pokemon_ids"):
        return "Somente Boxes vazios podem ser removidos."
    jogador["boxes"] = [
        item for item in jogador["boxes"] if str(item.get("id")) != str(box_id)
    ]
    return None


def mover_pokemon(
    jogador: dict[str, Any],
    regras: dict[str, Any],
    *,
    pokemon_id: str,
    destino: str,
) -> str | None:
    garantir_estrutura_boxes(jogador, regras)
    pokemon_id = str(pokemon_id)
    ids_validos = {
        str(item.get("id"))
        for item in jogador.get("pokemons", [])
        if isinstance(item, dict) and item.get("id")
    }
    if pokemon_id not in ids_validos:
        return "Pokémon não encontrado na ficha."

    destino = str(destino).strip()
    if destino == "equipe":
        limite_equipe = int(regras.get("limites", {}).get("tamanho_equipe", 6))
        if pokemon_id not in jogador["equipe"] and len(jogador["equipe"]) >= limite_equipe:
            return f"A equipe já possui o limite de {limite_equipe} Pokémon."
    elif destino.startswith("box:"):
        box_id = destino.split(":", 1)[1]
        box = encontrar_box(jogador, box_id)
        if not box:
            return "O Box de destino não foi encontrado."
        if (
            pokemon_id not in [str(item) for item in box.get("pokemon_ids", [])]
            and len(box.get("pokemon_ids", [])) >= int(box.get("limite", 10))
        ):
            return f'O Box "{box.get("nome", "Box")}" está cheio.'
    else:
        return "Selecione um destino válido."

    jogador["equipe"] = [
        item for item in jogador.get("equipe", []) if str(item) != pokemon_id
    ]
    for box_atual in jogador.get("boxes", []):
        box_atual["pokemon_ids"] = [
            item
            for item in box_atual.get("pokemon_ids", [])
            if str(item) != pokemon_id
        ]

    if destino == "equipe":
        jogador["equipe"].append(pokemon_id)
    else:
        box_id = destino.split(":", 1)[1]
        box = encontrar_box(jogador, box_id)
        assert box is not None
        box["pokemon_ids"].append(pokemon_id)
    return None


def _registro_detalhado(
    pokemon: dict[str, Any],
    *,
    especies: dict[str, dict[str, Any]],
    golpes: dict[str, dict[str, Any]],
    regras: dict[str, Any],
    estilo: str,
) -> dict[str, Any] | None:
    especie = especies.get(str(pokemon.get("especie_id")))
    if not especie:
        return None
    calculos = calcular_atributos_pokemon(
        pokemon=pokemon,
        especie=especie,
        regras=regras,
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
    estilo = str(jogador.get("treinador", {}).get("estilo_combate", ""))

    equipe: list[dict[str, Any]] = []
    for pokemon_id in jogador.get("equipe", []):
        pokemon = pokemons.get(str(pokemon_id))
        if pokemon:
            registro = _registro_detalhado(
                pokemon,
                especies=especies,
                golpes=golpes,
                regras=regras,
                estilo=estilo,
            )
            if registro:
                equipe.append(registro)

    boxes: list[dict[str, Any]] = []
    for box in jogador.get("boxes", []):
        registros: list[dict[str, Any]] = []
        for pokemon_id in box.get("pokemon_ids", []):
            pokemon = pokemons.get(str(pokemon_id))
            if pokemon:
                registro = _registro_detalhado(
                    pokemon,
                    especies=especies,
                    golpes=golpes,
                    regras=regras,
                    estilo=estilo,
                )
                if registro:
                    registros.append(registro)
        boxes.append({**box, "registros": registros})

    return equipe, boxes
