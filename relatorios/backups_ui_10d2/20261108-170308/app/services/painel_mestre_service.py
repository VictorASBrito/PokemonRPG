from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Campanha,
    FormaPokemon,
    FormaPokemonAtributo,
    FormaPokemonTipo,
    HistoricoAlteracao,
    Natureza,
    NaturezaModificador,
    Personagem,
    PersonagemAtributo,
    Pokemon,
    PokemonBonusAtributo,
    PokemonStatus,
    Usuario,
)
from app.services.personagem_service import carregar_regras_personagem
from app.services.pokemon_db_service import (
    calcular_pokemon,
    carregar_contexto_pokemon,
    carregar_regras_pokemon_db,
)


@dataclass(slots=True)
class PainelMestre:
    campanha: dict[str, Any]
    resumo: dict[str, int]
    jogadores: list[dict[str, Any]]


def _uuid(valor: str | uuid.UUID) -> uuid.UUID | None:
    if isinstance(valor, uuid.UUID):
        return valor
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError):
        return None


def _imagem_pokemon(pokemon: Pokemon) -> str:
    forma = pokemon.forma_pokemon
    if pokemon.shiny and forma.imagem_shiny_url:
        return forma.imagem_shiny_url
    return forma.imagem_url or forma.imagem_shiny_url or ""


def _tipos_pokemon(pokemon: Pokemon) -> list[str]:
    return [
        relacao.tipo.nome
        for relacao in sorted(pokemon.forma_pokemon.tipos, key=lambda item: item.posicao)
        if relacao.tipo.ativo
    ]


def _status_pokemon(pokemon: Pokemon) -> list[str]:
    return sorted(
        {
            relacao.status.nome
            for relacao in pokemon.status_ativos
            if relacao.status and relacao.status.ativo
        },
        key=str.casefold,
    )


def _pv_maximo_personagem(personagem: Personagem, pv_por_saude: int) -> int:
    atributos = {
        item.atributo.codigo: int(item.valor)
        for item in personagem.atributos
        if item.atributo and item.atributo.ativo
    }
    return max(0, int(atributos.get("saude", 1)) * pv_por_saude)


def _percentual_pv(atual: int, maximo: int) -> int:
    if maximo <= 0:
        return 0
    return max(0, min(100, round((max(0, atual) / maximo) * 100)))


