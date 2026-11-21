"""10E.3.3/4 — Evolução permanente opt-in, atômica e com trilha de auditoria.

Chamador deve COMMIT/ROLLBACK. Revalida identidade, autorização,
nível e inventário sob locks; falha fechada em materiais ambíguos.
Não implementa Mega ou mudanças temporárias de forma.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    AutorizacaoEvolucaoPokemon, EvolucaoPokemon, FormaPokemon,
    HistoricoAlteracao, Item, Personagem, PersonagemItem, Pokemon,
    PokemonEmCampo, Usuario,
)
from app.services.autorizacao_evolucao_service import invalidar_autorizacoes_por_troca_forma
from app.services.consulta_evolucao_service import _tem_condicoes_especiais
from app.services.materiais_evolucao_service import (
    MaterialEvolucao, item_corresponde_material, material_requerido_evolucao,
)
from app.services.pokemon_db_service import calcular_pokemon, carregar_regras_pokemon_db


@dataclass(frozen=True, slots=True)
class ResultadoEvolucao:
    pokemon_id: uuid.UUID
    origem_nome: str
    destino_nome: str
    forma_destino_id: uuid.UUID
    pv_anterior: int
    pv_novo: int
    pv_maximo_anterior: int
    pv_maximo_novo: int
    item_consumido: str | None


def _uuid(valor: uuid.UUID | str, tipo: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"Identificador de {tipo} inválido.") from exc


def _nivel_minimo(tipo: str, req: dict) -> int | None:
    campos = ("nivel_informativo", "nivel") if tipo != "nivel" else ("nivel", "nivel_informativo")
    valores: list[int] = []
    for campo in campos:
        bruto = req.get(campo)
        if bruto is None or bruto == "":
            continue
        if isinstance(bruto, bool) or not str(bruto).isdigit():
            raise ValueError("Nível evolutivo inválido: revisão do mestre necessária.")
        numero = int(bruto)
        if numero < 1 or numero > 999:
            raise ValueError("Nível evolutivo fora dos limites.")
        valores.append(numero)
    if tipo == "nivel" and not valores:
        raise ValueError("Evolução sem nível mínimo cadastrado.")
    return max(valores) if valores else None


def _consumir_material(
    *, personagem_id: uuid.UUID, pokemon_id: uuid.UUID,
    material: MaterialEvolucao, usuario_id: uuid.UUID,
) -> str:
    """Desconta somente a mochila real com lock, sem COMMIT parcial."""
    registros = list(db.session.scalars(
        select(PersonagemItem)
        .join(Item, Item.id == PersonagemItem.item_id)
        .where(
            PersonagemItem.personagem_id == personagem_id,
            PersonagemItem.quantidade > 0,
            Item.ativo.is_(True),
        )
        .options(selectinload(PersonagemItem.item))
        .order_by(Item.codigo, PersonagemItem.id)
        .with_for_update(of=PersonagemItem)
    ).all())
    encontrados = [r for r in registros if item_corresponde_material(
        r.item.codigo, r.item.nome, material
    )]
    if not encontrados:
        raise ValueError(f"Material necessário ausente na mochila: {material.nome}.")
    validos = [r for r in encontrados if r.item.consumivel]
    if not validos:
        raise ValueError(
            f"{material.nome} não está marcado como consumível no catálogo. "
            "Solicite revisão do item ao mestre."
        )
    registro = validos[0]
    antes = registro.quantidade
    registro.quantidade -= 1
    depois = registro.quantidade
    db.session.add(HistoricoAlteracao(
        usuario_id=usuario_id,
        entidade="personagem_item",
        registro_id=registro.id,
        acao="consumo_evolucao",
        dados_anteriores={
            "personagem_id": str(personagem_id),
            "item_id": str(registro.item_id),
            "quantidade": antes,
        },
        dados_novos={
            "pokemon_id": str(pokemon_id),
            "item_id": str(registro.item_id),
            "quantidade": depois,
            "consumido": 1,
            "motivo": "evolucao_pokemon",
        },
    ))
    if registro.quantidade == 0:
        db.session.delete(registro)
    return registro.item.nome


def _autorizacao_vigente(pokemon: Pokemon, relacao: EvolucaoPokemon) -> bool:
    return db.session.scalar(
        select(AutorizacaoEvolucaoPokemon.id).where(
            AutorizacaoEvolucaoPokemon.pokemon_id == pokemon.id,
            AutorizacaoEvolucaoPokemon.relacao_id == relacao.id,
            AutorizacaoEvolucaoPokemon.forma_origem_id == pokemon.forma_pokemon_id,
            AutorizacaoEvolucaoPokemon.ativo.is_(True),
            AutorizacaoEvolucaoPokemon.revogado_em.is_(None),
        ).with_for_update()
    ) is not None


def evoluir_pokemon(
    *, pokemon_id: uuid.UUID | str, relacao_id: uuid.UUID | str,
    personagem_id: uuid.UUID | str, campanha_id: uuid.UUID | str,
    usuario_id: uuid.UUID | str,
) -> ResultadoEvolucao:
    """Executa evolução com validações sob lock e flush; NÃO faz COMMIT."""
    pid = _uuid(pokemon_id, "Pokémon")
    rid = _uuid(relacao_id, "evolução")
    dono_id = _uuid(personagem_id, "treinador")
    cid = _uuid(campanha_id, "campanha")
    uid = _uuid(usuario_id, "usuário")

    usuario = db.session.get(Usuario, uid)
    # 'tester' acessa a própria ficha com perfil de sessão 'jogador'.
    # Manter a propriedade no Personagem.usuario_id (validada abaixo).
    if usuario is None or not usuario.ativo or usuario.perfil not in {"jogador", "tester"}:
        raise PermissionError("A evolução exige um jogador ou tester ativo, dono do Pokémon.")

    personagem = db.session.scalar(select(Personagem).where(
        Personagem.id == dono_id,
        Personagem.campanha_id == cid,
        Personagem.usuario_id == uid,
        Personagem.ativo.is_(True),
    ).with_for_update())
    if personagem is None or not personagem.campanha.ativo:
        raise PermissionError("Treinador inexistente, inativo ou fora desta campanha.")

    pokemon = db.session.scalar(select(Pokemon).where(
        Pokemon.id == pid,
        Pokemon.personagem_id == personagem.id,
        Pokemon.ativo.is_(True),
    ).with_for_update())
    if pokemon is None:
        raise ValueError("Pokémon não encontrado na ficha deste treinador.")
    if pokemon.forma_temporaria_id is not None:
        raise ValueError("Reverta a transformação temporária antes da evolução permanente.")

    relacao = db.session.get(EvolucaoPokemon, rid)
    if relacao is None or not relacao.ativo or relacao.forma_origem_id != pokemon.forma_pokemon_id:
        raise ValueError("A evolução não é mais válida para a forma atual.")
    req = relacao.requisitos if isinstance(relacao.requisitos, dict) else {}
    if req.get("tipo_relacao", "evolucao") != "evolucao":
        raise ValueError("Mega Evoluções e mudanças temporárias não são permitidas nesta etapa.")

    destino = db.session.scalar(
        select(FormaPokemon)
        .options(selectinload(FormaPokemon.atributos_base), selectinload(FormaPokemon.especie))
        .where(FormaPokemon.id == relacao.forma_destino_id)
    )
    origem = pokemon.forma_pokemon
    if (
        destino is None or not destino.ativo or destino.especie is None
        or not destino.especie.ativo or destino.id == origem.id
    ):
        raise ValueError("Destino evolutivo indisponível ou incompatível.")
    if not any(
        a.atributo.codigo in ("pv", "saude", "saúde") for a in destino.atributos_base
    ):
        raise ValueError("Destino sem atributo base de PV: revisão do catálogo necessária.")

    nivel_necessario = _nivel_minimo(relacao.tipo_requisito, req)
    if nivel_necessario is not None and personagem.nivel < nivel_necessario:
        raise ValueError(
            f"É necessário nível {nivel_necessario} do treinador; "
            f"nível atual: {personagem.nivel}."
        )
    especial = _tem_condicoes_especiais(relacao, req)
    if especial and not _autorizacao_vigente(pokemon, relacao):
        raise ValueError("Esta evolução exige liberação individual vigente do mestre.")

    material = material_requerido_evolucao(relacao.tipo_requisito, req)
    regras = carregar_regras_pokemon_db(personagem.campanha_id)
    pv_max_anterior = int(calcular_pokemon(pokemon, personagem, regras)["totais"].get("pv", 0))
    if pv_max_anterior < 1:
        raise ValueError("Não foi possível calcular os PV da forma anterior.")
    pv_atual_anterior = pokemon.pv_atual
    if pv_atual_anterior < 0:
        raise ValueError("Os PV atuais do Pokémon estão inválidos.")
    dano_atual = max(0, pv_max_anterior - min(pv_atual_anterior, pv_max_anterior))

    item_consumido = None
    if material is not None:
        item_consumido = _consumir_material(
            personagem_id=personagem.id, pokemon_id=pokemon.id,
            material=material, usuario_id=uid,
        )

    pokemon.forma_pokemon_id = destino.id
    db.session.flush()
    # Troca de FK não atualiza automaticamente a relação já carregada.
    db.session.expire(pokemon, ["forma_pokemon"])
    pv_max_novo = int(calcular_pokemon(pokemon, personagem, regras)["totais"].get("pv", 0))
    if pv_max_novo < 1:
        raise ValueError("A nova forma não possui PV válidos.")
    # Mantém os danos já sofridos; não cura desmaios automaticamente.
    pv_novo = 0 if pv_atual_anterior == 0 else max(1, pv_max_novo - dano_atual)
    pokemon.pv_atual = min(pv_max_novo, pv_novo)

    # Concessões antigas de todos os ramos deixam de valer após evoluir.
    invalidar_autorizacoes_por_troca_forma(
        pokemon, usuario_id=uid,
        motivo="Forma alterada pela evolução; autorização narrativa encerrada.",
    )

    db.session.add(HistoricoAlteracao(
        usuario_id=uid,
        entidade="pokemon",
        registro_id=pokemon.id,
        acao="evolucao",
        dados_anteriores={
            "forma_pokemon_id": str(origem.id),
            "pv_atual": pv_atual_anterior,
            "pv_maximo": pv_max_anterior,
        },
        dados_novos={
            "forma_pokemon_id": str(destino.id),
            "pv_atual": pokemon.pv_atual,
            "pv_maximo": pv_max_novo,
            "relacao_id": str(relacao.id),
            "material_consumido": item_consumido,
            "nivel_treinador": personagem.nivel,
        },
    ))
    db.session.flush()
    return ResultadoEvolucao(
        pokemon_id=pokemon.id,
        origem_nome=origem.nome,
        destino_nome=destino.nome,
        forma_destino_id=destino.id,
        pv_anterior=pv_atual_anterior,
        pv_novo=pokemon.pv_atual,
        pv_maximo_anterior=pv_max_anterior,
        pv_maximo_novo=pv_max_novo,
        item_consumido=item_consumido,
    )
