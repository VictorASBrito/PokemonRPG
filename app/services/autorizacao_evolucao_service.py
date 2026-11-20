"""10E.3.2 — Concessão/revogação de evoluções narrativas por INSTÂNCIA.

Todas as decisões sensíveis são revalidadas no PostgreSQL. O serviço
nunca muda a forma do Pokémon e não consome itens.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    AutorizacaoEvolucaoPokemon, CampanhaMembro, EvolucaoPokemon,
    FormaPokemon, HistoricoAlteracao, Personagem, Pokemon, Usuario,
)
from app.services.consulta_evolucao_service import _tem_condicoes_especiais

LIMITE_MOTIVO = 500


def _uuid(valor: uuid.UUID | str) -> uuid.UUID:
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Identificador inválido.") from exc


def _validar_motivo(texto: str) -> str:
    motivo = str(texto or "").strip()
    if not 5 <= len(motivo) <= LIMITE_MOTIVO:
        raise ValueError("Informe um motivo entre 5 e 500 caracteres.")
    return motivo


def _validar_contexto(
    *, pokemon_id: uuid.UUID | str, usuario_id: uuid.UUID | str,
    campanha_id: uuid.UUID | str,
) -> tuple[Pokemon, Usuario]:
    """Serializa decisões concorrentes no Pokémon e confere campanha/ator."""
    pid, uid, cid = _uuid(pokemon_id), _uuid(usuario_id), _uuid(campanha_id)
    usuario = db.session.get(Usuario, uid)
    if not usuario or not usuario.ativo or usuario.perfil not in ("mestre", "administrador"):
        raise PermissionError("Somente o mestre ou administrador ativo pode liberar evoluções.")
    # Administradores globais podem atuar sem vínculo; mestres precisam
    # pertencer à campanha com papel de mestre.
    if usuario.perfil == "mestre":
        membro = db.session.scalar(select(CampanhaMembro.id).where(
            CampanhaMembro.usuario_id == uid,
            CampanhaMembro.campanha_id == cid,
            CampanhaMembro.papel == "mestre",
        ))
        if membro is None:
            raise PermissionError("O mestre não pertence à campanha deste Pokémon.")

    pokemon = db.session.scalar(
        select(Pokemon).where(Pokemon.id == pid).with_for_update()
    )
    if not pokemon or not pokemon.ativo:
        raise ValueError("Pokémon inexistente ou inativo.")
    personagem = db.session.get(Personagem, pokemon.personagem_id)
    if not personagem or not personagem.ativo or personagem.campanha_id != cid:
        raise ValueError("O Pokémon não pertence à campanha informada.")
    return pokemon, usuario


def _auditar(
    autorizacao: AutorizacaoEvolucaoPokemon, *,
    usuario_id: uuid.UUID | None, acao: str, antes: dict | None,
) -> None:
    depois = {
        "pokemon_id": str(autorizacao.pokemon_id),
        "relacao_id": str(autorizacao.relacao_id),
        "forma_origem_id": str(autorizacao.forma_origem_id),
        "ativo": autorizacao.ativo,
        "autorizado_por_id": str(autorizacao.autorizado_por_id),
        "justificativa": autorizacao.justificativa,
        "motivo_revogacao": autorizacao.motivo_revogacao,
    }
    db.session.add(HistoricoAlteracao(
        usuario_id=usuario_id,
        entidade="autorizacao_evolucao_pokemon",
        registro_id=autorizacao.id,
        acao=acao,
        dados_anteriores=antes,
        dados_novos=depois,
    ))


def _anterior(a: AutorizacaoEvolucaoPokemon) -> dict:
    return {
        "ativo": a.ativo,
        "forma_origem_id": str(a.forma_origem_id),
        "autorizado_por_id": str(a.autorizado_por_id),
        "motivo_revogacao": a.motivo_revogacao,
    }


def autorizacoes_ativas_pokemon(
    pokemon: Pokemon,
) -> dict[uuid.UUID, AutorizacaoEvolucaoPokemon]:
    """Filtra autorizações por Pokémon e forma atual, não por espécie."""
    return {
        a.relacao_id: a
        for a in db.session.scalars(select(AutorizacaoEvolucaoPokemon).where(
            AutorizacaoEvolucaoPokemon.pokemon_id == pokemon.id,
            AutorizacaoEvolucaoPokemon.forma_origem_id == pokemon.forma_pokemon_id,
            AutorizacaoEvolucaoPokemon.ativo.is_(True),
            AutorizacaoEvolucaoPokemon.revogado_em.is_(None),
        )).all()
    }


def autorizar_evolucao_individual(
    *, pokemon_id: uuid.UUID | str, relacao_id: uuid.UUID | str,
    usuario_id: uuid.UUID | str, campanha_id: uuid.UUID | str, motivo: str,
) -> tuple[AutorizacaoEvolucaoPokemon, bool]:
    """Concede uma única relação para um único Pokémon; flush, sem commit."""
    justificativa = _validar_motivo(motivo)
    pokemon, usuario = _validar_contexto(
        pokemon_id=pokemon_id, usuario_id=usuario_id, campanha_id=campanha_id,
    )
    relacao = db.session.get(EvolucaoPokemon, _uuid(relacao_id))
    if not relacao or not relacao.ativo:
        raise ValueError("Relação evolutiva inexistente ou inativa.")
    req = relacao.requisitos if isinstance(relacao.requisitos, dict) else {}
    if (
        req.get("tipo_relacao", "evolucao") != "evolucao"
        or pokemon.forma_pokemon_id != relacao.forma_origem_id
    ):
        raise ValueError("Esta relação não corresponde à forma atual do Pokémon.")
    destino = db.session.get(FormaPokemon, relacao.forma_destino_id)
    if not destino or not destino.ativo or not destino.especie or not destino.especie.ativo:
        raise ValueError("Destino evolutivo inativo ou inexistente.")
    if not _tem_condicoes_especiais(relacao, req):
        raise ValueError("Evolução simples por nível/pedra não exige liberação narrativa.")
    autorizacao = db.session.scalar(
        select(AutorizacaoEvolucaoPokemon)
        .where(
            AutorizacaoEvolucaoPokemon.pokemon_id == pokemon.id,
            AutorizacaoEvolucaoPokemon.relacao_id == relacao.id,
        )
        .with_for_update()
    )
    if (
        autorizacao and autorizacao.ativo
        and autorizacao.revogado_em is None
        and autorizacao.forma_origem_id == pokemon.forma_pokemon_id
    ):
        return autorizacao, False

    antes = _anterior(autorizacao) if autorizacao else None
    if autorizacao is None:
        autorizacao = AutorizacaoEvolucaoPokemon(
            pokemon_id=pokemon.id,
            relacao_id=relacao.id,
            forma_origem_id=pokemon.forma_pokemon_id,
            autorizado_por_id=usuario.id,
            justificativa=justificativa,
            ativo=True,
        )
        db.session.add(autorizacao)
    else:
        autorizacao.forma_origem_id = pokemon.forma_pokemon_id
        autorizacao.autorizado_por_id = usuario.id
        autorizacao.justificativa = justificativa
        autorizacao.autorizado_em = datetime.now(timezone.utc)
        autorizacao.ativo = True
        autorizacao.revogado_em = None
        autorizacao.revogado_por_id = None
        autorizacao.motivo_revogacao = None
    db.session.flush()
    _auditar(autorizacao, usuario_id=usuario.id, acao="autorizar_evolucao", antes=antes)
    return autorizacao, True


def _marcar_revogada(
    autorizacao: AutorizacaoEvolucaoPokemon, *, usuario_id: uuid.UUID | None,
    motivo: str,
) -> None:
    antes = _anterior(autorizacao)
    autorizacao.ativo = False
    autorizacao.revogado_em = datetime.now(timezone.utc)
    autorizacao.revogado_por_id = usuario_id
    autorizacao.motivo_revogacao = motivo
    _auditar(autorizacao, usuario_id=usuario_id, acao="revogar_evolucao", antes=antes)


def revogar_evolucao_individual(
    *, pokemon_id: uuid.UUID | str, relacao_id: uuid.UUID | str,
    usuario_id: uuid.UUID | str, campanha_id: uuid.UUID | str, motivo: str,
) -> bool:
    """Revoga concessão específica. Não altera outros ramos nem espécies."""
    justificativa = _validar_motivo(motivo)
    pokemon, usuario = _validar_contexto(
        pokemon_id=pokemon_id, usuario_id=usuario_id, campanha_id=campanha_id,
    )
    autorizacao = db.session.scalar(
        select(AutorizacaoEvolucaoPokemon).where(
            AutorizacaoEvolucaoPokemon.pokemon_id == pokemon.id,
            AutorizacaoEvolucaoPokemon.relacao_id == _uuid(relacao_id),
        ).with_for_update()
    )
    if autorizacao is None or not autorizacao.ativo:
        return False
    _marcar_revogada(autorizacao, usuario_id=usuario.id, motivo=justificativa)
    db.session.flush()
    return True


def invalidar_autorizacoes_por_troca_forma(
    pokemon: Pokemon, *, usuario_id: uuid.UUID | str | None,
) -> int:
    """Desativa concessões quando a espécie/forma é editada manualmente.

    Chamado dentro da MESMA transação da edição de identidade, antes do
    commit; impede reuso se um Pokémon voltar depois à forma anterior.
    """
    uid = _uuid(usuario_id) if usuario_id is not None else None
    registros = list(db.session.scalars(
        select(AutorizacaoEvolucaoPokemon)
        .where(
            AutorizacaoEvolucaoPokemon.pokemon_id == pokemon.id,
            AutorizacaoEvolucaoPokemon.ativo.is_(True),
        ).with_for_update()
    ))
    for a in registros:
        _marcar_revogada(
            a, usuario_id=uid,
            motivo="Mudança manual da forma do Pokémon; autorização anterior invalidada.",
        )
    if registros:
        db.session.flush()
    return len(registros)
