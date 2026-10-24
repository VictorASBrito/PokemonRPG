from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import Campanha, FormaPokemon, FormaPokemonTipo, HistoricoAlteracao, Natureza, Personagem, Pokemon, PokemonCapturavel, Usuario
from app.services.pokemon_db_service import buscar_forma, calcular_pokemon, carregar_personagem_pokemon, carregar_regras_pokemon_db

LIMITE_CAPTURAVEIS = 15


@dataclass(slots=True)
class PainelCapturaveisMestre:
    campanha: dict[str, Any]
    capturaveis: list[dict[str, Any]]
    encontrados_por: list[dict[str, str]]
    total_ativos: int
    limite: int


def _campanha_ativa(campanha_codigo: str, *, bloquear: bool = False) -> Campanha | None:
    consulta = select(Campanha).where(
        Campanha.codigo == campanha_codigo,
        Campanha.ativo.is_(True),
    )
    if bloquear:
        # Serializa adições e remoções da mesma campanha no PostgreSQL.
        # Evita que duas solicitações escolham o mesmo slot simultaneamente.
        consulta = consulta.with_for_update()
    return db.session.execute(consulta).scalar_one_or_none()


def _natureza_aleatoria() -> Natureza | None:
    naturezas = list(
        db.session.execute(
            select(Natureza).where(Natureza.ativo.is_(True)).order_by(func.lower(Natureza.nome))
        ).scalars()
    )
    if not naturezas:
        return None
    return random.choice(naturezas)


def _genero_aleatorio(campanha_id: uuid.UUID) -> str:
    regras = carregar_regras_pokemon_db(campanha_id)
    generos = [str(item).strip() for item in regras.get("generos", []) if str(item).strip()]
    for opcoes in (["♂", "♀"], ["♂", "♀", "Ø"], generos):
        validos = [valor for valor in opcoes if valor in generos or opcoes is generos]
        if validos:
            return random.choice(validos)
    return "Ø"


def _tipos_forma(forma: FormaPokemon) -> list[dict[str, str]]:
    tipos: list[dict[str, str]] = []
    for relacao in sorted(forma.tipos, key=lambda item: item.posicao):
        if relacao.tipo and relacao.tipo.ativo:
            tipos.append({"nome": relacao.tipo.nome, "codigo": relacao.tipo.codigo})
    return tipos


def _imagem_forma(capturavel: PokemonCapturavel) -> str:
    forma = capturavel.forma_pokemon
    if capturavel.shiny and forma.imagem_shiny_url:
        return forma.imagem_shiny_url
    return forma.imagem_url or forma.imagem_shiny_url or ""


def _serializar(capturavel: PokemonCapturavel) -> dict[str, Any]:
    return {
        "id": str(capturavel.id),
        "ordem": capturavel.ordem,
        "nome": capturavel.forma_pokemon.nome,
        "imagem": _imagem_forma(capturavel),
        "tipos": _tipos_forma(capturavel.forma_pokemon),
        "encontrado_por": capturavel.encontrado_por.nome if capturavel.encontrado_por else "Não definido",
        "natureza": capturavel.natureza.nome if capturavel.natureza else "",
        "genero": capturavel.genero or "Ø",
        "shiny": capturavel.shiny,
    }


def _consulta_capturaveis(campanha_id: uuid.UUID):
    return (
        select(PokemonCapturavel)
        .where(
            PokemonCapturavel.campanha_id == campanha_id,
            PokemonCapturavel.ativo.is_(True),
        )
        .options(
            selectinload(PokemonCapturavel.forma_pokemon)
            .selectinload(FormaPokemon.tipos)
            .selectinload(FormaPokemonTipo.tipo),
            selectinload(PokemonCapturavel.encontrado_por),
            selectinload(PokemonCapturavel.natureza),
        )
        .order_by(PokemonCapturavel.ordem.asc(), PokemonCapturavel.criado_em.asc())
    )


def listar_capturaveis_campo(*, campanha_codigo: str) -> list[dict[str, Any]]:
    campanha = _campanha_ativa(campanha_codigo)
    if campanha is None:
        return []
    registros = list(db.session.execute(_consulta_capturaveis(campanha.id)).scalars())
    return [_serializar(item) for item in registros]


