"""Criação e controle de NPCs e hordas (somente mestre).

Registros temporários do Campo. Nunca cria Personagem, Pokemon ou Capturavel.
Mutações usam lock na campanha para serialização com o Campo existente.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Campanha, FormaPokemon, FormaPokemonAtributo, FormaPokemonTipo,
    GrupoNPCEmCampo, HistoricoAlteracao, PokemonNPCEmCampo,
)
from app.services.calculo_atributos import calcular_progressao
from app.services.pokemon_db_service import carregar_regras_pokemon_db

MAX_GRUPOS = 40
MAX_POKEMONS = 80
MAX_GRUPO = 24
MAX_LOTE = 12


def _uuid(valor):
    try:
        return uuid.UUID(str(valor))
    except (ValueError, TypeError, AttributeError):
        return None


def _numero(valor, *, minimo, maximo, nome):
    entrada = str(valor).strip()
    if not entrada.isascii() or not entrada.isdecimal():
        raise ValueError(f"{nome}: informe um número inteiro válido.")
    numero = int(entrada)
    if numero < minimo or numero > maximo:
        raise ValueError(f"{nome}: permitido de {minimo} a {maximo}.")
    return numero


def _campanha(codigo, *, bloquear=True):
    consulta = select(Campanha).where(Campanha.codigo == codigo, Campanha.ativo.is_(True))
    if bloquear:
        consulta = consulta.with_for_update()
    campanha = db.session.execute(consulta).scalar_one_or_none()
    if campanha is None:
        raise ValueError("Campanha não encontrada ou inativa.")
    return campanha


def _grupo(campanha_id, grupo_id):
    uid = _uuid(grupo_id)
    if uid is None:
        raise ValueError("Grupo inválido.")
    grupo = db.session.execute(
        select(GrupoNPCEmCampo)
        .where(GrupoNPCEmCampo.id == uid, GrupoNPCEmCampo.campanha_id == campanha_id)
    ).scalar_one_or_none()
    if grupo is None:
        raise ValueError("Grupo não encontrado nesta campanha.")
    return grupo


def _forma(forma_id):
    uid = _uuid(forma_id)
    if uid is None:
        raise ValueError("Selecione uma espécie/forma válida no catálogo.")
    forma = db.session.execute(
        select(FormaPokemon)
        .where(FormaPokemon.id == uid, FormaPokemon.ativo.is_(True))
        .options(
            selectinload(FormaPokemon.atributos_base).selectinload(FormaPokemonAtributo.atributo)
        )
    ).scalar_one_or_none()
    if forma is None:
        raise ValueError("Espécie/forma não encontrada ou inativa.")
    return forma


def _pv_maximo(forma, nivel, regras):
    bases = [
        int(rel.valor_base) for rel in forma.atributos_base
        if rel.atributo and rel.atributo.ativo
        and rel.atributo.codigo.replace("-", "_") == "pv"
    ]
    if not bases:
        raise ValueError("A espécie selecionada não tem PV base configurado.")
    return max(1, calcular_progressao(bases[0], nivel, regras.get("progressao_pv", [])))


def _limites(campanha_id, *, novos_grupos=0, novos_pokemons=0, grupo=None):
    grupos = db.session.scalar(
        select(func.count()).select_from(GrupoNPCEmCampo).where(GrupoNPCEmCampo.campanha_id == campanha_id)
    ) or 0
    pokemons = db.session.scalar(
        select(func.count()).select_from(PokemonNPCEmCampo)
        .join(GrupoNPCEmCampo)
        .where(GrupoNPCEmCampo.campanha_id == campanha_id)
    ) or 0
    if grupos + novos_grupos > MAX_GRUPOS or pokemons + novos_pokemons > MAX_POKEMONS:
        raise ValueError("Limite do Campo: 40 grupos e 80 Pokémon adversários.")
    if grupo is not None:
        existentes = db.session.scalar(
            select(func.count()).select_from(PokemonNPCEmCampo)
            .where(PokemonNPCEmCampo.grupo_id == grupo.id)
        ) or 0
        if existentes + novos_pokemons > MAX_GRUPO:
            raise ValueError("Cada grupo aceita até 24 Pokémon.")


def _historico(usuario_id, registro_id, acao, antes=None, depois=None):
    db.session.add(HistoricoAlteracao(
        entidade="campo_npc", registro_id=registro_id, acao=acao,
        usuario_id=_uuid(usuario_id), dados_anteriores=antes, dados_novos=depois
    ))


def _adicionar(grupo, forma, *, nivel, quantidade, pv_maximo):
    for _ in range(quantidade):
        db.session.add(PokemonNPCEmCampo(
            grupo=grupo, forma_pokemon_id=forma.id, nivel=nivel,
            pv_atual=pv_maximo, pv_maximo=pv_maximo
        ))


def criar_grupo_npc(*, campanha_codigo, nome, tipo, time_numero, forma_id, nivel,
                    quantidade, usuario_id):
    tipo = str(tipo or "").strip().lower()
    if tipo not in ("npc", "horda"):
        raise ValueError("Escolha NPC treinador ou horda selvagem.")
    nome = str(nome or "").strip()
    if not nome or len(nome) > 120:
        raise ValueError("Informe um nome de grupo com até 120 caracteres.")
    time = _numero(time_numero, minimo=1, maximo=16, nome="Time")
    lvl = _numero(nivel, minimo=1, maximo=100, nome="Nível")
    qtd = _numero(quantidade, minimo=1, maximo=MAX_LOTE, nome="Quantidade")
    campanha = _campanha(campanha_codigo)
    _limites(campanha.id, novos_grupos=1, novos_pokemons=qtd)
    forma = _forma(forma_id)
    pv = _pv_maximo(forma, lvl, carregar_regras_pokemon_db(campanha.id))
    grupo = GrupoNPCEmCampo(campanha_id=campanha.id, nome=nome, tipo=tipo, time_numero=time)
    db.session.add(grupo)
    db.session.flush()
    _adicionar(grupo, forma, nivel=lvl, quantidade=qtd, pv_maximo=pv)
    _historico(usuario_id, grupo.id, "criar", depois={
        "nome": nome, "tipo": tipo, "time": time, "forma": str(forma.id),
        "nivel": lvl, "quantidade": qtd
    })
    db.session.commit()
    return f"{nome}: {qtd} Pokémon adicionados ao Time {time}."


def adicionar_pokemons_npc(*, campanha_codigo, grupo_id, forma_id, nivel,
                          quantidade, usuario_id):
    lvl = _numero(nivel, minimo=1, maximo=100, nome="Nível")
    qtd = _numero(quantidade, minimo=1, maximo=MAX_LOTE, nome="Quantidade")
    campanha = _campanha(campanha_codigo)
    grupo = _grupo(campanha.id, grupo_id)
    _limites(campanha.id, novos_pokemons=qtd, grupo=grupo)
    forma = _forma(forma_id)
    pv = _pv_maximo(forma, lvl, carregar_regras_pokemon_db(campanha.id))
    _adicionar(grupo, forma, nivel=lvl, quantidade=qtd, pv_maximo=pv)
    _historico(usuario_id, grupo.id, "adicionar", depois={
        "forma": str(forma.id), "nivel": lvl, "quantidade": qtd
    })
    db.session.commit()
    return f"{qtd} Pokémon adicionados a {grupo.nome}."


def mover_grupo_npc(*, campanha_codigo, grupo_id, time_numero, usuario_id):
    time = _numero(time_numero, minimo=1, maximo=16, nome="Time")
    campanha = _campanha(campanha_codigo)
    grupo = _grupo(campanha.id, grupo_id)
    if grupo.time_numero == time:
        return "O grupo já está nesse time."
    antes = grupo.time_numero
    grupo.time_numero = time
    _historico(usuario_id, grupo.id, "mover", antes={"time": antes}, depois={"time": time})
    db.session.commit()
    return f"{grupo.nome} movido para o Time {time}."


def ajustar_pv_npc(*, campanha_codigo, pokemon_id, quantidade, operacao, usuario_id):
    qtd = _numero(quantidade, minimo=1, maximo=9999, nome="PV")
    if operacao not in ("mais", "menos"):
        raise ValueError("Selecione aumentar ou reduzir PV.")
    campanha = _campanha(campanha_codigo)
    uid = _uuid(pokemon_id)
    if uid is None:
        raise ValueError("Pokémon adversário inválido.")
    pokemon = db.session.execute(
        select(PokemonNPCEmCampo).join(GrupoNPCEmCampo)
        .where(PokemonNPCEmCampo.id == uid, GrupoNPCEmCampo.campanha_id == campanha.id)
    ).scalar_one_or_none()
    if pokemon is None:
        raise ValueError("Pokémon adversário não encontrado nesta campanha.")
    antes = pokemon.pv_atual
    pokemon.pv_atual = max(0, min(pokemon.pv_maximo, antes + (qtd if operacao == "mais" else -qtd)))
    if antes != pokemon.pv_atual:
        _historico(usuario_id, pokemon.id, "ajustar_pv",
                   antes={"pv": antes}, depois={"pv": pokemon.pv_atual})
    db.session.commit()
    return f"PV atualizado: {pokemon.pv_atual}/{pokemon.pv_maximo}."


def retirar_pokemon_npc(*, campanha_codigo, pokemon_id, usuario_id):
    campanha = _campanha(campanha_codigo)
    uid = _uuid(pokemon_id)
    if uid is None:
        raise ValueError("Pokémon adversário inválido.")
    pokemon = db.session.execute(
        select(PokemonNPCEmCampo).join(GrupoNPCEmCampo)
        .where(PokemonNPCEmCampo.id == uid, GrupoNPCEmCampo.campanha_id == campanha.id)
    ).scalar_one_or_none()
    if pokemon is None:
        raise ValueError("Pokémon adversário não encontrado nesta campanha.")
    grupo = pokemon.grupo
    nome = grupo.nome
    db.session.delete(pokemon)
    db.session.flush()
    restantes = db.session.scalar(
        select(func.count()).select_from(PokemonNPCEmCampo)
        .where(PokemonNPCEmCampo.grupo_id == grupo.id)
    ) or 0
    if not restantes:
        db.session.delete(grupo)
    _historico(usuario_id, uid, "retirar", antes={"grupo": str(grupo.id), "nome": nome})
    db.session.commit()
    return "Pokémon adversário retirado do campo."


def remover_grupo_npc(*, campanha_codigo, grupo_id, usuario_id):
    campanha = _campanha(campanha_codigo)
    grupo = _grupo(campanha.id, grupo_id)
    nome, uid = grupo.nome, grupo.id
    db.session.delete(grupo)
    _historico(usuario_id, uid, "remover", antes={"nome": nome})
    db.session.commit()
    return f"Grupo {nome} retirado do campo."


def limpar_npcs_campo(*, campanha_id, usuario_id):
    """Remove adversários na transação do serviço principal; NÃO executa commit."""
    grupos = list(db.session.execute(
        select(GrupoNPCEmCampo).where(GrupoNPCEmCampo.campanha_id == campanha_id)
    ).scalars())
    quantidade = db.session.scalar(
        select(func.count()).select_from(PokemonNPCEmCampo)
        .join(GrupoNPCEmCampo)
        .where(GrupoNPCEmCampo.campanha_id == campanha_id)
    ) or 0
    for grupo in grupos:
        db.session.delete(grupo)
        _historico(usuario_id, grupo.id, "limpar", antes={"nome": grupo.nome})
    # Calcula antes de excluir, para não zerar a contagem com autoflush.
    return quantidade


def listar_grupos_npc(*, campanha_id):
    grupos = db.session.execute(
        select(GrupoNPCEmCampo).where(GrupoNPCEmCampo.campanha_id == campanha_id)
        .options(
            selectinload(GrupoNPCEmCampo.pokemons)
            .selectinload(PokemonNPCEmCampo.forma_pokemon)
            .selectinload(FormaPokemon.tipos).selectinload(FormaPokemonTipo.tipo)
        )
        .order_by(GrupoNPCEmCampo.time_numero, GrupoNPCEmCampo.criado_em, GrupoNPCEmCampo.id)
    ).scalars().all()
    resultado = []
    for grupo in grupos:
        membros = []
        for pokemon in grupo.pokemons:
            forma = pokemon.forma_pokemon
            imagem = forma.imagem_shiny_url if pokemon.shiny else forma.imagem_url
            tipos = [x.tipo.nome for x in forma.tipos if x.tipo and x.tipo.ativo]
            membros.append({
                "id": str(pokemon.id), "nome": forma.nome, "especie": forma.nome,
                "imagem": imagem or forma.imagem_url or "", "tipos": tipos,
                "nivel": pokemon.nivel, "pv_atual": pokemon.pv_atual,
                "pv_maximo": pokemon.pv_maximo, "shiny": pokemon.shiny,
            })
        resultado.append({
            "id": str(grupo.id), "nome": grupo.nome, "tipo": grupo.tipo,
            "time_numero": grupo.time_numero, "pokemons": membros,
        })
    return resultado