def carregar_painel_mestre(*, campanha_codigo: str) -> PainelMestre:
    campanha = db.session.execute(
        select(Campanha).where(
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if campanha is None:
        return PainelMestre(
            campanha={"nome": "Campanha", "descricao": None},
            resumo={
                "jogadores": 0,
                "pokemons": 0,
                "equipe": 0,
                "box": 0,
                "alertas": 0,
            },
            jogadores=[],
        )

    regras_pokemon = carregar_regras_pokemon_db(campanha.id)
    regras_personagem = carregar_regras_personagem(campanha.id)
    pv_por_saude = int(regras_personagem.get("pv_por_ponto_saude", 10))
    limite_equipe = int(regras_pokemon.get("limites", {}).get("tamanho_equipe", 6))

    personagens = list(
        db.session.execute(
            select(Personagem)
            .join(Usuario, Usuario.id == Personagem.usuario_id)
            .where(
                Personagem.campanha_id == campanha.id,
                Personagem.ativo.is_(True),
            )
            .options(
                selectinload(Personagem.usuario),
                selectinload(Personagem.atributos).selectinload(PersonagemAtributo.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.forma_pokemon)
                .selectinload(FormaPokemon.tipos)
                .selectinload(FormaPokemonTipo.tipo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.forma_pokemon)
                .selectinload(FormaPokemon.atributos_base)
                .selectinload(FormaPokemonAtributo.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.natureza)
                .selectinload(Natureza.modificadores)
                .selectinload(NaturezaModificador.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.bonus_atributos)
                .selectinload(PokemonBonusAtributo.atributo),
                selectinload(Personagem.pokemons)
                .selectinload(Pokemon.status_ativos)
                .selectinload(PokemonStatus.status),
                selectinload(Personagem.pokemons).selectinload(Pokemon.item_equipado),
            )
        ).scalars()
    )
    personagens.sort(
        key=lambda personagem: (
            personagem.ordem_painel is None,
            personagem.ordem_painel if personagem.ordem_painel is not None else 10**9,
            personagem.nome.casefold(),
        )
    )

    jogadores: list[dict[str, Any]] = []
    total_pokemons = 0
    total_equipe = 0
    total_box = 0
    total_alertas = 0

    for personagem in personagens:
        pv_maximo = _pv_maximo_personagem(personagem, pv_por_saude)
        alertas: list[str] = []
        if not personagem.usuario.ativo:
            alertas.append("Acesso desativado")
        if pv_maximo > 0 and personagem.pv_atual <= max(1, pv_maximo // 4):
            alertas.append("Treinador com PV baixo")

        pokemons_ativos = [pokemon for pokemon in personagem.pokemons if pokemon.ativo]
        equipe_modelos = sorted(
            (pokemon for pokemon in pokemons_ativos if pokemon.localizacao == "equipe"),
            key=lambda pokemon: pokemon.posicao or 9999,
        )
        box_total = sum(1 for pokemon in pokemons_ativos if pokemon.localizacao == "box")
        total_pokemons += len(pokemons_ativos)
        total_equipe += len(equipe_modelos)
        total_box += box_total

        equipe: list[dict[str, Any]] = []
        for pokemon in equipe_modelos:
            calculos = calcular_pokemon(pokemon, personagem, regras_pokemon)
            pv_pokemon_maximo = int(calculos.get("totais", {}).get("pv", 0))
            status = _status_pokemon(pokemon)
            if pv_pokemon_maximo > 0 and pokemon.pv_atual <= max(1, pv_pokemon_maximo // 4):
                alertas.append(f"{pokemon.apelido or pokemon.forma_pokemon.nome} com PV baixo")
            if status:
                alertas.append(
                    f"{pokemon.apelido or pokemon.forma_pokemon.nome}: {', '.join(status)}"
                )
            equipe.append(
                {
                    "id": str(pokemon.id),
                    "nome": pokemon.apelido or pokemon.forma_pokemon.nome,
                    "especie": pokemon.forma_pokemon.nome,
                    "imagem": _imagem_pokemon(pokemon),
                    "shiny": pokemon.shiny,
                    "tipos": _tipos_pokemon(pokemon),
                    "pv_atual": pokemon.pv_atual,
                    "pv_maximo": pv_pokemon_maximo,
                    "pv_percentual": _percentual_pv(pokemon.pv_atual, pv_pokemon_maximo),
                    "status": status,
                    "item": pokemon.item_equipado.nome if pokemon.item_equipado else "",
                    "posicao": pokemon.posicao,
                }
            )

        # Um mesmo Pokémon pode gerar mais de um aviso. Mantemos os textos únicos,
        # preservando a ordem em que foram encontrados.
        alertas = list(dict.fromkeys(alertas))
        total_alertas += len(alertas)

        atributos_personagem: list[dict[str, Any]] = []
        for relacao in sorted(
            (
                item
                for item in personagem.atributos
                if item.atributo
                and item.atributo.ativo
                and item.atributo.escopo in {"personagem", "ambos"}
            ),
            key=lambda item: (item.atributo.ordem, item.atributo.nome.casefold()),
        ):
            valor = relacao.valor
            numero = int(valor) if valor == valor.to_integral_value() else float(valor)
            atributos_personagem.append(
                {
                    "codigo": relacao.atributo.codigo,
                    "nome": relacao.atributo.nome,
                    "valor": numero,
                }
            )

        termos_busca = " ".join(
            [
                personagem.nome,
                personagem.usuario.nome,
                personagem.usuario.login,
                personagem.classe or "",
                personagem.origem or "",
                *(pokemon["nome"] for pokemon in equipe),
                *(pokemon["especie"] for pokemon in equipe),
            ]
        )
        jogadores.append(
            {
                "id": str(personagem.id),
                "usuario_id": str(personagem.usuario_id),
                "nome": personagem.nome,
                "jogador": personagem.usuario.nome,
                "login": personagem.usuario.login,
                "acesso_ativo": personagem.usuario.ativo,
                "foto_url": personagem.foto_url or "",
                "nivel": personagem.nivel,
                "classe": personagem.classe or "",
                "origem": personagem.origem or "",
                "pokedolares": personagem.pokedolares,
                "pv_atual": personagem.pv_atual,
                "pv_maximo": pv_maximo,
                "pv_percentual": _percentual_pv(personagem.pv_atual, pv_maximo),
                "atributos": atributos_personagem,
                "ordem_painel": personagem.ordem_painel,
                "equipe": equipe,
                "equipe_total": len(equipe),
                "limite_equipe": limite_equipe,
                "box_total": box_total,
                "alertas": alertas,
                "busca": termos_busca,
            }
        )

    return PainelMestre(
        campanha={"nome": campanha.nome, "descricao": campanha.descricao},
        resumo={
            "jogadores": len(jogadores),
            "pokemons": total_pokemons,
            "equipe": total_equipe,
            "box": total_box,
            "alertas": total_alertas,
        },
        jogadores=jogadores,
    )


def salvar_ordem_jogadores_painel(
    *,
    campanha_codigo: str,
    personagem_ids: list[str],
    usuario_id: str | None,
) -> list[str]:
    campanha = db.session.execute(
        select(Campanha).where(
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if campanha is None:
        raise ValueError("Campanha não encontrada.")

    identificadores: list[uuid.UUID] = []
    for valor in personagem_ids:
        identificador = _uuid(valor)
        if identificador is None or identificador in identificadores:
            raise ValueError("A ordem enviada contém jogadores inválidos ou repetidos.")
        identificadores.append(identificador)

    personagens = list(
        db.session.execute(
            select(Personagem)
            .where(
                Personagem.campanha_id == campanha.id,
                Personagem.ativo.is_(True),
            )
            .with_for_update()
        ).scalars()
    )
    existentes = {personagem.id: personagem for personagem in personagens}
    if len(existentes) != len(identificadores) or set(existentes) != set(identificadores):
        raise ValueError(
            "A ordem precisa conter todos os jogadores ativos da campanha exatamente uma vez."
        )

    ordem_anterior = [
        str(personagem.id)
        for personagem in sorted(
            personagens,
            key=lambda personagem: (
                personagem.ordem_painel is None,
                personagem.ordem_painel if personagem.ordem_painel is not None else 10**9,
                personagem.nome.casefold(),
            ),
        )
    ]
    for posicao, identificador in enumerate(identificadores, start=1):
        existentes[identificador].ordem_painel = posicao

    db.session.add(
        HistoricoAlteracao(
            usuario_id=_uuid(usuario_id) if usuario_id else None,
            entidade="campanha",
            registro_id=campanha.id,
            acao="reordenar_painel",
            dados_anteriores={"ordem_jogadores": ordem_anterior},
            dados_novos={"ordem_jogadores": [str(item) for item in identificadores]},
        )
    )
    db.session.commit()
    return [str(item) for item in identificadores]


def ajustar_pv_personagem(
    *,
    campanha_codigo: str,
    personagem_id: str,
    delta: int,
    usuario_id: str | None,
) -> dict[str, int] | None:
    identificador = _uuid(personagem_id)
    if identificador is None:
        return None

    personagem = db.session.execute(
        select(Personagem)
        .join(Campanha, Campanha.id == Personagem.campanha_id)
        .where(
            Personagem.id == identificador,
            Personagem.ativo.is_(True),
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
        .options(
            selectinload(Personagem.atributos).selectinload(PersonagemAtributo.atributo)
        )
        .with_for_update()
    ).scalar_one_or_none()
    if personagem is None:
        return None

    regras = carregar_regras_personagem(personagem.campanha_id)
    maximo = _pv_maximo_personagem(
        personagem, int(regras.get("pv_por_ponto_saude", 10))
    )
    anterior = personagem.pv_atual
    novo = max(-maximo, min(maximo, anterior + int(delta))) if maximo > 0 else 0
    personagem.pv_atual = novo
    db.session.add(
        HistoricoAlteracao(
            usuario_id=_uuid(usuario_id) if usuario_id else None,
            entidade="personagem",
            registro_id=personagem.id,
            acao="ajustar_pv_painel",
            dados_anteriores={"pv_atual": anterior},
            dados_novos={"pv_atual": novo, "delta": int(delta)},
        )
    )
    db.session.commit()
    return {
        "pv_atual": novo,
        "pv_maximo": maximo,
        "pv_percentual": _percentual_pv(novo, maximo),
    }


def ajustar_pv_pokemon(
    *,
    campanha_codigo: str,
    pokemon_id: str,
    delta: int,
    usuario_id: str | None,
) -> dict[str, int] | None:
    identificador = _uuid(pokemon_id)
    if identificador is None:
        return None

    pokemon_base = db.session.execute(
        select(Pokemon)
        .join(Personagem, Personagem.id == Pokemon.personagem_id)
        .join(Campanha, Campanha.id == Personagem.campanha_id)
        .where(
            Pokemon.id == identificador,
            Pokemon.ativo.is_(True),
            Personagem.ativo.is_(True),
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if pokemon_base is None:
        return None

    contexto = carregar_contexto_pokemon(
        pokemon_base.personagem_id,
        campanha_codigo=campanha_codigo,
    )
    if contexto is None:
        return None
    pokemon = next(
        (item for item in contexto.personagem.pokemons if item.id == identificador and item.ativo),
        None,
    )
    if pokemon is None:
        return None

    maximo = int(calcular_pokemon(pokemon, contexto.personagem, contexto.regras)["totais"].get("pv", 0))
    anterior = pokemon.pv_atual
    novo = max(0, min(maximo, anterior + int(delta))) if maximo > 0 else 0
    pokemon.pv_atual = novo
    db.session.add(
        HistoricoAlteracao(
            usuario_id=_uuid(usuario_id) if usuario_id else None,
            entidade="pokemon",
            registro_id=pokemon.id,
            acao="ajustar_pv_painel",
            dados_anteriores={"pv_atual": anterior},
            dados_novos={"pv_atual": novo, "delta": int(delta)},
        )
    )
    db.session.commit()
    return {
        "pv_atual": novo,
        "pv_maximo": maximo,
        "pv_percentual": _percentual_pv(novo, maximo),
    }
