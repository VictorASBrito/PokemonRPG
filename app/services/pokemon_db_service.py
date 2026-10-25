from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Atributo,
    Campanha,
    CategoriaGolpe,
    CategoriaItem,
    ConjuntoRegras,
    EspeciePokemon,
    FormaPokemon,
    FormaPokemonAtributo,
    FormaPokemonTipo,
    Golpe,
    HistoricoAlteracao,
    Item,
    Natureza,
    NaturezaModificador,
    Personagem,
    Pokemon,
    PokemonBonusAtributo,
    PokemonGolpe,
    PokemonStatus,
    Regra,
    RegraValor,
    StatusCondicao,
)
from app.services.calculo_atributos import (
    aplicar_aumento,
    aplicar_diminuicao,
    calcular_progressao,
)
from app.services.importacao.utils import slug, uuid_legado

ATRIBUTOS_PADRAO = (
    "pv",
    "ataque",
    "defesa",
    "ataque_especial",
    "defesa_especial",
    "velocidade",
)
BOX_ID = "box-unica"


@dataclass(slots=True)
class ContextoPokemon:
    personagem: Personagem
    regras: dict[str, Any]
    jogador: dict[str, Any]


def _inteiro(valor: Any, padrao: int = 0) -> int:
    try:
        if valor is None or isinstance(valor, bool):
            return padrao if valor is None else int(valor)
        return int(Decimal(str(valor).strip().replace(",", ".")))
    except (ArithmeticError, TypeError, ValueError):
        return padrao


def _codigo_atributo(codigo: Any) -> str:
    """Normaliza códigos vindos do banco e das regras para uma chave única.

    O catálogo inicial foi importado usando ``slug``, que transforma
    ``ataque_especial`` em ``ataque-especial``. Já as regras antigas usam
    sublinhado. Internamente os cálculos trabalham com sublinhado e, na saída,
    disponibilizamos os dois formatos para manter compatibilidade com as telas.
    """
    return str(codigo or "").strip().replace("-", "_")


def _mapa_atributos_normalizado(mapa: Any) -> dict[str, Any]:
    if not isinstance(mapa, dict):
        return {}
    return {_codigo_atributo(codigo): valor for codigo, valor in mapa.items()}


def _com_aliases_atributos(valores: dict[str, int]) -> dict[str, int]:
    """Expõe ``ataque_especial`` e ``ataque-especial`` com o mesmo valor."""
    resultado = dict(valores)
    for codigo, valor in list(valores.items()):
        resultado[codigo.replace("_", "-")] = valor
    return resultado


def _decimal_numero(valor: Decimal | int | float | None) -> int | float:
    if valor is None:
        return 0
    numero = Decimal(valor)
    return int(numero) if numero == numero.to_integral_value() else float(numero)


def _resolver_uuid(referencia: str | uuid.UUID, namespace: str) -> uuid.UUID:
    if isinstance(referencia, uuid.UUID):
        return referencia
    try:
        return uuid.UUID(str(referencia))
    except (TypeError, ValueError):
        return uuid_legado(namespace, str(referencia))


def _opcoes_carregamento():
    return (
        selectinload(Personagem.usuario),
        selectinload(Personagem.campanha),
        selectinload(Personagem.atributos),
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
        .selectinload(Pokemon.golpes)
        .selectinload(PokemonGolpe.golpe)
        .selectinload(Golpe.tipo),
        selectinload(Personagem.pokemons)
        .selectinload(Pokemon.golpes)
        .selectinload(PokemonGolpe.golpe)
        .selectinload(Golpe.categoria),
        selectinload(Personagem.pokemons)
        .selectinload(Pokemon.status_ativos)
        .selectinload(PokemonStatus.status),
        selectinload(Personagem.pokemons)
        .selectinload(Pokemon.bonus_atributos)
        .selectinload(PokemonBonusAtributo.atributo),
        selectinload(Personagem.pokemons).selectinload(Pokemon.item_equipado),
    )


