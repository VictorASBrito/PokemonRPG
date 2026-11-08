"""10D.2 — Cura administrativa de Pokémon da campanha, sem migration.

Usar apenas em endpoints autenticados com perfil mestre e CSRF. Inclui equipe e Box;
a alteração de PV e remoção de condições é atômica por requisição.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import Campanha, HistoricoAlteracao, Personagem, Pokemon, Usuario
from app.services.pokemon_db_service import calcular_pokemon, carregar_contexto_pokemon


def _uuid(valor):
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError, AttributeError):
        return None


def curar_pokemons_mestre(*, campanha_codigo: str, usuario_id: str | None,
                         personagem_id: str | None = None) -> dict:
    """Restaura PV e remove condições; inclui Box. Confirma escopo na consulta.

    Alvos: personagens ativos de contas jogador/tester da campanha ativa.
    Inclui personagens ativos mesmo que a conta esteja desativada; a cura
    não altera acesso. Operação idempotente quanto aos PV e condições.
    """
    campanha = db.session.execute(
        select(Campanha).where(Campanha.codigo == campanha_codigo, Campanha.ativo.is_(True))
    ).scalar_one_or_none()
    if campanha is None:
        raise ValueError("Campanha não encontrada ou inativa.")

    consulta = (
        select(Personagem.id)
        .join(Usuario, Usuario.id == Personagem.usuario_id)
        .where(
            Personagem.campanha_id == campanha.id,
            Personagem.ativo.is_(True),
            Usuario.perfil.in_(("jogador", "tester")),
        )
        .order_by(Personagem.id)
    )
    if personagem_id is not None:
        identificador = _uuid(personagem_id)
        if identificador is None:
            raise ValueError("Treinador inválido.")
        consulta = consulta.where(Personagem.id == identificador)
    ids = list(db.session.execute(consulta).scalars())
    if personagem_id is not None and not ids:
        raise ValueError("Treinador não encontrado nesta campanha.")

    quantidade_pokemon = 0
    pv_restaurados = 0
    condicoes_removidas = 0
    modificados = 0
    autor = _uuid(usuario_id)

    for pid in ids:
        contexto = carregar_contexto_pokemon(pid, campanha_codigo=campanha_codigo)
        if contexto is None:
            raise ValueError("Não foi possível carregar a equipe de um dos treinadores.")
        pokemons = sorted(
            (p for p in contexto.personagem.pokemons if p.ativo),
            key=lambda p: str(p.id),
        )
        for pokemon in pokemons:
            # Lock protege atualizações de PV simultâneas à sessão.
            bloqueado = db.session.execute(
                select(Pokemon).where(Pokemon.id == pokemon.id, Pokemon.ativo.is_(True))
                .with_for_update()
            ).scalar_one_or_none()
            if bloqueado is None:
                continue
            quantidade_pokemon += 1
            anterior = int(bloqueado.pv_atual)
            status = list(bloqueado.status_ativos)
            quantidade_status = len(status)
            # O PV máximo pode ser alterado pelas condições configuradas.
            # Excluímos e descarregamos as condições ANTES de recalculá-lo.
            for relacao in status:
                db.session.delete(relacao)
            if status:
                db.session.flush()
                db.session.expire(bloqueado, ["status_ativos"])
            maximo = max(0, int(calcular_pokemon(
                bloqueado, contexto.personagem, contexto.regras
            ).get("totais", {}).get("pv", 0)))
            if anterior == maximo and not status:
                continue
            bloqueado.pv_atual = maximo
            pv_restaurados += max(0, maximo - anterior)
            condicoes_removidas += quantidade_status
            modificados += 1
            db.session.add(HistoricoAlteracao(
                usuario_id=autor,
                entidade="pokemon",
                registro_id=bloqueado.id,
                acao="curar_total_mestre",
                dados_anteriores={"pv_atual": anterior,
                                  "status_ids": [str(s.status_id) for s in status]},
                dados_novos={"pv_atual": maximo, "status_ids": [],
                             "escopo": "treinador" if personagem_id else "campanha"},
            ))

    db.session.commit()
    return {
        "treinadores": len(ids),
        "pokemons": quantidade_pokemon,
        "alterados": modificados,
        "pv_restaurados": pv_restaurados,
        "condicoes_removidas": condicoes_removidas,
    }