def carregar_painel_capturaveis_mestre(*, campanha_codigo: str) -> PainelCapturaveisMestre:
    campanha = _campanha_ativa(campanha_codigo)
    if campanha is None:
        return PainelCapturaveisMestre(
            campanha={"nome": "Campanha", "descricao": None},
            capturaveis=[],
            encontrados_por=[],
            total_ativos=0,
            limite=LIMITE_CAPTURAVEIS,
        )

    capturaveis = list(db.session.execute(_consulta_capturaveis(campanha.id)).scalars())
    personagens = list(
        db.session.execute(
            select(Personagem)
            .join(Usuario, Usuario.id == Personagem.usuario_id)
            .where(
                Personagem.campanha_id == campanha.id,
                Personagem.ativo.is_(True),
                Usuario.ativo.is_(True),
                Usuario.perfil.in_(("jogador", "tester")),
            )
            .order_by(func.lower(Personagem.nome))
        ).scalars()
    )
    return PainelCapturaveisMestre(
        campanha={"nome": campanha.nome, "descricao": campanha.descricao},
        capturaveis=[_serializar(item) for item in capturaveis],
        encontrados_por=[{"id": str(item.id), "nome": item.nome} for item in personagens],
        total_ativos=len(capturaveis),
        limite=LIMITE_CAPTURAVEIS,
    )


def criar_capturavel_campo(
    *,
    campanha_codigo: str,
    forma_id: str | None,
    forma_nome: str | None,
    encontrado_por_personagem_id: str | None,
    usuario_responsavel_id: str | None,
) -> PokemonCapturavel:
    campanha = _campanha_ativa(campanha_codigo, bloquear=True)
    if campanha is None:
        raise ValueError("Campanha não encontrada.")

    ativos = list(db.session.execute(_consulta_capturaveis(campanha.id)).scalars())
    if len(ativos) >= LIMITE_CAPTURAVEIS:
        raise ValueError(f"O campo já atingiu o limite de {LIMITE_CAPTURAVEIS} Pokémon capturáveis.")

    forma = None
    nome_informado = str(forma_nome or "").strip()
    identificador = str(forma_id or "").strip()
    if identificador:
        try:
            forma_uuid = uuid.UUID(identificador)
        except (TypeError, ValueError):
            # Compatibilidade com a primeira versão do seletor visual: ela
            # enviava o nome da espécie no input oculto "forma_id".
            # Aceitamos apenas se os dois campos concordam e a forma existe.
            if nome_informado and identificador.casefold() == nome_informado.casefold():
                forma = buscar_forma(nome_informado)
            else:
                raise ValueError("Selecione uma espécie válida no catálogo.")
        else:
            forma = db.session.get(FormaPokemon, forma_uuid)
    elif nome_informado:
        forma = buscar_forma(nome_informado)
    if forma is None or not forma.ativo:
        raise ValueError("Selecione uma espécie válida no catálogo.")

    encontrado_por = None
    if encontrado_por_personagem_id:
        try:
            encontrado_por_uuid = uuid.UUID(str(encontrado_por_personagem_id))
        except (TypeError, ValueError):
            raise ValueError("Selecione o jogador que encontrou o Pokémon.")
        encontrado_por = db.session.get(Personagem, encontrado_por_uuid)
    if encontrado_por is None or not encontrado_por.ativo or encontrado_por.campanha_id != campanha.id:
        raise ValueError("Selecione o jogador que encontrou o Pokémon.")

    ocupadas = {item.ordem for item in ativos if item.ordem is not None}
    ordem = next((numero for numero in range(1, LIMITE_CAPTURAVEIS + 1) if numero not in ocupadas), None)
    if ordem is None:
        raise ValueError(f"O campo já atingiu o limite de {LIMITE_CAPTURAVEIS} Pokémon capturáveis.")

    natureza = _natureza_aleatoria()
    capturavel = PokemonCapturavel(
        campanha_id=campanha.id,
        forma_pokemon_id=forma.id,
        encontrado_por_personagem_id=encontrado_por.id,
        natureza_id=natureza.id if natureza else None,
        genero=_genero_aleatorio(campanha.id),
        shiny=False,
        ordem=ordem,
        ativo=True,
    )
    db.session.add(capturavel)
    db.session.flush()
    db.session.add(
        HistoricoAlteracao(
            entidade="pokemon_capturavel",
            registro_id=capturavel.id,
            acao="criar",
            usuario_id=uuid.UUID(str(usuario_responsavel_id)) if usuario_responsavel_id else None,
            dados_anteriores=None,
            dados_novos={
                "campanha_codigo": campanha.codigo,
                "forma": forma.nome,
                "encontrado_por": encontrado_por.nome,
            },
        )
    )
    db.session.commit()
    return capturavel


