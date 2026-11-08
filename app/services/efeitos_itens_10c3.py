"""Aplica apenas efeitos terapêuticos estruturados aos Pokémon do treinador.

Não executa expressões arbitrárias nem altera mecânicas de batalha/PP.
Executado dentro da transação de inventário; o chamador faz commit único.
"""
from __future__ import annotations

import re
import secrets
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import Pokemon, PokemonStatus, StatusCondicao
from app.services.pokemon_db_service import calcular_pokemon, carregar_regras_pokemon_db

TIPOS_TERAPEUTICOS = {"recuperar_pv", "remover_status"}
_DADOS = re.compile(r"^([1-9][0-9]?)d([1-9][0-9]{0,2})(?:\+([0-9]{1,4}))?$", re.I)


def efeitos_estruturados(item: Any) -> list[dict]:
    bruto = getattr(item, "efeitos", None)
    if not isinstance(bruto, dict):
        return []
    efeitos = bruto.get("efeitos")
    return [e for e in efeitos if isinstance(e, dict)] if isinstance(efeitos, list) else []


def exige_alvo_pokemon(item: Any) -> bool:
    return any(e.get("tipo") in TIPOS_TERAPEUTICOS for e in efeitos_estruturados(item))


def quantidade_recuperada(efeito: dict, maximo: int, *, rolar=None) -> int:
    modo = efeito.get("operacao", "fixo")
    if modo == "fixo":
        valor = int(efeito.get("valor") or 0)
        if not 0 < valor <= 999999:
            raise ValueError("Quantidade de PV inválida no item.")
        return valor
    if modo == "percentual":
        valor = Decimal(str(efeito.get("valor") or 0))
        if not Decimal(0) < valor <= Decimal(100):
            raise ValueError("Percentual de cura inválido.")
        return max(1, int(Decimal(maximo) * valor / Decimal(100)))
    if modo == "dados":
        exp = str(efeito.get("expressao") or "").strip().lower().replace(" ", "")
        m = _DADOS.fullmatch(exp)
        if not m:
            raise ValueError("Expressão de dados inválida para cura.")
        n, faces, bonus = (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
        if n > 20 or faces > 100 or bonus > 1000:
            raise ValueError("Expressão de dados excede o limite permitido.")
        rodar = rolar or (lambda f: secrets.randbelow(f) + 1)
        return sum(rodar(faces) for _ in range(n)) + bonus
    raise ValueError("Operação de recuperação de PV não suportada.")


def aplicar_efeitos_terapeuticos(*, item: Any, personagem: Any, pokemon_id: Any, quantidade: int) -> dict:
    """Não grava commit nem consome o item. Rejeita usos sem efeito real."""
    from uuid import UUID
    try:
        identificador = UUID(str(pokemon_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Selecione o Pokémon que receberá o item.") from None
    pokemon = db.session.execute(
        select(Pokemon)
        .where(Pokemon.id == identificador, Pokemon.personagem_id == personagem.id, Pokemon.ativo.is_(True))
        .options(selectinload(Pokemon.forma_pokemon), selectinload(Pokemon.status_ativos))
        .with_for_update()
    ).scalar_one_or_none()
    if pokemon is None:
        raise ValueError("Pokémon inválido ou não pertencente ao personagem.")

    efeitos = efeitos_estruturados(item)
    terapia = [e for e in efeitos if e.get("tipo") in TIPOS_TERAPEUTICOS]
    if not terapia:
        raise ValueError("O item não possui efeitos terapêuticos configurados.")
    if any(e.get("alvo", "pokemon") != "pokemon" for e in terapia):
        raise ValueError("Nesta etapa, os efeitos de cura só são permitidos para Pokémon.")

    precisa_pv = any(e["tipo"] == "recuperar_pv" for e in terapia)
    maximo = None
    if precisa_pv:
        try:
            regras = carregar_regras_pokemon_db(personagem.campanha_id)
            maximo = int(calcular_pokemon(pokemon, personagem, regras)["totais"]["pv"])
        except (ValueError, KeyError, TypeError, AttributeError, ArithmeticError) as exc:
            raise ValueError("Não foi possível calcular o PV máximo deste Pokémon.") from exc
        if maximo <= 0:
            raise ValueError("O Pokémon não possui PV máximo válido.")

    # Validação de todos os status ANTES de mudar qualquer dado; falhas fazem rollback.
    ids_status = set()
    todos = False
    for efeito in terapia:
        if efeito["tipo"] != "remover_status":
            continue
        if efeito.get("todos"):
            todos = True
        elif efeito.get("status_id"):
            try: ids_status.add(UUID(str(efeito["status_id"])))
            except (ValueError, TypeError): raise ValueError("Status configurado no item é inválido.") from None
        else:
            raise ValueError("Configure um status específico ou 'Todos' no catálogo.")
    if ids_status:
        encontrados = set(db.session.execute(
            select(StatusCondicao.id).where(StatusCondicao.id.in_(ids_status), StatusCondicao.ativo.is_(True))
        ).scalars())
        if encontrados != ids_status:
            raise ValueError("Item refere-se a uma condição inexistente/inativa.")

    antes = {"pokemon_id":str(pokemon.id),"pv":int(pokemon.pv_atual),"status_ids":[str(s.status_id) for s in pokemon.status_ativos]}
    pv = int(pokemon.pv_atual)
    ativos = {s.status_id:s for s in pokemon.status_ativos}
    removidos = set()
    for _ in range(quantidade):
        houve_efeito = False
        for efeito in terapia:
            if efeito["tipo"] == "recuperar_pv":
                recuperado = quantidade_recuperada(efeito, maximo)
                destino = min(maximo, pv + recuperado)
                if destino > pv:
                    pv = destino
                    houve_efeito = True
            elif efeito["tipo"] == "remover_status":
                elegiveis = set(ativos) if todos or efeito.get("todos") else ids_status
                for sid in elegiveis & set(ativos):
                    removidos.add(sid)
                    ativos.pop(sid)
                    houve_efeito = True
        if not houve_efeito:
            raise ValueError("O Pokémon já está recuperado ou não possui a condição necessária. Nenhum item foi gasto.")
    pokemon.pv_atual = pv
    for registro in pokemon.status_ativos:
        if registro.status_id in removidos:
            db.session.delete(registro)
    return {"antes":antes,"depois":{"pokemon_id":str(pokemon.id),"pv":pv,"status_ids":[str(s) for s in ativos]},"pv_recuperado":pv-antes["pv"],"status_removidos":[str(s) for s in sorted(removidos,key=str)]}
