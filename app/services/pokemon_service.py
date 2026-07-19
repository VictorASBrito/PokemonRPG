from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from app.models.pokemon import ATRIBUTOS_BONUS, agora_iso, estrutura_pokemon_padrao
from app.services.calculo_atributos import calcular_atributos_pokemon
from app.services.json_service import ler_json


def carregar_catalogo_pokemons(data_dir: str | Path) -> dict[str, Any]:
    return ler_json(
        Path(data_dir) / "catalogo" / "pokemons.json",
        {"pokemons": [], "total": 0},
    )


def carregar_catalogo_golpes(data_dir: str | Path) -> dict[str, Any]:
    return ler_json(
        Path(data_dir) / "catalogo" / "golpes.json",
        {"golpes": [], "total": 0},
    )


def carregar_regras_pokemon(data_dir: str | Path) -> dict[str, Any]:
    return ler_json(
        Path(data_dir) / "catalogo" / "regras_pokemon.json",
        {"limites": {"tamanho_equipe": 6, "golpes_por_pokemon": 4}},
    )


def indexar_catalogo(catalogo: dict[str, Any], chave: str) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in catalogo.get(chave, [])
        if isinstance(item, dict) and item.get("id")
    }


def buscar_por_nome(
    catalogo: dict[str, Any],
    chave: str,
    nome: str,
) -> dict[str, Any] | None:
    nome_normalizado = nome.strip().casefold()
    return next(
        (
            item
            for item in catalogo.get(chave, [])
            if str(item.get("nome", "")).casefold() == nome_normalizado
        ),
        None,
    )


def garantir_estrutura_pokemon(jogador: dict[str, Any]) -> dict[str, Any]:
    jogador.setdefault("pokemons", [])
    jogador.setdefault("equipe", [])
    jogador.setdefault(
        "boxes",
        [{"id": "box_1", "nome": "Box 1", "limite": 10, "pokemon_ids": []}],
    )
    jogador["schema_version"] = max(3, int(jogador.get("schema_version", 1)))

    ids_validos = {
        str(item.get("id"))
        for item in jogador.get("pokemons", [])
        if isinstance(item, dict) and item.get("id")
    }
    equipe_limpa: list[str] = []
    for pokemon_id in jogador.get("equipe", []):
        pokemon_id = str(pokemon_id)
        if pokemon_id in ids_validos and pokemon_id not in equipe_limpa:
            equipe_limpa.append(pokemon_id)
    jogador["equipe"] = equipe_limpa

    ocupados = set(equipe_limpa)
    boxes_limpas: list[dict[str, Any]] = []
    for indice, box in enumerate(jogador.get("boxes", []), start=1):
        if not isinstance(box, dict):
            continue
        limite = max(1, _inteiro(box.get("limite"), 10))
        pokemon_ids: list[str] = []
        for pokemon_id in box.get("pokemon_ids", []):
            pokemon_id = str(pokemon_id)
            if (
                pokemon_id in ids_validos
                and pokemon_id not in ocupados
                and len(pokemon_ids) < limite
            ):
                pokemon_ids.append(pokemon_id)
                ocupados.add(pokemon_id)
        boxes_limpas.append(
            {
                "id": str(box.get("id") or f"box_{indice}"),
                "nome": str(box.get("nome") or f"Box {indice}"),
                "limite": limite,
                "pokemon_ids": pokemon_ids,
            }
        )
    if not boxes_limpas:
        boxes_limpas = [
            {"id": "box_1", "nome": "Box 1", "limite": 10, "pokemon_ids": []}
        ]
    jogador["boxes"] = boxes_limpas
    return jogador


def encontrar_pokemon(jogador: dict[str, Any], pokemon_id: str) -> dict[str, Any] | None:
    garantir_estrutura_pokemon(jogador)
    return next(
        (
            pokemon
            for pokemon in jogador.get("pokemons", [])
            if str(pokemon.get("id")) == pokemon_id
        ),
        None,
    )


def _inteiro(valor: Any, padrao: int = 0) -> int:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return padrao


