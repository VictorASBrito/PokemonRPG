"""Espelhamento transacional de Capturáveis no Campo (horda).

O campo é uma representação do mesmo encontro, não um segundo sorteio:
natureza, sexo e Shiny são copiados do registro capturável. Não executa commit.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import GrupoNPCEmCampo, PokemonNPCEmCampo
from app.services.campo_npc_service import _forma, _limites, _pv_maximo, _historico
from app.services.pokemon_db_service import carregar_regras_pokemon_db

LOCAL_ESPALHAMENTO = "__capturaveis__"
TIME_PADRAO = 16
NOME_HORDA = "Horda dos Capturáveis"


def espelhar_capturavel_campo(*, campanha, capturavel, encontrador,
                             usuario_id):
    """Uma horda por campanha recebe os capturáveis novos no Time 16.

    Lançar ValueError faz rollback da criação inteira se o Campo estiver cheio.
    Isso garante o requisito de não gerar Capturável sem NPC correspondente.
    """
    existente = db.session.scalar(
        select(PokemonNPCEmCampo.id).where(PokemonNPCEmCampo.capturavel_id == capturavel.id)
    )
    if existente is not None:
        return
    nivel = max(1, min(100, int(encontrador.nivel)))
    # Separar por nível evita misturar níveis de treinadores diferentes.
    identificador = f"{LOCAL_ESPALHAMENTO}-{nivel}"
    grupo = db.session.execute(
        select(GrupoNPCEmCampo).where(
            GrupoNPCEmCampo.campanha_id == campanha.id,
            GrupoNPCEmCampo.tipo == "horda",
            GrupoNPCEmCampo.local_id == identificador,
        )
    ).scalar_one_or_none()
    _limites(
        campanha.id, novos_grupos=0 if grupo else 1, novos_pokemons=1,
        grupo=grupo
    )
    if grupo is None:
        grupo = GrupoNPCEmCampo(
            campanha_id=campanha.id, nome=f"{NOME_HORDA} · Nv. {nivel}", tipo="horda",
            time_numero=TIME_PADRAO, local_id=identificador,
            zona_nome="Capturáveis", terreno="Encontro",
        )
        db.session.add(grupo)
        db.session.flush()
    forma = _forma(str(capturavel.forma_pokemon_id))
    pv = _pv_maximo(forma, nivel, carregar_regras_pokemon_db(campanha.id))
    pokemon = PokemonNPCEmCampo(
        grupo_id=grupo.id,
        capturavel_id=capturavel.id,
        forma_pokemon_id=forma.id, nivel=nivel,
        pv_atual=pv, pv_maximo=pv,
        natureza_id=capturavel.natureza_id,
        genero=capturavel.genero, shiny=bool(capturavel.shiny),
        enviado_captura=True,
    )
    db.session.add(pokemon)
    db.session.flush()
    _historico(
        usuario_id, pokemon.id, "espelhar_capturavel",
        depois={"capturavel_id": str(capturavel.id), "time": grupo.time_numero},
    )


def retirar_espelho_capturavel(*, campanha_id, capturavel_id, usuario_id):
    """Desativa a representação no Campo ao atribuir/remover o Capturável.

    Não afeta o registro capturável; operação sem commit e idempotente.
    """
    pokemon = db.session.execute(
        select(PokemonNPCEmCampo).join(GrupoNPCEmCampo)
        .where(
            PokemonNPCEmCampo.capturavel_id == capturavel_id,
            GrupoNPCEmCampo.campanha_id == campanha_id,
        )
    ).scalar_one_or_none()
    if pokemon is None:
        return
    grupo = pokemon.grupo
    uid = pokemon.id
    db.session.delete(pokemon)
    db.session.flush()
    restante = db.session.scalar(
        select(func.count()).select_from(PokemonNPCEmCampo)
        .where(PokemonNPCEmCampo.grupo_id == grupo.id)
    ) or 0
    if not restante:
        db.session.delete(grupo)
    _historico(usuario_id, uid, "retirar_espelho",
               antes={"capturavel_id": str(capturavel_id)})