def carregar_personagem_pokemon(
    referencia: str | uuid.UUID,
    *,
    campanha_codigo: str | None = None,
) -> Personagem | None:
    personagem_id = _resolver_uuid(referencia, "personagem")
    consulta = (
        select(Personagem)
        .where(Personagem.id == personagem_id, Personagem.ativo.is_(True))
        .options(*_opcoes_carregamento())
    )
    if campanha_codigo:
        consulta = consulta.join(Campanha, Campanha.id == Personagem.campanha_id).where(
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    return db.session.execute(consulta).scalar_one_or_none()


def _valores_regras(campanha_id: uuid.UUID) -> tuple[ConjuntoRegras | None, dict[str, Any]]:
    conjunto = db.session.execute(
        select(ConjuntoRegras)
        .where(
            ConjuntoRegras.campanha_id == campanha_id,
            ConjuntoRegras.em_uso.is_(True),
            ConjuntoRegras.ativo.is_(True),
        )
        .options(selectinload(ConjuntoRegras.valores).selectinload(RegraValor.regra))
    ).scalar_one_or_none()
    if conjunto is None:
        return None, {}
    return conjunto, {
        registro.regra.codigo: registro.valor
        for registro in conjunto.valores
        if registro.regra.ativo
    }


def carregar_regras_pokemon_db(campanha_id: uuid.UUID) -> dict[str, Any]:
    _, valores = _valores_regras(campanha_id)
    atributos = list(
        db.session.execute(
            select(Atributo)
            .where(
                Atributo.ativo.is_(True),
                Atributo.escopo.in_(["pokemon", "ambos"]),
            )
            .order_by(Atributo.ordem, func.lower(Atributo.nome))
        ).scalars()
    )
    naturezas = list(
        db.session.execute(
            select(Natureza)
            .where(Natureza.ativo.is_(True))
            .options(
                selectinload(Natureza.modificadores).selectinload(
                    NaturezaModificador.atributo
                )
            )
            .order_by(func.lower(Natureza.nome))
        ).scalars()
    )
    status = list(
        db.session.execute(
            select(StatusCondicao)
            .where(StatusCondicao.ativo.is_(True))
            .order_by(func.lower(StatusCondicao.nome))
        ).scalars()
    )

    return {
        "limites": {
            "tamanho_equipe": _inteiro(valores.get("tamanho-equipe"), 6),
            "golpes_por_pokemon": _inteiro(valores.get("golpes-por-pokemon"), 4),
        },
        "boxes": {
            "espacos": _inteiro(valores.get("tamanho-box"), 100),
            "nome": str(valores.get("nome-box") or "Box Pokémon"),
            "id": BOX_ID,
        },
        "bonus_shiny": valores.get("bonus-shiny") or {},
        "progressao_pv": valores.get("progressao-pv") or [],
        "progressao_atributos": valores.get("progressao-atributos") or [],
        "estilos_combate": valores.get("estilos-combate") or {},
        "generos": valores.get("generos-pokemon") or ["Ø", "♂", "♀"],
        "atributos": [
            {"id": item.codigo, "nome": item.nome, "descricao": item.descricao}
            for item in atributos
        ],
        "naturezas": [
            {
                "id": str(item.id),
                "codigo": item.codigo,
                "nome": item.nome,
                "descricao": item.descricao,
            }
            for item in naturezas
        ],
        "status": [
            {"id": "", "codigo": "nenhum", "nome": "Nenhum", "descricao": "Sem condição ativa."}
        ]
        + [
            {
                "id": str(item.id),
                "codigo": item.codigo,
                "nome": item.nome,
                "descricao": item.descricao,
            }
            for item in status
        ],
    }


def _forma_para_dict(forma: FormaPokemon) -> dict[str, Any]:
    atributos = {
        item.atributo.codigo: _decimal_numero(item.valor_base)
        for item in forma.atributos_base
        if item.atributo.ativo
    }
    tipos = [
        item.tipo.nome
        for item in sorted(forma.tipos, key=lambda rel: rel.posicao)
        if item.tipo.ativo
    ]
    return {
        "id": str(forma.id),
        "codigo": forma.codigo,
        "nome": forma.nome,
        "categoria": forma.categoria,
        "imagem": forma.imagem_url or "",
        "imagem_shiny": forma.imagem_shiny_url or forma.imagem_url or "",
        "tipos": tipos,
        "atributos_base": atributos,
    }


def _golpe_para_dict(golpe: Golpe) -> dict[str, Any]:
    precisao = None if golpe.precisao is None else _decimal_numero(golpe.precisao)
    if precisao is None:
        precisao_texto = "—"
    elif float(precisao).is_integer():
        precisao_texto = f"{int(precisao)}%"
    else:
        precisao_texto = f"{precisao}%"
    return {
        "id": str(golpe.id),
        "codigo": golpe.codigo,
        "nome": golpe.nome,
        "tipo": golpe.tipo.nome if golpe.tipo and golpe.tipo.ativo else "—",
        "categoria": golpe.categoria.nome if golpe.categoria else "—",
        "dano": golpe.expressao_dano or "",
        "precisao": precisao,
        "precisao_texto": precisao_texto,
        "prioridade": golpe.prioridade,
        "efeito": golpe.descricao or "",
        "efeitos": golpe.efeitos,
    }


def _status_principal(pokemon: Pokemon) -> StatusCondicao | None:
    ativos = [item.status for item in pokemon.status_ativos if item.status.ativo]
    return sorted(ativos, key=lambda item: item.nome.casefold())[0] if ativos else None


def _pokemon_para_dict(pokemon: Pokemon) -> dict[str, Any]:
    bonus = {
        item.atributo.codigo: _decimal_numero(item.valor)
        for item in pokemon.bonus_atributos
        if item.atributo.ativo
    }
    status = _status_principal(pokemon)
    golpes = [
        {"golpe_id": str(item.golpe_id)}
        for item in sorted(pokemon.golpes, key=lambda rel: rel.posicao)
        if item.golpe.ativo
    ]
    return {
        "id": str(pokemon.id),
        "especie_id": str(pokemon.forma_pokemon_id),
        "apelido": pokemon.apelido or "",
        "genero": pokemon.genero or "Ø",
        "shiny": pokemon.shiny,
        "natureza": pokemon.natureza.nome if pokemon.natureza else "",
        "natureza_id": str(pokemon.natureza_id) if pokemon.natureza_id else "",
        "status": status.nome if status else "Nenhum",
        "status_id": str(status.id) if status else "",
        "item_carregado": pokemon.item_equipado.nome if pokemon.item_equipado else "",
        "item_equipado_id": str(pokemon.item_equipado_id) if pokemon.item_equipado_id else "",
        "pv_atual": pokemon.pv_atual,
        "bonus": bonus,
        "golpes": golpes,
        "anotacoes": pokemon.anotacoes or "",
        "localizacao": pokemon.localizacao,
        "posicao": pokemon.posicao,
    }


def _efeitos_status(status: StatusCondicao | None) -> list[dict[str, Any]]:
    if status is None or status.efeitos is None:
        return []
    if isinstance(status.efeitos, list):
        return [item for item in status.efeitos if isinstance(item, dict)]
    if isinstance(status.efeitos, dict):
        if isinstance(status.efeitos.get("efeitos"), list):
            return [
                item for item in status.efeitos["efeitos"] if isinstance(item, dict)
            ]
        return [status.efeitos]
    return []


def _aplicar_status_configurado(
    valores: dict[str, int], status: StatusCondicao | None
) -> bool:
    aplicado = False
    for efeito in _efeitos_status(status):
        tipo = str(efeito.get("tipo", "")).strip().lower()
        if tipo not in {"alterar_atributo", "modificador_atributo"}:
            continue
        atributo = _codigo_atributo(efeito.get("atributo", ""))
        if atributo not in valores:
            continue
        aplicado = True
        if efeito.get("multiplicador") is not None:
            valores[atributo] = max(
                0, math.floor(valores[atributo] * float(efeito["multiplicador"]))
            )
            continue
        percentual = efeito.get("percentual", efeito.get("valor_percentual"))
        if percentual is not None:
            percentual = float(percentual)
            valores[atributo] = (
                aplicar_aumento(valores[atributo], percentual)
                if percentual >= 0
                else aplicar_diminuicao(valores[atributo], abs(percentual))
            )
            continue
        if efeito.get("valor") is not None:
            valores[atributo] = max(0, valores[atributo] + _inteiro(efeito["valor"]))
    return aplicado


def calcular_pokemon(
    pokemon: Pokemon,
    personagem: Personagem,
    regras: dict[str, Any],
) -> dict[str, Any]:
    nivel = max(1, personagem.nivel)
    forma = pokemon.forma_pokemon
    base_original = {
        _codigo_atributo(item.atributo.codigo): _inteiro(item.valor_base)
        for item in forma.atributos_base
        if item.atributo.ativo
    }
    bonus_shiny = _mapa_atributos_normalizado(
        regras.get("bonus_shiny", {}) if pokemon.shiny else {}
    )
    bases = {
        codigo: _inteiro(base_original.get(codigo))
        + _inteiro(bonus_shiny.get(codigo))
        for codigo in {**{item: 0 for item in ATRIBUTOS_PADRAO}, **base_original}
    }

    valores: dict[str, int] = {}
    for codigo, base in bases.items():
        faixas = (
            regras.get("progressao_pv", [])
            if codigo == "pv"
            else regras.get("progressao_atributos", [])
        )
        valores[codigo] = calcular_progressao(base, nivel, faixas)

    if pokemon.natureza:
        for modificador in pokemon.natureza.modificadores:
            codigo = _codigo_atributo(modificador.atributo.codigo)
            if codigo not in valores:
                continue
            valor = float(modificador.valor)
            if modificador.tipo_modificador == "percentual":
                valores[codigo] = (
                    aplicar_aumento(valores[codigo], valor)
                    if valor >= 0
                    else aplicar_diminuicao(valores[codigo], abs(valor))
                )
            else:
                valores[codigo] = max(0, valores[codigo] + int(valor))

    estilo = personagem.estilo_combate or ""
    modificadores_estilo = _mapa_atributos_normalizado(
        (regras.get("estilos_combate", {}).get(estilo, {}) or {})
    )
    for codigo, percentual in modificadores_estilo.items():
        if codigo in valores:
            valores[codigo] = aplicar_aumento(valores[codigo], float(percentual))

    status = _status_principal(pokemon)
    configurado = _aplicar_status_configurado(valores, status)
    if status and not configurado:
        codigo = status.codigo
        if codigo == "dormindo":
            valores["velocidade"] = 0
        elif codigo == "paralisado":
            valores["velocidade"] = aplicar_diminuicao(valores.get("velocidade", 0), 0.50)
        elif codigo == "queimando":
            valores["ataque"] = aplicar_diminuicao(valores.get("ataque", 0), 0.50)

    bonus = {
        _codigo_atributo(item.atributo.codigo): _inteiro(item.valor)
        for item in pokemon.bonus_atributos
        if item.atributo.ativo
    }
    for codigo in valores:
        valores[codigo] = max(0, valores[codigo] + _inteiro(bonus.get(codigo)))

    velocidade = valores.get("velocidade", 0)
    dados_defesa = 0 if velocidade <= 0 else math.ceil(velocidade / 10)
    golpes = [
        _golpe_para_dict(item.golpe)
        for item in sorted(pokemon.golpes, key=lambda rel: rel.posicao)
        if item.golpe.ativo
    ]
    return {
        "nivel": nivel,
        "bases": _com_aliases_atributos(bases),
        "totais": _com_aliases_atributos(valores),
        "dados_defesa": dados_defesa,
        "dados_defesa_texto": f"{dados_defesa}d6",
        "golpes": golpes,
        "natureza": {
            "nome": pokemon.natureza.nome if pokemon.natureza else "",
        },
        "status": status.nome if status else "Nenhum",
    }


def _jogador_basico(personagem: Personagem) -> dict[str, Any]:
    return {
        "id": str(personagem.id),
        "usuario_id": str(personagem.usuario_id),
        "campanha_id": str(personagem.campanha_id),
        "treinador": {
            "nome": personagem.nome,
            "foto_url": personagem.foto_url or "",
            "nivel": personagem.nivel,
            "idade": personagem.idade,
            "genero": personagem.genero or "",
            "origem": personagem.origem or "",
            "classe": personagem.classe or "",
            "estilo_combate": personagem.estilo_combate or "",
            "numeros_shiny": personagem.numeros_shiny or [],
            "pokedolares": personagem.pokedolares,
            "pv_atual": personagem.pv_atual,
            "atributos": {},
        },
    }


def registro_detalhado(
    pokemon: Pokemon,
    personagem: Personagem,
    regras: dict[str, Any],
) -> dict[str, Any]:
    return {
        "pokemon": _pokemon_para_dict(pokemon),
        "especie": _forma_para_dict(pokemon.forma_pokemon),
        "calculos": calcular_pokemon(pokemon, personagem, regras),
    }


def carregar_contexto_pokemon(
    referencia: str | uuid.UUID,
    *,
    campanha_codigo: str | None = None,
) -> ContextoPokemon | None:
    personagem = carregar_personagem_pokemon(
        referencia, campanha_codigo=campanha_codigo
    )
    if personagem is None:
        return None
    regras = carregar_regras_pokemon_db(personagem.campanha_id)
    return ContextoPokemon(
        personagem=personagem,
        regras=regras,
        jogador=_jogador_basico(personagem),
    )


def equipe_detalhada_db(contexto: ContextoPokemon) -> list[dict[str, Any]]:
    pokemons = sorted(
        (
            item
            for item in contexto.personagem.pokemons
            if item.ativo and item.localizacao == "equipe"
        ),
        key=lambda item: item.posicao or 9999,
    )
    return [
        registro_detalhado(item, contexto.personagem, contexto.regras)
        for item in pokemons
    ]


def box_detalhada_db(contexto: ContextoPokemon) -> dict[str, Any]:
    pokemons = sorted(
        (
            item
            for item in contexto.personagem.pokemons
            if item.ativo and item.localizacao == "box"
        ),
        key=lambda item: item.posicao or 9999,
    )
    registros = []
    for indice, item in enumerate(pokemons):
        registro = registro_detalhado(item, contexto.personagem, contexto.regras)
        registro["ordem_box"] = indice
        registros.append(registro)
    return {
        "id": BOX_ID,
        "nome": contexto.regras["boxes"]["nome"],
        "limite": contexto.regras["boxes"]["espacos"],
        "registros": registros,
    }


def listar_formas_ativas() -> list[FormaPokemon]:
    return list(
        db.session.execute(
            select(FormaPokemon)
            .where(FormaPokemon.ativo.is_(True))
            .order_by(func.lower(FormaPokemon.nome))
        ).scalars()
    )


def listar_golpes_ativos() -> list[Golpe]:
    return list(
        db.session.execute(
            select(Golpe)
            .where(Golpe.ativo.is_(True))
            .options(selectinload(Golpe.tipo), selectinload(Golpe.categoria))
            .order_by(func.lower(Golpe.nome))
        ).scalars()
    )


def listar_itens_ativos() -> list[Item]:
    return list(
        db.session.execute(
            select(Item).where(Item.ativo.is_(True)).order_by(func.lower(Item.nome))
        ).scalars()
    )


def _buscar_por_nome(modelo, nome: str):
    nome = nome.strip()
    if not nome:
        return None
    return db.session.execute(
        select(modelo)
        .where(modelo.ativo.is_(True), func.lower(modelo.nome) == nome.lower())
        .order_by(modelo.id)
    ).scalars().first()


def buscar_forma(nome: str) -> FormaPokemon | None:
    forma = _buscar_por_nome(FormaPokemon, nome)
    if forma is None:
        return None
    # As relações necessárias ao cálculo podem não estar carregadas no objeto
    # retornado por uma consulta simples. Recarregamos com o mesmo perfil usado
    # nas fichas.
    return db.session.execute(
        select(FormaPokemon)
        .where(FormaPokemon.id == forma.id)
        .options(
            selectinload(FormaPokemon.tipos).selectinload(FormaPokemonTipo.tipo),
            selectinload(FormaPokemon.atributos_base).selectinload(
                FormaPokemonAtributo.atributo
            ),
        )
    ).scalar_one()


def _buscar_pokemon_contexto(
    personagem_id: uuid.UUID,
    pokemon_id: str | uuid.UUID,
    *,
    bloquear: bool = False,
) -> Pokemon | None:
    identificador = _resolver_uuid(pokemon_id, "pokemon")
    consulta = select(Pokemon).where(
        Pokemon.id == identificador,
        Pokemon.personagem_id == personagem_id,
        Pokemon.ativo.is_(True),
    )
    if bloquear:
        consulta = consulta.with_for_update()
    return db.session.execute(consulta).scalar_one_or_none()


def _snapshot(pokemon: Pokemon) -> dict[str, Any]:
    return {
        "forma_pokemon_id": str(pokemon.forma_pokemon_id),
        "apelido": pokemon.apelido,
        "genero": pokemon.genero,
        "shiny": pokemon.shiny,
        "natureza_id": str(pokemon.natureza_id) if pokemon.natureza_id else None,
        "pv_atual": pokemon.pv_atual,
        "item_equipado_id": str(pokemon.item_equipado_id) if pokemon.item_equipado_id else None,
        "localizacao": pokemon.localizacao,
        "posicao": pokemon.posicao,
        "anotacoes": pokemon.anotacoes,
    }


def _auditar(
    *,
    usuario_id: str | uuid.UUID | None,
    pokemon: Pokemon,
    acao: str,
    antes: dict[str, Any] | None,
    depois: dict[str, Any] | None,
) -> None:
    identificador_usuario = None
    if usuario_id:
        try:
            identificador_usuario = uuid.UUID(str(usuario_id))
        except (TypeError, ValueError):
            identificador_usuario = None
    db.session.add(
        HistoricoAlteracao(
            usuario_id=identificador_usuario,
            entidade="pokemon",
            registro_id=pokemon.id,
            acao=acao,
            dados_anteriores=antes,
            dados_novos=depois,
        )
    )


def _atributos_pokemon() -> list[Atributo]:
    return list(
        db.session.execute(
            select(Atributo)
            .where(
                Atributo.ativo.is_(True),
                Atributo.escopo.in_(["pokemon", "ambos"]),
            )
            .order_by(Atributo.ordem)
        ).scalars()
    )


def _sincronizar_bonus(pokemon: Pokemon, formulario: Any) -> None:
    atuais = {item.atributo_id: item for item in pokemon.bonus_atributos}
    atributos = _atributos_pokemon()
    ids_desejados: set[uuid.UUID] = set()
    for atributo in atributos:
        valor = _inteiro(formulario.get(f"bonus_{atributo.codigo}"), 0)
        ids_desejados.add(atributo.id)
        registro = atuais.get(atributo.id)
        if registro is None:
            registro = PokemonBonusAtributo(
                pokemon=pokemon,
                atributo=atributo,
                valor=valor,
            )
            db.session.add(registro)
        else:
            registro.valor = valor
    for atributo_id, registro in atuais.items():
        if atributo_id not in ids_desejados:
            db.session.delete(registro)


def _sincronizar_golpes(
    pokemon: Pokemon,
    nomes: Iterable[str],
    limite: int,
) -> list[str]:
    erros: list[str] = []
    desejados: list[Golpe] = []
    usados: set[uuid.UUID] = set()
    for nome in list(nomes)[:limite]:
        nome = str(nome).strip()
        if not nome:
            continue
        golpe = _buscar_por_nome(Golpe, nome)
        if golpe is None:
            erros.append(f'O golpe "{nome}" não existe no catálogo do banco.')
            continue
        if golpe.id in usados:
            erros.append(f'O golpe "{nome}" foi informado mais de uma vez.')
            continue
        usados.add(golpe.id)
        desejados.append(golpe)
    if erros:
        return erros

    for registro in list(pokemon.golpes):
        db.session.delete(registro)
    db.session.flush()
    for posicao, golpe in enumerate(desejados, start=1):
        db.session.add(PokemonGolpe(pokemon=pokemon, golpe=golpe, posicao=posicao))
    return []


def _sincronizar_status(pokemon: Pokemon, nome: str) -> list[str]:
    nome = nome.strip()
    desejado = None
    if nome and nome.casefold() != "nenhum":
        desejado = _buscar_por_nome(StatusCondicao, nome)
        if desejado is None:
            return ["Selecione um status disponível no banco."]
    for registro in list(pokemon.status_ativos):
        db.session.delete(registro)
    db.session.flush()
    if desejado:
        db.session.add(PokemonStatus(pokemon=pokemon, status=desejado))
    return []


def _sincronizar_item(pokemon: Pokemon, nome: str) -> list[str]:
    nome = nome.strip()
    if not nome:
        pokemon.item_equipado_id = None
        return []
    item = _buscar_por_nome(Item, nome)
    if item is None:
        return ["Selecione um item existente no catálogo do banco."]
    pokemon.item_equipado_id = item.id
    return []


def _recarregar_pokemon(pokemon_id: uuid.UUID, personagem_id: uuid.UUID) -> Pokemon:
    # A coleção Personagem.pokemons pode ter sido carregada antes da inclusão ou
    # alteração atual. Expirar o mapa de identidade evita reutilizar essa coleção
    # antiga e garante que golpes, status, bônus e item sejam relidos do banco.
    db.session.expire_all()
    personagem = carregar_personagem_pokemon(personagem_id)
    assert personagem is not None
    return next(item for item in personagem.pokemons if item.id == pokemon_id)


def criar_pokemon_box(
    *,
    personagem: Personagem,
    forma: FormaPokemon,
    regras: dict[str, Any],
    usuario_responsavel_id: str | uuid.UUID | None,
) -> Pokemon:
    limite = int(regras.get("boxes", {}).get("espacos", 100))
    ocupados = db.session.scalar(
        select(func.count(Pokemon.id)).where(
            Pokemon.personagem_id == personagem.id,
            Pokemon.ativo.is_(True),
            Pokemon.localizacao == "box",
        )
    ) or 0
    if ocupados >= limite:
        raise ValueError("A Box está cheia.")
    ultima = db.session.scalar(
        select(func.max(Pokemon.posicao)).where(
            Pokemon.personagem_id == personagem.id,
            Pokemon.ativo.is_(True),
            Pokemon.localizacao == "box",
        )
    ) or 0
    natureza = db.session.execute(
        select(Natureza)
        .where(Natureza.ativo.is_(True))
        .order_by(
            (func.lower(Natureza.nome) != "dócil"),
            func.lower(Natureza.nome),
        )
    ).scalars().first()
    pokemon = Pokemon(
        personagem_id=personagem.id,
        forma_pokemon_id=forma.id,
        genero="Ø",
        shiny=False,
        natureza_id=natureza.id if natureza else None,
        pv_atual=0,
        localizacao="box",
        posicao=int(ultima) + 1,
        ativo=True,
    )
    db.session.add(pokemon)
    db.session.flush()
    pokemon = _recarregar_pokemon(pokemon.id, personagem.id)
    pokemon.pv_atual = calcular_pokemon(pokemon, personagem, regras)["totais"].get("pv", 0)
    _auditar(
        usuario_id=usuario_responsavel_id,
        pokemon=pokemon,
        acao="criacao",
        antes=None,
        depois=_snapshot(pokemon),
    )
    db.session.commit()
    return pokemon


def atualizar_pokemon_formulario(
    *,
    contexto: ContextoPokemon,
    pokemon_id: str,
    formulario: Any,
    usuario_responsavel_id: str | uuid.UUID | None,
    permitir_identidade: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    pokemon = _buscar_pokemon_contexto(contexto.personagem.id, pokemon_id, bloquear=True)
    if pokemon is None:
        return None, ["Pokémon não encontrado na ficha deste jogador."]
    antes = _snapshot(pokemon)
    erros: list[str] = []

    # A autorização também fica no serviço, não só no formulário/rota.
    # Campos omitidos por usuários comuns não podem apagar dados existentes.
    campos_restritos = ("especie_nome", "genero", "natureza", "shiny")
    if not permitir_identidade and any(campo in formulario for campo in campos_restritos):
        db.session.rollback()
        return None, ["Apenas Admin/Mestre ou Tester pode alterar espécie, gênero, natureza ou Shiny."]
    if permitir_identidade:
        forma = buscar_forma(str(formulario.get("especie_nome", "")))
        if forma is None:
            erros.append("Selecione uma espécie ou forma existente no banco.")
        else:
            pokemon.forma_pokemon_id = forma.id

        genero = str(formulario.get("genero", "Ø")).strip() or "Ø"
        if genero not in contexto.regras.get("generos", []):
            erros.append("Selecione um gênero disponível na configuração atual.")
        else:
            pokemon.genero = genero

        natureza_nome = str(formulario.get("natureza", "")).strip()
        natureza = _buscar_por_nome(Natureza, natureza_nome) if natureza_nome else None
        if natureza_nome and natureza is None:
            erros.append("Selecione uma natureza disponível no banco.")
        else:
            pokemon.natureza_id = natureza.id if natureza else None

        pokemon.shiny = formulario.get("shiny") == "1"

    pokemon.apelido = str(formulario.get("apelido", "")).strip() or None
    pokemon.anotacoes = str(formulario.get("anotacoes", "")).strip() or None

    # Itens equipados são alterados exclusivamente pela tela de inventário.
    erros.extend(_sincronizar_status(pokemon, str(formulario.get("status", "Nenhum"))))
    erros.extend(
        _sincronizar_golpes(
            pokemon,
            formulario.getlist("golpe_nome"),
            int(contexto.regras.get("limites", {}).get("golpes_por_pokemon", 4)),
        )
    )
    _sincronizar_bonus(pokemon, formulario)
    db.session.flush()

    if erros:
        db.session.rollback()
        return None, erros

    recarregado = _recarregar_pokemon(pokemon.id, contexto.personagem.id)
    calculos = calcular_pokemon(recarregado, contexto.personagem, contexto.regras)
    pv_maximo = int(calculos["totais"].get("pv", 0))
    pv_atual = _inteiro(formulario.get("pv_atual"), recarregado.pv_atual)
    if pv_atual < 0 or pv_atual > pv_maximo:
        db.session.rollback()
        return None, [f"Os PV atuais devem estar entre 0 e {pv_maximo}."]
    recarregado.pv_atual = pv_atual
    _auditar(
        usuario_id=usuario_responsavel_id,
        pokemon=recarregado,
        acao="edicao",
        antes=antes,
        depois=_snapshot(recarregado),
    )
    db.session.commit()

    contexto_atualizado = carregar_contexto_pokemon(contexto.personagem.id)
    assert contexto_atualizado is not None
    atualizado = next(
        item
        for item in contexto_atualizado.personagem.pokemons
        if str(item.id) == str(pokemon_id)
    )
    return registro_detalhado(
        atualizado, contexto_atualizado.personagem, contexto_atualizado.regras
    ), []


def _compactar_posicoes(personagem_id: uuid.UUID, localizacao: str) -> None:
    registros = list(
        db.session.execute(
            select(Pokemon)
            .where(
                Pokemon.personagem_id == personagem_id,
                Pokemon.ativo.is_(True),
                Pokemon.localizacao == localizacao,
            )
            .order_by(Pokemon.posicao, Pokemon.criado_em, Pokemon.id)
            .with_for_update()
        ).scalars()
    )
    deslocamento = len(registros) + 1000
    for indice, pokemon in enumerate(registros, start=1):
        pokemon.posicao = deslocamento + indice
    db.session.flush()
    for indice, pokemon in enumerate(registros, start=1):
        pokemon.posicao = indice


def mover_pokemon_db(
    *,
    contexto: ContextoPokemon,
    pokemon_id: str,
    destino: str,
    usuario_responsavel_id: str | uuid.UUID | None,
) -> str | None:
    pokemon = _buscar_pokemon_contexto(contexto.personagem.id, pokemon_id, bloquear=True)
    if pokemon is None:
        return "Pokémon não encontrado na ficha."
    antes = _snapshot(pokemon)
    destino = destino.strip()

    if destino == "equipe":
        if pokemon.localizacao == "equipe":
            return None
        limite = int(contexto.regras.get("limites", {}).get("tamanho_equipe", 6))
        total = db.session.scalar(
            select(func.count(Pokemon.id)).where(
                Pokemon.personagem_id == contexto.personagem.id,
                Pokemon.ativo.is_(True),
                Pokemon.localizacao == "equipe",
            )
        ) or 0
        if total >= limite:
            return f"A equipe já possui o limite de {limite} Pokémon."
        ultima_posicao = db.session.scalar(
            select(func.max(Pokemon.posicao)).where(
                Pokemon.personagem_id == contexto.personagem.id,
                Pokemon.ativo.is_(True),
                Pokemon.localizacao == "equipe",
            )
        ) or 0
        pokemon.localizacao = "equipe"
        pokemon.posicao = int(ultima_posicao) + 1
        db.session.flush()
        _compactar_posicoes(contexto.personagem.id, "box")
    elif destino == f"box:{BOX_ID}":
        if pokemon.localizacao == "box":
            return None
        limite = int(contexto.regras.get("boxes", {}).get("espacos", 100))
        total = db.session.scalar(
            select(func.count(Pokemon.id)).where(
                Pokemon.personagem_id == contexto.personagem.id,
                Pokemon.ativo.is_(True),
                Pokemon.localizacao == "box",
            )
        ) or 0
        if total >= limite:
            return "A Box está cheia."
        ultima_posicao = db.session.scalar(
            select(func.max(Pokemon.posicao)).where(
                Pokemon.personagem_id == contexto.personagem.id,
                Pokemon.ativo.is_(True),
                Pokemon.localizacao == "box",
            )
        ) or 0
        pokemon.localizacao = "box"
        pokemon.posicao = int(ultima_posicao) + 1
        # Pokémon guardados na Box não permanecem no campo de batalha.
        from app.models.db import PokemonEmCampo
        registro_campo = db.session.execute(
            select(PokemonEmCampo).where(PokemonEmCampo.pokemon_id == pokemon.id)
        ).scalar_one_or_none()
        if registro_campo is not None:
            db.session.delete(registro_campo)
        db.session.flush()
        _compactar_posicoes(contexto.personagem.id, "equipe")
    else:
        return "Selecione um destino válido."

    _auditar(
        usuario_id=usuario_responsavel_id,
        pokemon=pokemon,
        acao="movimentacao",
        antes=antes,
        depois=_snapshot(pokemon),
    )
    db.session.commit()
    return None


def remover_pokemon_db(
    *,
    contexto: ContextoPokemon,
    pokemon_id: str,
    usuario_responsavel_id: str | uuid.UUID | None,
) -> bool:
    pokemon = _buscar_pokemon_contexto(contexto.personagem.id, pokemon_id, bloquear=True)
    if pokemon is None:
        return False
    localizacao = pokemon.localizacao
    antes = _snapshot(pokemon)
    pokemon.ativo = False
    pokemon.localizacao = None
    pokemon.posicao = None
    # Limpeza do campo na mesma transação da remoção da ficha.
    from app.models.db import PokemonEmCampo
    registro_campo = db.session.execute(
        select(PokemonEmCampo).where(PokemonEmCampo.pokemon_id == pokemon.id)
    ).scalar_one_or_none()
    if registro_campo is not None:
        db.session.delete(registro_campo)
    _auditar(
        usuario_id=usuario_responsavel_id,
        pokemon=pokemon,
        acao="remocao",
        antes=antes,
        depois={"ativo": False},
    )
    db.session.flush()
    if localizacao in {"equipe", "box"}:
        _compactar_posicoes(contexto.personagem.id, localizacao)
    db.session.commit()
    return True


def renomear_box_db(campanha_id: uuid.UUID, nome: str) -> str | None:
    nome = nome.strip()
    if not nome:
        return "Informe um nome para a Box."
    if len(nome) > 60:
        return "O nome da Box deve possuir no máximo 60 caracteres."
    conjunto, _ = _valores_regras(campanha_id)
    if conjunto is None:
        return "Nenhum conjunto de regras ativo foi encontrado."
    regra = db.session.execute(select(Regra).where(Regra.codigo == "nome-box")).scalar_one_or_none()
    if regra is None:
        regra = Regra(
            codigo="nome-box",
            nome="Nome da Box",
            categoria="limites",
            tipo_valor="texto",
            valor_padrao="Box Pokémon",
            ativo=True,
        )
        db.session.add(regra)
        db.session.flush()
    valor = db.session.execute(
        select(RegraValor).where(
            RegraValor.conjunto_regras_id == conjunto.id,
            RegraValor.regra_id == regra.id,
        )
    ).scalar_one_or_none()
    if valor is None:
        valor = RegraValor(conjunto_regras=conjunto, regra=regra, valor=nome)
        db.session.add(valor)
    else:
        valor.valor = nome
    db.session.commit()
    return None


def total_formas_ativas() -> int:
    return int(db.session.scalar(select(func.count(FormaPokemon.id)).where(FormaPokemon.ativo.is_(True))) or 0)


def pesquisar_formas_autocomplete(termo: str, *, limite: int = 20) -> list[dict[str, Any]]:
    """Resultados enriquecidos para a busca visual, sem carregar todo o catálogo."""
    from app.services.tipos_visual import tipo_visual

    termo = str(termo or "").strip()[:100]
    consulta = (
        select(FormaPokemon)
        .join(EspeciePokemon, EspeciePokemon.id == FormaPokemon.especie_id)
        .options(
            selectinload(FormaPokemon.especie),
            selectinload(FormaPokemon.tipos).selectinload(FormaPokemonTipo.tipo),
        )
        .where(FormaPokemon.ativo.is_(True), EspeciePokemon.ativo.is_(True))
    )
    if termo:
        padrao = f"%{termo.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(FormaPokemon.nome).like(padrao),
                func.lower(FormaPokemon.codigo).like(padrao),
                func.lower(EspeciePokemon.nome).like(padrao),
            )
        )
    formas = list(db.session.execute(
        consulta.order_by(func.lower(FormaPokemon.nome)).limit(max(1, min(int(limite), 50)))
    ).scalars())
    return [
        {
            # O campo "valor" permanece o nome para os formulários já existentes;
            # "id" é o UUID estável usado pelo formulário de capturáveis.
            "id": str(forma.id),
            "valor": forma.nome,
            "rotulo": forma.nome,
            "detalhe": f"{forma.especie.nome} · {forma.categoria.title()}",
            "imagem": forma.imagem_url or "",
            "tipos": [tipo_visual(rel.tipo.nome) for rel in sorted(forma.tipos, key=lambda item: item.posicao)],
        }
        for forma in formas
    ]


