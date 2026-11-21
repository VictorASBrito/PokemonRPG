"""Encaminhamento de integrantes de hordas ao sistema existente de Capturáveis.

Uma operação única no PostgreSQL, com lock de campanha: nunca duplica
o mesmo integrante e não re-sorteia natureza, gênero ou Shiny.
"""
from __future__ import annotations

from sqlalchemy import select
from app.extensions import db
from app.models.db import (
    GrupoNPCEmCampo, HistoricoAlteracao, Personagem, PokemonCapturavel,
    PokemonNPCEmCampo, Usuario,
)
from app.services.campo_npc_service import _campanha, _historico, _uuid
from app.services.capturaveis_service import LIMITE_CAPTURAVEIS, _consulta_capturaveis



def listar_hordas_pendentes(*, campanha_codigo: str) -> list[dict]:
    """Integra as hordas já criadas à tela de Capturáveis, sem tocar no Campo."""
    campanha = _campanha(campanha_codigo, bloquear=False)
    membros = db.session.scalars(
        select(PokemonNPCEmCampo).join(GrupoNPCEmCampo)
        .where(
            GrupoNPCEmCampo.campanha_id == campanha.id,
            GrupoNPCEmCampo.tipo == "horda",
            PokemonNPCEmCampo.enviado_captura.is_(False),
        )
        .order_by(GrupoNPCEmCampo.nome, PokemonNPCEmCampo.criado_em)
    ).all()
    return [
        {
            "id": str(p.id),
            "nome": p.forma_pokemon.nome,
            "imagem": (
                (p.forma_pokemon.imagem_shiny_url if p.shiny else p.forma_pokemon.imagem_url)
                or p.forma_pokemon.imagem_url or p.forma_pokemon.imagem_shiny_url or ""
            ),
            "grupo": p.grupo.nome,
            "shiny": bool(p.shiny),
            "encontrador_id": str(p.grupo.encontrado_por_personagem_id)
                if p.grupo.encontrado_por_personagem_id else "",
        }
        for p in membros
    ]

def encaminhar_horda(*, campanha_codigo, pokemon_id, encontrador_id, usuario_id):
    campanha = _campanha(campanha_codigo)
    uid = _uuid(pokemon_id)
    if uid is None:
        raise ValueError("Pokémon da horda inválido.")
    pokemon = db.session.execute(
        select(PokemonNPCEmCampo).join(GrupoNPCEmCampo)
        .where(PokemonNPCEmCampo.id == uid, GrupoNPCEmCampo.campanha_id == campanha.id)
    ).scalar_one_or_none()
    if pokemon is None or pokemon.grupo.tipo != "horda":
        raise ValueError("Este Pokémon não pertence a uma horda ativa da campanha.")
    if pokemon.enviado_captura:
        raise ValueError("Esse integrante já foi disponibilizado para captura.")
    uid_encontrador = _uuid(encontrador_id)
    if uid_encontrador is None:
        raise ValueError("Selecione o treinador que encontrou o Pokémon.")
    if (pokemon.grupo.encontrado_por_personagem_id is not None
            and pokemon.grupo.encontrado_por_personagem_id != uid_encontrador):
        raise ValueError(
            "Esta horda já teve o encontrador definido no sorteio de Shiny. "
            "Selecione o mesmo treinador para preservar o resultado."
        )
    encontrado_por = db.session.execute(
        select(Personagem).join(Usuario, Usuario.id == Personagem.usuario_id)
        .where(Personagem.id == uid_encontrador, Personagem.campanha_id == campanha.id,
               Personagem.ativo.is_(True), Usuario.ativo.is_(True),
               Usuario.perfil.in_(("jogador", "tester")))
    ).scalar_one_or_none()
    if encontrado_por is None:
        raise ValueError("O treinador selecionado não pertence à campanha ativa.")
    ativos = list(db.session.execute(_consulta_capturaveis(campanha.id)).scalars())
    if len(ativos) >= LIMITE_CAPTURAVEIS:
        raise ValueError("A lista de Capturáveis já atingiu 15 Pokémon.")
    ocupadas = {item.ordem for item in ativos if item.ordem is not None}
    ordem = next((i for i in range(1, LIMITE_CAPTURAVEIS + 1) if i not in ocupadas), None)
    if ordem is None:
        raise ValueError("Não existe uma vaga disponível entre os 15 Capturáveis.")
    registro = PokemonCapturavel(
        campanha_id=campanha.id,
        forma_pokemon_id=pokemon.forma_pokemon_id,
        encontrado_por_personagem_id=encontrado_por.id,
        natureza_id=pokemon.natureza_id,
        genero=pokemon.genero,
        shiny=bool(pokemon.shiny),
        ordem=ordem, ativo=True,
        observacoes=f"Origem: horda {pokemon.grupo.nome} · Campo de Ankar",
    )
    db.session.add(registro)
    db.session.flush()
    pokemon.enviado_captura = True
    pokemon.capturavel_id = registro.id
    db.session.add(HistoricoAlteracao(
        entidade="pokemon_capturavel", registro_id=registro.id, acao="criar_horda",
        usuario_id=_uuid(usuario_id), dados_anteriores=None,
        dados_novos={
            "origem_horda": str(pokemon.grupo.id), "origem_pokemon": str(pokemon.id),
            "encontrado_por": str(encontrado_por.id), "shiny": bool(pokemon.shiny),
            "natureza_id": str(pokemon.natureza_id) if pokemon.natureza_id else None,
            "genero": pokemon.genero,
        },
    ))
    _historico(usuario_id, pokemon.id, "enviar_captura",
               depois={"capturavel_id": str(registro.id), "ordem": ordem})
    db.session.commit()
    return f"Pokémon de {pokemon.grupo.nome} disponibilizado na vaga {ordem} dos Capturáveis."