def _opcoes(regras: dict[str, Any], chave: str) -> set[str]:
    return {
        str(item.get("nome", item)).strip()
        for item in regras.get(chave, [])
        if str(item.get("nome", item)).strip()
    }


def _normalizar_bonus(formulario: Any) -> dict[str, int]:
    return {
        atributo: _inteiro(formulario.get(f"bonus_{atributo}"), 0)
        for atributo in ATRIBUTOS_BONUS
    }


def _normalizar_golpes(
    formulario: Any,
    catalogo_golpes: dict[str, Any],
    limite: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    golpes: list[dict[str, Any]] = []
    erros: list[str] = []
    ids_usados: set[str] = set()

    nomes = formulario.getlist("golpe_nome")
    usos = formulario.getlist("golpe_usos")
    for nome, quantidade_usos in list(zip(nomes, usos))[:limite]:
        nome = str(nome).strip()
        if not nome:
            continue
        golpe = buscar_por_nome(catalogo_golpes, "golpes", nome)
        if not golpe:
            erros.append(f'O golpe "{nome}" não existe no catálogo atual.')
            continue
        golpe_id = str(golpe["id"])
        if golpe_id in ids_usados:
            erros.append(f'O golpe "{nome}" foi informado mais de uma vez.')
            continue
        ids_usados.add(golpe_id)
        golpes.append(
            {
                "golpe_id": golpe_id,
                "usos": max(0, _inteiro(quantidade_usos, 0)),
            }
        )
    return golpes, erros


def montar_pokemon_do_formulario(
    *,
    pokemon_atual: dict[str, Any] | None,
    formulario: Any,
    especie: dict[str, Any],
    regras: dict[str, Any],
    catalogo_golpes: dict[str, Any],
    estilo_combate: str,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    limites = regras.get("limites", {})
    erros: list[str] = []
    candidato = deepcopy(pokemon_atual) if pokemon_atual else {}

    nivel_min = _inteiro(limites.get("nivel_minimo"), 1)
    nivel_max = _inteiro(limites.get("nivel_maximo"), 100)
    nivel = _inteiro(formulario.get("nivel"), 1)
    if nivel < nivel_min or nivel > nivel_max:
        erros.append(f"O nível deve estar entre {nivel_min} e {nivel_max}.")

    amizade_min = _inteiro(limites.get("amizade_minima"), 0)
    amizade_max = _inteiro(limites.get("amizade_maxima"), 100)
    amizade = _inteiro(formulario.get("amizade"), 1)
    if amizade < amizade_min or amizade > amizade_max:
        erros.append(f"A amizade deve estar entre {amizade_min} e {amizade_max}.")

    generos = set(str(item) for item in regras.get("generos", []))
    genero = str(formulario.get("genero", "Ø")).strip() or "Ø"
    if generos and genero not in generos:
        erros.append("Selecione um gênero disponível na configuração atual.")

    natureza = str(formulario.get("natureza", "Dócil")).strip() or "Dócil"
    if natureza not in _opcoes(regras, "naturezas"):
        erros.append("Selecione uma natureza disponível na configuração atual.")

    status = str(formulario.get("status", "Nenhum")).strip() or "Nenhum"
    if status not in _opcoes(regras, "status"):
        erros.append("Selecione um status disponível na configuração atual.")

    limite_golpes = _inteiro(limites.get("golpes_por_pokemon"), 4)
    golpes, erros_golpes = _normalizar_golpes(
        formulario, catalogo_golpes, limite_golpes
    )
    erros.extend(erros_golpes)

    candidato.update(
        {
            "especie_id": str(especie["id"]),
            "apelido": str(formulario.get("apelido", "")).strip(),
            "genero": genero,
            "nivel": nivel,
            "experiencia": max(0, _inteiro(formulario.get("experiencia"), 0)),
            "amizade": amizade,
            "shiny": formulario.get("shiny") == "1",
            "natureza": natureza,
            "status": status,
            "item_carregado": str(formulario.get("item_carregado", "")).strip(),
            "bonus": _normalizar_bonus(formulario),
            "golpes": golpes,
            "anotacoes": str(formulario.get("anotacoes", "")).strip(),
            "atualizado_em": agora_iso(),
        }
    )

    calculos = calcular_atributos_pokemon(
        pokemon=candidato,
        especie=especie,
        regras=regras,
        estilo_combate=estilo_combate,
        golpes_catalogo=indexar_catalogo(catalogo_golpes, "golpes"),
    )

    pv_maximo = calculos["totais"]["pv"]
    pv_padrao = _inteiro(candidato.get("pv_atual"), pv_maximo)
    pv_atual = _inteiro(formulario.get("pv_atual"), pv_padrao)
    if pv_atual < 0 or pv_atual > pv_maximo:
        erros.append(f"Os PV atuais devem estar entre 0 e {pv_maximo}.")
    candidato["pv_atual"] = max(0, min(pv_atual, pv_maximo))

    if calculos.get("pp_excedente", 0) > 0:
        erros.append(
            "O total de PP gasto pelos usos dos golpes ultrapassa o PP máximo do Pokémon."
        )

    if "id" not in candidato:
        base = estrutura_pokemon_padrao(
            especie_id=str(especie["id"]),
            pv_maximo=pv_maximo,
            natureza=natureza,
        )
        base.update(candidato)
        candidato = base

    return candidato, calculos, erros


def criar_pokemon_na_equipe(
    *,
    jogador: dict[str, Any],
    especie: dict[str, Any],
    regras: dict[str, Any],
) -> dict[str, Any]:
    garantir_estrutura_pokemon(jogador)
    pokemon_base = {
        "nivel": 1,
        "shiny": False,
        "natureza": "Dócil",
        "status": "Nenhum",
        "bonus": {atributo: 0 for atributo in ATRIBUTOS_BONUS},
        "golpes": [],
    }
    calculos = calcular_atributos_pokemon(
        pokemon=pokemon_base,
        especie=especie,
        regras=regras,
    )
    pokemon = estrutura_pokemon_padrao(
        especie_id=str(especie["id"]),
        pv_maximo=calculos["totais"]["pv"],
    )
    jogador["pokemons"].append(pokemon)
    jogador["equipe"].append(pokemon["id"])
    return pokemon


def remover_pokemon(jogador: dict[str, Any], pokemon_id: str) -> bool:
    garantir_estrutura_pokemon(jogador)
    quantidade_antes = len(jogador["pokemons"])
    jogador["pokemons"] = [
        item for item in jogador["pokemons"] if str(item.get("id")) != pokemon_id
    ]
    jogador["equipe"] = [item for item in jogador["equipe"] if str(item) != pokemon_id]
    for box in jogador.get("boxes", []):
        box["pokemon_ids"] = [
            item for item in box.get("pokemon_ids", []) if str(item) != pokemon_id
        ]
    return len(jogador["pokemons"]) < quantidade_antes


def equipe_detalhada(
    *,
    jogador: dict[str, Any],
    catalogo_pokemons: dict[str, Any],
    catalogo_golpes: dict[str, Any],
    regras: dict[str, Any],
) -> list[dict[str, Any]]:
    garantir_estrutura_pokemon(jogador)
    especies = indexar_catalogo(catalogo_pokemons, "pokemons")
    golpes = indexar_catalogo(catalogo_golpes, "golpes")
    pokemons = {
        str(item.get("id")): item
        for item in jogador.get("pokemons", [])
        if isinstance(item, dict)
    }
    estilo = str(jogador.get("treinador", {}).get("estilo_combate", ""))
    resultado: list[dict[str, Any]] = []

    for pokemon_id in jogador.get("equipe", []):
        pokemon = pokemons.get(str(pokemon_id))
        if not pokemon:
            continue
        especie = especies.get(str(pokemon.get("especie_id")))
        if not especie:
            continue
        calculos = calcular_atributos_pokemon(
            pokemon=pokemon,
            especie=especie,
            regras=regras,
            estilo_combate=estilo,
            golpes_catalogo=golpes,
        )
        resultado.append(
            {
                "pokemon": pokemon,
                "especie": especie,
                "calculos": calculos,
            }
        )
    return resultado