def pesquisar_golpes_autocomplete(termo: str, *, limite: int = 20) -> list[dict[str, Any]]:
    """Devolve os metadados visuais para uma prévia sem salvar o Pokémon."""
    from app.services.tipos_visual import tipo_visual

    termo = str(termo or "").strip()[:100]
    consulta = select(Golpe).options(
        selectinload(Golpe.tipo), selectinload(Golpe.categoria)
    ).where(Golpe.ativo.is_(True))
    if termo:
        padrao = f"%{termo.lower()}%"
        consulta = consulta.where(
            or_(func.lower(Golpe.nome).like(padrao), func.lower(Golpe.codigo).like(padrao))
        )
    golpes = list(db.session.execute(
        consulta.order_by(func.lower(Golpe.nome)).limit(max(1, min(int(limite), 50)))
    ).scalars())
    resultado: list[dict[str, Any]] = []
    for golpe in golpes:
        dados = _golpe_para_dict(golpe)
        tipo = tipo_visual(dados["tipo"]) if golpe.tipo else None
        resultado.append({
            "valor": dados["nome"],
            "rotulo": dados["nome"],
            "detalhe": " · ".join(parte for parte in [
                dados["categoria"], dados["dano"] or "Sem dano",
            ] if parte and parte != "—"),
            "tipos": [tipo] if tipo else [],
            "imagem": "",  # O catálogo não possui imagens de golpes.
            "tipo": dados["tipo"],
            "categoria": dados["categoria"],
            "dano": dados["dano"] or "—",
            "precisao_texto": dados["precisao_texto"],
            "prioridade": dados["prioridade"],
            "efeito": dados["efeito"],
        })
    return resultado