def _retirar_do_campo_e_reordenar(
    *, campanha_id: uuid.UUID, capturavel: PokemonCapturavel,
) -> int | None:
    """Libera posições antes de reordenar, pois UNIQUE não é diferível.

    Não faz commit: a saída do campo e a atribuição à Box precisam ocorrer
    na MESMA transação, com rollback conjunto em qualquer falha.
    """
    ativos = list(db.session.execute(_consulta_capturaveis(campanha_id)).scalars())
    sobreviventes = [item for item in ativos if item.id != capturavel.id]
    ordem_antiga = capturavel.ordem
    capturavel.ativo = False
    capturavel.ordem = None
    for item in sobreviventes:
        item.ordem = None
    db.session.flush()
    for indice, item in enumerate(sobreviventes, start=1):
        item.ordem = indice
    db.session.flush()
    return ordem_antiga


def atribuir_capturavel_box(
    *,
    campanha_codigo: str,
    capturavel_id: str,
    personagem_id: str,
    usuario_responsavel_id: str | None,
) -> tuple[Pokemon, str]:
    """Transfere um encontro para a Box sem sortear novamente sua identidade.

    A operação inteira é atômica; uma segunda solicitação para o mesmo encontro
    é rejeitada depois que a primeira o retirou do campo. O lock da campanha
    serializa as operações com capturáveis no PostgreSQL.
    """
    campanha = _campanha_ativa(campanha_codigo, bloquear=True)
    if campanha is None:
        raise ValueError("Campanha não encontrada.")
    try:
        origem_uuid = uuid.UUID(str(capturavel_id))
        destino_uuid = uuid.UUID(str(personagem_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Selecione um capturável e um jogador válidos.") from None

    capturavel = db.session.execute(
        _consulta_capturaveis(campanha.id).where(PokemonCapturavel.id == origem_uuid)
    ).scalar_one_or_none()
    if capturavel is None:
        raise ValueError("Esse Pokémon já saiu do campo ou não está disponível.")

    # O personagem é o destinatário da captura; pode diferir de quem o encontrou.
    personagem = db.session.execute(
        select(Personagem)
        .join(Usuario, Usuario.id == Personagem.usuario_id)
        .where(
            Personagem.id == destino_uuid,
            Personagem.campanha_id == campanha.id,
            Personagem.ativo.is_(True),
            Usuario.ativo.is_(True),
            Usuario.perfil.in_(("jogador", "tester")),
        )
        .with_for_update()
    ).scalar_one_or_none()
    if personagem is None:
        raise ValueError("Selecione um jogador ativo desta campanha.")

    regras = carregar_regras_pokemon_db(campanha.id)
    limite = int(regras.get("boxes", {}).get("espacos", 100))
    ocupados = db.session.scalar(
        select(func.count(Pokemon.id)).where(
            Pokemon.personagem_id == personagem.id,
            Pokemon.ativo.is_(True),
            Pokemon.localizacao == "box",
        )
    ) or 0
    if ocupados >= limite:
        raise ValueError(f"A Box de {personagem.nome} está cheia ({ocupados}/{limite}).")
    ultima_posicao = db.session.scalar(
        select(func.max(Pokemon.posicao)).where(
            Pokemon.personagem_id == personagem.id,
            Pokemon.ativo.is_(True),
            Pokemon.localizacao == "box",
        )
    ) or 0

    # Copiar ANTES de alterar o encontro: não recomputar natureza, sexo ou shiny.
    origem = {
        "capturavel_id": str(capturavel.id),
        "campanha_codigo": campanha.codigo,
        "forma_pokemon_id": str(capturavel.forma_pokemon_id),
        "natureza_id": str(capturavel.natureza_id) if capturavel.natureza_id else None,
        "genero": capturavel.genero,
        "shiny": bool(capturavel.shiny),
        "encontrado_por_personagem_id": (
            str(capturavel.encontrado_por_personagem_id)
            if capturavel.encontrado_por_personagem_id else None
        ),
    }
    pokemon = Pokemon(
        personagem_id=personagem.id,
        forma_pokemon_id=capturavel.forma_pokemon_id,
        natureza_id=capturavel.natureza_id,
        genero=capturavel.genero,
        shiny=bool(capturavel.shiny),
        localizacao="box",
        posicao=int(ultima_posicao) + 1,
        pv_atual=0,
        ativo=True,
    )
    db.session.add(pokemon)
    db.session.flush()

    # Cálculo baseado na ficha de destino, que usa nível compartilhado.
    # A recarga ativa os relacionamentos de espécie, atributos e natureza.
    pokemon_id = pokemon.id
    db.session.expire_all()
    personagem_completo = carregar_personagem_pokemon(
        destino_uuid, campanha_codigo=campanha_codigo
    )
    assert personagem_completo is not None
    pokemon_completo = next(
        item for item in personagem_completo.pokemons if item.id == pokemon_id
    )
    pokemon_completo.pv_atual = int(
        calcular_pokemon(pokemon_completo, personagem_completo, regras)["totais"].get("pv", 0)
    )

    # Recarrega a mesma entidade já bloqueada pela transação; ao liberar
    # as posições não devem existir outros escritores para esta campanha.
    capturavel = db.session.get(PokemonCapturavel, origem_uuid)
    assert capturavel is not None
    ordem_antiga = _retirar_do_campo_e_reordenar(
        campanha_id=campanha.id, capturavel=capturavel
    )

    usuario_uuid = uuid.UUID(str(usuario_responsavel_id)) if usuario_responsavel_id else None
    destino = {
        "pokemon_id": str(pokemon_id),
        "personagem_id": str(destino_uuid),
        "localizacao": "box",
        "posicao": pokemon_completo.posicao,
        "pv_atual": pokemon_completo.pv_atual,
    }
    db.session.add_all([
        HistoricoAlteracao(
            entidade="pokemon", registro_id=pokemon_id, acao="criacao",
            usuario_id=usuario_uuid, dados_anteriores=None,
            dados_novos={**origem, **destino, "origem": "campo_capturaveis"},
        ),
        HistoricoAlteracao(
            entidade="pokemon_capturavel", registro_id=origem_uuid,
            acao="atribuir", usuario_id=usuario_uuid,
            dados_anteriores={**origem, "ordem": ordem_antiga},
            dados_novos=destino,
        ),
    ])
    db.session.commit()
    return pokemon_completo, personagem_completo.nome


def remover_capturavel_campo(*, campanha_codigo: str, capturavel_id: str, usuario_responsavel_id: str | None) -> bool:
    campanha = _campanha_ativa(campanha_codigo, bloquear=True)
    if campanha is None:
        return False
    try:
        capturavel_uuid = uuid.UUID(str(capturavel_id))
    except (TypeError, ValueError):
        return False

    capturavel = db.session.execute(
        _consulta_capturaveis(campanha.id).where(PokemonCapturavel.id == capturavel_uuid)
    ).scalar_one_or_none()
    if capturavel is None:
        return False

    ordem_antiga = _retirar_do_campo_e_reordenar(
        campanha_id=campanha.id, capturavel=capturavel
    )

    db.session.add(
        HistoricoAlteracao(
            entidade="pokemon_capturavel",
            registro_id=capturavel.id,
            acao="remover",
            usuario_id=uuid.UUID(str(usuario_responsavel_id)) if usuario_responsavel_id else None,
            dados_anteriores={
                "campanha_codigo": campanha.codigo,
                "ordem_anterior": ordem_antiga,
                "forma": capturavel.forma_pokemon.nome,
            },
            dados_novos=None,
        )
    )
    db.session.commit()
    return True
