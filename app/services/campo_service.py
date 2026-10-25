"""Serviço do painel compartilhado: consulta e ações sobre Pokémon da equipe.

Todas as mutações serializam ações da mesma campanha por lock na linha de
campanhas (PostgreSQL). Não há combate automático nem rolagens de captura.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Campanha, FormaPokemon, FormaPokemonTipo, HistoricoAlteracao,
    Personagem, Pokemon, PokemonEmCampo, Usuario,
)

TOTAL_TIMES = 16


@dataclass(slots=True)
class ContextoCampo:
    times: list[dict[str, Any]]
    opcoes_pokemon: list[dict[str, str]]
    total_pokemons: int
    times_ocupados: int


def _uuid(valor: str | uuid.UUID | None) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valor))
    except (ValueError, AttributeError, TypeError):
        return None


def _campanha(codigo: str, *, bloquear: bool = False) -> Campanha | None:
    consulta = select(Campanha).where(Campanha.codigo == codigo, Campanha.ativo.is_(True))
    if bloquear:
        consulta = consulta.with_for_update()
    return db.session.execute(consulta).scalar_one_or_none()


def _pokemon_valido(campanha_id: uuid.UUID, pokemon_id: uuid.UUID) -> Pokemon | None:
    """Restringe o campo a Pokémon ativos da equipe de treinador ativo."""
    return db.session.execute(
        select(Pokemon)
        .join(Personagem, Personagem.id == Pokemon.personagem_id)
        .join(Usuario, Usuario.id == Personagem.usuario_id)
        .where(
            Pokemon.id == pokemon_id, Pokemon.ativo.is_(True),
            Pokemon.localizacao == "equipe",
            Personagem.campanha_id == campanha_id, Personagem.ativo.is_(True),
            Usuario.ativo.is_(True),
        )
        .with_for_update(of=Pokemon)
    ).scalar_one_or_none()


def _pode_alterar(pokemon: Pokemon, *, mestre: bool, personagem_id: str | None) -> bool:
    return mestre or (
        _uuid(personagem_id) is not None and pokemon.personagem_id == _uuid(personagem_id)
    )


def _registrar_historico(
    *, usuario_id: str | None, pokemon_id: uuid.UUID, acao: str,
    antes: dict[str, Any] | None, depois: dict[str, Any] | None,
) -> None:
    db.session.add(HistoricoAlteracao(
        entidade="pokemon_em_campo", registro_id=pokemon_id, acao=acao,
        usuario_id=_uuid(usuario_id), dados_anteriores=antes, dados_novos=depois,
    ))


def posicionar_pokemon(
    *, campanha_codigo: str, pokemon_id: str,
    time_numero: str | int, mestre: bool, personagem_id: str | None,
    usuario_id: str | None,
) -> str:
    """Coloca ou move um Pokémon existente. Levanta ValueError sem commit."""
    try:
        time = int(time_numero)
    except (ValueError, TypeError):
        raise ValueError("Selecione um time entre 1 e 16.")
    if str(time_numero).strip() != str(time) or not 1 <= time <= TOTAL_TIMES:
        raise ValueError("Selecione um time entre 1 e 16.")
    identificador = _uuid(pokemon_id)
    if identificador is None:
        raise ValueError("Selecione um Pokémon válido da equipe.")

    campanha = _campanha(campanha_codigo, bloquear=True)
    if campanha is None:
        raise ValueError("Campanha não encontrada.")
    pokemon = _pokemon_valido(campanha.id, identificador)
    if pokemon is None:
        raise ValueError("Este Pokémon não está disponível na equipe.")
    if not _pode_alterar(pokemon, mestre=mestre, personagem_id=personagem_id):
        raise PermissionError("Você só pode posicionar Pokémon da sua própria equipe.")

    registro = db.session.execute(
        select(PokemonEmCampo)
        .where(PokemonEmCampo.campanha_id == campanha.id, PokemonEmCampo.pokemon_id == identificador)
    ).scalar_one_or_none()
    if registro is not None and registro.time_numero == time:
        return "O Pokémon já está nesse time."
    anterior = {"time": registro.time_numero} if registro is not None else None
    if registro is None:
        registro = PokemonEmCampo(campanha_id=campanha.id, pokemon_id=identificador, time_numero=time)
        db.session.add(registro)
    else:
        registro.time_numero = time
    _registrar_historico(
        usuario_id=usuario_id, pokemon_id=identificador,
        acao="posicionar" if anterior is None else "mudar_time",
        antes=anterior, depois={"time": time},
    )
    db.session.commit()
    return f"Pokémon colocado no Time {time}."


def retirar_pokemon(
    *, campanha_codigo: str, pokemon_id: str,
    mestre: bool, personagem_id: str | None, usuario_id: str | None,
) -> bool:
    identificador = _uuid(pokemon_id)
    if identificador is None:
        return False
    campanha = _campanha(campanha_codigo, bloquear=True)
    if campanha is None:
        return False
    registro = db.session.execute(
        select(PokemonEmCampo)
        .where(PokemonEmCampo.pokemon_id == identificador, PokemonEmCampo.campanha_id == campanha.id)
    ).scalar_one_or_none()
    if registro is None:
        return False
    pokemon = db.session.get(Pokemon, identificador)
    if pokemon is None or not _pode_alterar(pokemon, mestre=mestre, personagem_id=personagem_id):
        raise PermissionError("Você só pode retirar Pokémon da sua própria equipe.")
    time = registro.time_numero
    db.session.delete(registro)
    _registrar_historico(
        usuario_id=usuario_id, pokemon_id=identificador,
        acao="retirar", antes={"time": time}, depois=None,
    )
    db.session.commit()
    return True


def limpar_campo(*, campanha_codigo: str, usuario_id: str | None) -> int:
    campanha = _campanha(campanha_codigo, bloquear=True)
    if campanha is None:
        return 0
    registros = list(db.session.execute(
        select(PokemonEmCampo).where(PokemonEmCampo.campanha_id == campanha.id)
    ).scalars())
    for item in registros:
        db.session.delete(item)
        _registrar_historico(
            usuario_id=usuario_id, pokemon_id=item.pokemon_id,
            acao="retirar", antes={"time": item.time_numero}, depois={"campo_limpo": True},
        )
    db.session.commit()
    return len(registros)


def carregar_campo(
    *, campanha_codigo: str, mestre: bool,
    personagem_id: str | None,
) -> ContextoCampo:
    campanha = _campanha(campanha_codigo)
    times = [{"numero": numero, "pokemons": []} for numero in range(1, TOTAL_TIMES + 1)]
    if campanha is None:
        return ContextoCampo(times=times, opcoes_pokemon=[], total_pokemons=0, times_ocupados=0)

    campos = list(db.session.execute(
        select(PokemonEmCampo)
        .join(Pokemon, Pokemon.id == PokemonEmCampo.pokemon_id)
        .join(Personagem, Personagem.id == Pokemon.personagem_id)
        .join(Usuario, Usuario.id == Personagem.usuario_id)
        .where(
            PokemonEmCampo.campanha_id == campanha.id,
            Pokemon.ativo.is_(True), Pokemon.localizacao == "equipe",
            Personagem.campanha_id == campanha.id, Personagem.ativo.is_(True), Usuario.ativo.is_(True),
        )
        .options(
            selectinload(PokemonEmCampo.pokemon).selectinload(Pokemon.forma_pokemon)
            .selectinload(FormaPokemon.tipos).selectinload(FormaPokemonTipo.tipo),
            selectinload(PokemonEmCampo.pokemon).selectinload(Pokemon.personagem),
        )
        .order_by(PokemonEmCampo.time_numero, PokemonEmCampo.criado_em, PokemonEmCampo.id)
    ).scalars())

    campo_ids: set[uuid.UUID] = set()
    for item in campos:
        pokemon = item.pokemon
        forma = pokemon.forma_pokemon
        campo_ids.add(pokemon.id)
        imagem = (forma.imagem_shiny_url if pokemon.shiny else forma.imagem_url) or forma.imagem_url or forma.imagem_shiny_url or ""
        tipos = [rel.tipo.nome for rel in forma.tipos if rel.tipo and rel.tipo.ativo]
        times[item.time_numero - 1]["pokemons"].append({
            "id": str(pokemon.id),
            "nome": pokemon.apelido or forma.nome,
            "especie": forma.nome,
            "imagem": imagem,
            "tipos": tipos,
            "treinador": pokemon.personagem.nome,
            "shiny": bool(pokemon.shiny),
            "pv_atual": pokemon.pv_atual,
            "pode_retirar": _pode_alterar(pokemon, mestre=mestre, personagem_id=personagem_id),
        })

    opcoes = list(db.session.execute(
        select(Pokemon)
        .join(Personagem, Personagem.id == Pokemon.personagem_id)
        .join(Usuario, Usuario.id == Personagem.usuario_id)
        .where(
            Personagem.campanha_id == campanha.id, Personagem.ativo.is_(True), Usuario.ativo.is_(True),
            Pokemon.ativo.is_(True), Pokemon.localizacao == "equipe",
            *( [] if mestre else [Pokemon.personagem_id == _uuid(personagem_id)] ),
        )
        .options(selectinload(Pokemon.forma_pokemon), selectinload(Pokemon.personagem))
        .order_by(func.lower(Personagem.nome), Pokemon.posicao)
    ).scalars())
    return ContextoCampo(
        times=times,
        opcoes_pokemon=[{
            "id": str(p.id),
            "rotulo": f"{p.personagem.nome} · {p.apelido or p.forma_pokemon.nome}" + (" (em campo)" if p.id in campo_ids else ""),
        } for p in opcoes],
        total_pokemons=len(campos),
        times_ocupados=sum(bool(item["pokemons"]) for item in times),
    )