def pesquisar_itens_autocomplete(termo: str, *, limite: int = 20) -> list[dict[str, Any]]:
    termo = str(termo or "").strip()[:100]
    consulta = select(Item).options(selectinload(Item.categoria)).where(Item.ativo.is_(True))
    if termo:
        padrao = f"%{termo.lower()}%"
        consulta = consulta.where(or_(
            func.lower(Item.nome).like(padrao),
            func.lower(Item.codigo).like(padrao),
            Item.categoria.has(func.lower(CategoriaItem.nome).like(padrao)),
        ))
    itens = list(db.session.execute(
        consulta.order_by(func.lower(Item.nome)).limit(max(1, min(int(limite), 50)))
    ).scalars())
    return [
        {
            "valor": str(item.id),
            "rotulo": item.nome,
            "detalhe": item.categoria.nome if item.categoria else "Sem categoria",
            "imagem": item.imagem_url or "",
            "tags": (["Consumível"] if item.consumivel else []) + (["Equipável"] if item.equipavel else []),
        }
        for item in itens
    ]


def nomes_formas() -> list[str]:
    return [item.nome for item in listar_formas_ativas()]


def nomes_golpes() -> list[str]:
    return [item.nome for item in listar_golpes_ativos()]


def nomes_itens() -> list[str]:
    return [item.nome for item in listar_itens_ativos()]


def golpes_formulario(pokemon: Pokemon, limite: int) -> list[dict[str, Any]]:
    resultado = [
        _golpe_para_dict(item.golpe)
        for item in sorted(pokemon.golpes, key=lambda rel: rel.posicao)
        if item.golpe.ativo
    ]
    while len(resultado) < limite:
        resultado.append({"id": "", "nome": ""})
    return resultado[:limite]
