from __future__ import annotations

import copy
import json
import math
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Atributo,
    CategoriaGolpe,
    EspeciePokemon,
    FormaPokemon,
    FormaPokemonGolpe,
    Golpe,
    HistoricoAlteracao,
    StatusCondicao,
    TipoPokemon,
)
from app.services.importacao.utils import slug

TIPOS_EFEITO = (
    ("texto", "Efeito textual"),
    ("aplicar_status", "Aplicar status"),
    ("alterar_atributo", "Alterar atributo"),
    ("dano_adicional", "Dano adicional"),
    ("cura", "Cura ou recuperação"),
    ("multiplos_ataques", "Múltiplos ataques"),
    ("condicao", "Condição especial"),
)

ALVOS_EFEITO = (
    ("oponente", "Oponente"),
    ("usuario", "Usuário do golpe"),
    ("aliado", "Aliado"),
    ("todos_oponentes", "Todos os oponentes"),
    ("todos", "Todos em campo"),
    ("campo", "Campo de batalha"),
)

OPERACOES_ATRIBUTO = (
    ("percentual", "Percentual"),
    ("fixo", "Valor fixo"),
    ("estagio", "Estágio"),
)

MODOS_CURA = (
    ("percentual_pv_maximo", "% do PV máximo"),
    ("percentual_dano", "% do dano causado"),
    ("fixo", "Valor fixo"),
    ("dados", "Expressão de dados"),
)

METODOS_APRENDIZADO = (
    ("nivel", "Por nível"),
    ("mt", "MT/TR"),
    ("tutor", "Tutor"),
    ("ovo", "Movimento de ovo"),
    ("evento", "Evento"),
    ("inicial", "Inicial"),
    ("personalizado", "Personalizado"),
)


@dataclass(slots=True)
class PaginaGolpes:
    itens: list[Golpe]
    pagina: int
    por_pagina: int
    total: int

    @property
    def paginas(self) -> int:
        return max(1, math.ceil(self.total / self.por_pagina))

    @property
    def tem_anterior(self) -> bool:
        return self.pagina > 1

    @property
    def tem_proxima(self) -> bool:
        return self.pagina < self.paginas


@dataclass(slots=True)
class PaginaFormasVinculo:
    itens: list[FormaPokemon]
    pagina: int
    por_pagina: int
    total: int

    @property
    def paginas(self) -> int:
        return max(1, math.ceil(self.total / self.por_pagina))

    @property
    def tem_anterior(self) -> bool:
        return self.pagina > 1

    @property
    def tem_proxima(self) -> bool:
        return self.pagina < self.paginas


@dataclass(slots=True)
class OpcoesGolpes:
    tipos: list[TipoPokemon]
    categorias: list[CategoriaGolpe]
    atributos: list[Atributo]
    status: list[StatusCondicao]


def _uuid(valor: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError):
        return None


def _decimal(valor: Any, *, padrao: Decimal | None = Decimal("0")) -> Decimal | None:
    try:
        texto = str(valor if valor is not None else "").strip().replace(",", ".")
        if not texto:
            return padrao
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return padrao


def _numero_json(valor: Decimal | int | None) -> int | float | None:
    if valor is None:
        return None
    numero = Decimal(valor)
    return int(numero) if numero == numero.to_integral_value() else float(numero)


def _existe_codigo(modelo, codigo: str, *, ignorar_id: uuid.UUID | None = None) -> bool:
    consulta = select(modelo.id).where(func.lower(modelo.codigo) == codigo.lower())
    if ignorar_id:
        consulta = consulta.where(modelo.id != ignorar_id)
    return db.session.execute(consulta).first() is not None


def opcoes_golpes() -> OpcoesGolpes:
    tipos = list(
        db.session.execute(
            select(TipoPokemon)
            .where(TipoPokemon.ativo.is_(True))
            .order_by(func.lower(TipoPokemon.nome))
        ).scalars()
    )
    categorias = list(
        db.session.execute(
            select(CategoriaGolpe)
            .where(CategoriaGolpe.ativo.is_(True))
            .order_by(func.lower(CategoriaGolpe.nome))
        ).scalars()
    )
    atributos = list(
        db.session.execute(
            select(Atributo)
            .where(Atributo.ativo.is_(True), Atributo.escopo.in_(["pokemon", "ambos"]))
            .order_by(Atributo.ordem, func.lower(Atributo.nome))
        ).scalars()
    )
    status = list(
        db.session.execute(
            select(StatusCondicao)
            .where(StatusCondicao.ativo.is_(True))
            .order_by(func.lower(StatusCondicao.nome))
        ).scalars()
    )
    return OpcoesGolpes(
        tipos=tipos,
        categorias=categorias,
        atributos=atributos,
        status=status,
    )


def resumo_golpes() -> dict[str, int]:
    return {
        "golpes": int(db.session.scalar(select(func.count(Golpe.id))) or 0),
        "golpes_ativos": int(
            db.session.scalar(select(func.count(Golpe.id)).where(Golpe.ativo.is_(True))) or 0
        ),
        "categorias_golpe": int(
            db.session.scalar(
                select(func.count(CategoriaGolpe.id)).where(CategoriaGolpe.ativo.is_(True))
            )
            or 0
        ),
        "vinculos_golpe": int(db.session.scalar(select(func.count(FormaPokemonGolpe.id))) or 0),
    }


def listar_golpes_admin(
    *,
    termo: str = "",
    tipo_id: str = "",
    categoria_id: str = "",
    situacao: str = "ativos",
    origem: str = "todas",
    pagina: int = 1,
    por_pagina: int = 36,
) -> PaginaGolpes:
    consulta = (
        select(Golpe)
        .options(selectinload(Golpe.tipo), selectinload(Golpe.categoria))
        .join(CategoriaGolpe, Golpe.categoria_id == CategoriaGolpe.id)
        .outerjoin(TipoPokemon, Golpe.tipo_id == TipoPokemon.id)
    )
    termo = termo.strip()
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.where(
            or_(
                Golpe.nome.ilike(padrao),
                Golpe.codigo.ilike(padrao),
                Golpe.descricao.ilike(padrao),
                cast(Golpe.efeitos, String).ilike(padrao),
            )
        )
    tipo_uuid = _uuid(tipo_id)
    if tipo_uuid:
        consulta = consulta.where(Golpe.tipo_id == tipo_uuid)
    categoria_uuid = _uuid(categoria_id)
    if categoria_uuid:
        consulta = consulta.where(Golpe.categoria_id == categoria_uuid)
    if situacao == "ativos":
        consulta = consulta.where(Golpe.ativo.is_(True))
    elif situacao == "inativos":
        consulta = consulta.where(Golpe.ativo.is_(False))
    if origem == "personalizados":
        consulta = consulta.where(Golpe.personalizado.is_(True))
    elif origem == "oficiais":
        consulta = consulta.where(Golpe.personalizado.is_(False))

    pagina = max(1, int(pagina or 1))
    subconsulta = consulta.with_only_columns(Golpe.id).order_by(None).subquery()
    total = int(db.session.scalar(select(func.count()).select_from(subconsulta)) or 0)
    itens = list(
        db.session.execute(
            consulta.order_by(func.lower(Golpe.nome))
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        ).scalars().unique()
    )
    return PaginaGolpes(itens=itens, pagina=pagina, por_pagina=por_pagina, total=total)


def carregar_golpe_admin(golpe_id: str | uuid.UUID) -> Golpe | None:
    identificador = _uuid(golpe_id)
    if not identificador:
        return None
    return db.session.execute(
        select(Golpe)
        .where(Golpe.id == identificador)
        .options(
            selectinload(Golpe.tipo),
            selectinload(Golpe.categoria),
            selectinload(Golpe.formas)
            .selectinload(FormaPokemonGolpe.forma_pokemon)
            .selectinload(FormaPokemon.especie),
        )
    ).scalar_one_or_none()


def efeitos_para_editor(efeitos: Any) -> list[dict[str, Any]]:
    if not efeitos:
        return []
    if isinstance(efeitos, list):
        return [copy.deepcopy(item) for item in efeitos if isinstance(item, dict)]
    if not isinstance(efeitos, dict):
        return []
    if isinstance(efeitos.get("efeitos"), list):
        return [copy.deepcopy(item) for item in efeitos["efeitos"] if isinstance(item, dict)]
    if "texto" in efeitos and "tipo" not in efeitos:
        return [{"tipo": "texto", "texto": str(efeitos.get("texto") or "")}]
    if "tipo" in efeitos:
        return [copy.deepcopy(efeitos)]
    return [{"tipo": "texto", "texto": json.dumps(efeitos, ensure_ascii=False)}]


def _percentual(valor: Any, *, padrao: Decimal = Decimal("100")) -> Decimal:
    numero = _decimal(valor, padrao=padrao)
    assert numero is not None
    return numero


def _texto(valor: Any, limite: int = 2000) -> str:
    return str(valor or "").strip()[:limite]


def _validar_efeitos_json(valor: str | None) -> tuple[dict[str, Any] | None, list[str]]:
    if not valor or not valor.strip():
        return None, []
    try:
        bruto = json.loads(valor)
    except json.JSONDecodeError:
        return None, ["O editor de efeitos enviou um conteúdo inválido. Atualize a página e tente novamente."]
    itens = bruto.get("efeitos", []) if isinstance(bruto, dict) else bruto
    if not isinstance(itens, list):
        return None, ["A estrutura dos efeitos deve conter uma lista."]
    if len(itens) > 20:
        return None, ["Um golpe pode possuir no máximo 20 efeitos configurados."]

    opcoes = opcoes_golpes()
    atributos = {item.codigo: item for item in opcoes.atributos}
    status_ids = {str(item.id) for item in opcoes.status}
    tipos_validos = {item[0] for item in TIPOS_EFEITO}
    alvos_validos = {item[0] for item in ALVOS_EFEITO}
    operacoes_validas = {item[0] for item in OPERACOES_ATRIBUTO}
    modos_cura_validos = {item[0] for item in MODOS_CURA}

    normalizados: list[dict[str, Any]] = []
    erros: list[str] = []
    for indice, item in enumerate(itens, start=1):
        if not isinstance(item, dict):
            erros.append(f"Efeito {indice}: conteúdo inválido.")
            continue
        tipo = str(item.get("tipo", "texto")).strip()
        if tipo not in tipos_validos:
            erros.append(f"Efeito {indice}: tipo não reconhecido.")
            continue
        alvo = str(item.get("alvo", "oponente")).strip()
        if alvo not in alvos_validos:
            alvo = "oponente"
        chance = _percentual(item.get("chance", 100))
        if chance < 0 or chance > 100:
            erros.append(f"Efeito {indice}: a chance deve estar entre 0 e 100.")
            continue
        base: dict[str, Any] = {
            "tipo": tipo,
            "alvo": alvo,
            "chance": _numero_json(chance),
        }

        if tipo == "texto":
            texto = _texto(item.get("texto"))
            if not texto:
                erros.append(f"Efeito {indice}: informe o texto do efeito.")
                continue
            base["texto"] = texto
        elif tipo == "aplicar_status":
            status_id = str(item.get("status_id", "")).strip()
            if status_id not in status_ids:
                erros.append(f"Efeito {indice}: selecione um status ativo.")
                continue
            base["status_id"] = status_id
            duracao = _texto(item.get("duracao"), 80)
            if duracao:
                base["duracao"] = duracao
        elif tipo == "alterar_atributo":
            atributo = str(item.get("atributo", "")).strip()
            if atributo not in atributos:
                erros.append(f"Efeito {indice}: selecione um atributo ativo.")
                continue
            operacao = str(item.get("operacao", "percentual")).strip()
            if operacao not in operacoes_validas:
                erros.append(f"Efeito {indice}: operação de atributo inválida.")
                continue
            valor_numero = _decimal(item.get("valor"), padrao=None)
            if valor_numero is None:
                erros.append(f"Efeito {indice}: informe o valor da alteração.")
                continue
            base.update(
                atributo=atributo,
                operacao=operacao,
                valor=_numero_json(valor_numero),
            )
        elif tipo == "dano_adicional":
            expressao = _texto(item.get("expressao"), 80)
            if not expressao:
                erros.append(f"Efeito {indice}: informe a expressão do dano adicional.")
                continue
            base["expressao"] = expressao
        elif tipo == "cura":
            modo = str(item.get("modo", "percentual_pv_maximo")).strip()
            if modo not in modos_cura_validos:
                erros.append(f"Efeito {indice}: modo de cura inválido.")
                continue
            base["modo"] = modo
            if modo == "dados":
                expressao = _texto(item.get("expressao"), 80)
                if not expressao:
                    erros.append(f"Efeito {indice}: informe a expressão de cura.")
                    continue
                base["expressao"] = expressao
            else:
                valor_numero = _decimal(item.get("valor"), padrao=None)
                if valor_numero is None or valor_numero < 0:
                    erros.append(f"Efeito {indice}: informe um valor de cura válido.")
                    continue
                base["valor"] = _numero_json(valor_numero)
        elif tipo == "multiplos_ataques":
            try:
                minimo = int(item.get("minimo", 2))
                maximo = int(item.get("maximo", minimo))
            except (TypeError, ValueError):
                erros.append(f"Efeito {indice}: quantidades de ataques inválidas.")
                continue
            if minimo < 2 or maximo < minimo or maximo > 20:
                erros.append(f"Efeito {indice}: use entre 2 e 20 ataques, com máximo maior ou igual ao mínimo.")
                continue
            base.update(minimo=minimo, maximo=maximo)
        elif tipo == "condicao":
            descricao = _texto(item.get("descricao"))
            if not descricao:
                erros.append(f"Efeito {indice}: descreva a condição especial.")
                continue
            base["descricao"] = descricao

        observacao = _texto(item.get("observacao"), 500)
        if observacao:
            base["observacao"] = observacao
        normalizados.append(base)

    if erros:
        return None, erros
    return ({"versao": 1, "efeitos": normalizados} if normalizados else None), []


def _snapshot_golpe(golpe: Golpe) -> dict[str, Any]:
    return {
        "codigo": golpe.codigo,
        "nome": golpe.nome,
        "tipo_id": str(golpe.tipo_id) if golpe.tipo_id else None,
        "categoria_id": str(golpe.categoria_id),
        "expressao_dano": golpe.expressao_dano,
        "precisao": _numero_json(golpe.precisao),
        "prioridade": golpe.prioridade,
        "descricao": golpe.descricao,
        "efeitos": copy.deepcopy(golpe.efeitos),
        "personalizado": golpe.personalizado,
        "ativo": golpe.ativo,
    }


def _snapshot_vinculo(vinculo: FormaPokemonGolpe) -> dict[str, Any]:
    return {
        "forma_pokemon_id": str(vinculo.forma_pokemon_id),
        "golpe_id": str(vinculo.golpe_id),
        "metodo": vinculo.metodo,
        "nivel_requerido": vinculo.nivel_requerido,
        "configuracoes": copy.deepcopy(vinculo.configuracoes),
        "observacoes": vinculo.observacoes,
    }


def _auditar(
    *,
    usuario_id: str | uuid.UUID | None,
    entidade: str,
    registro_id: uuid.UUID,
    acao: str,
    antes: dict[str, Any] | None,
    depois: dict[str, Any] | None,
) -> None:
    db.session.add(
        HistoricoAlteracao(
            usuario_id=_uuid(usuario_id),
            entidade=entidade,
            registro_id=registro_id,
            acao=acao,
            dados_anteriores=antes,
            dados_novos=depois,
        )
    )


def _validar_dados_golpe(
    formulario: Mapping[str, Any],
    *,
    golpe: Golpe | None = None,
) -> tuple[dict[str, Any], list[str]]:
    erros: list[str] = []
    nome = _texto(formulario.get("nome"), 180)
    codigo = slug(formulario.get("codigo") or nome, padrao="golpe")
    if not nome:
        erros.append("Informe o nome do golpe.")
    if _existe_codigo(Golpe, codigo, ignorar_id=golpe.id if golpe else None):
        erros.append(f'O código de golpe "{codigo}" já está em uso.')

    categoria_id = _uuid(formulario.get("categoria_id"))
    categoria = db.session.get(CategoriaGolpe, categoria_id) if categoria_id else None
    if categoria is None or not categoria.ativo:
        erros.append("Selecione uma categoria de golpe ativa.")

    tipo_id = _uuid(formulario.get("tipo_id"))
    tipo = db.session.get(TipoPokemon, tipo_id) if tipo_id else None
    if tipo_id and (tipo is None or not tipo.ativo):
        erros.append("O tipo selecionado não existe ou está inativo.")

    expressao_dano = _texto(formulario.get("expressao_dano"), 80) or None
    precisao = _decimal(formulario.get("precisao"), padrao=None)
    if precisao is not None and (precisao < 0 or precisao > 100):
        erros.append("A precisão deve estar entre 0 e 100.")
    try:
        prioridade = int(str(formulario.get("prioridade", "0")).strip() or 0)
    except ValueError:
        prioridade = 0
        erros.append("A prioridade deve ser um número inteiro.")
    if prioridade < -20 or prioridade > 20:
        erros.append("A prioridade deve ficar entre -20 e 20.")

    efeitos, erros_efeitos = _validar_efeitos_json(str(formulario.get("efeitos_json", "")))
    erros.extend(erros_efeitos)
    return {
        "nome": nome,
        "codigo": codigo,
        "tipo_id": tipo_id,
        "categoria_id": categoria_id,
        "expressao_dano": expressao_dano,
        "precisao": precisao,
        "prioridade": prioridade,
        "descricao": _texto(formulario.get("descricao"), 6000) or None,
        "efeitos": efeitos,
        "personalizado": str(formulario.get("personalizado", "")) == "1",
    }, erros


def criar_golpe_admin(
    formulario: Mapping[str, Any],
    *,
    usuario_id: str | uuid.UUID | None,
) -> tuple[Golpe | None, list[str]]:
    dados, erros = _validar_dados_golpe(formulario)
    if erros:
        db.session.rollback()
        return None, erros
    golpe = Golpe(ativo=True, **dados)
    db.session.add(golpe)
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="golpe",
        registro_id=golpe.id,
        acao="criacao",
        antes=None,
        depois=_snapshot_golpe(golpe),
    )
    db.session.commit()
    return golpe, []


def atualizar_golpe_admin(
    golpe: Golpe,
    formulario: Mapping[str, Any],
    *,
    usuario_id: str | uuid.UUID | None,
) -> list[str]:
    antes = _snapshot_golpe(golpe)
    dados, erros = _validar_dados_golpe(formulario, golpe=golpe)
    if erros:
        db.session.rollback()
        return erros
    for chave, valor in dados.items():
        setattr(golpe, chave, valor)
    db.session.flush()
    depois = _snapshot_golpe(golpe)
    if antes != depois:
        _auditar(
            usuario_id=usuario_id,
            entidade="golpe",
            registro_id=golpe.id,
            acao="edicao",
            antes=antes,
            depois=depois,
        )
    db.session.commit()
    return []


def alterar_atividade_golpe(
    golpe: Golpe,
    *,
    ativo: bool,
    usuario_id: str | uuid.UUID | None,
) -> None:
    antes = _snapshot_golpe(golpe)
    golpe.ativo = ativo
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="golpe",
        registro_id=golpe.id,
        acao="reativacao" if ativo else "desativacao",
        antes=antes,
        depois=_snapshot_golpe(golpe),
    )
    db.session.commit()


def duplicar_golpe_admin(
    golpe: Golpe,
    *,
    usuario_id: str | uuid.UUID | None,
) -> Golpe:
    codigo_base = f"{golpe.codigo}-copia"
    codigo = codigo_base
    sequencia = 2
    while _existe_codigo(Golpe, codigo):
        codigo = f"{codigo_base}-{sequencia}"
        sequencia += 1
    copia = Golpe(
        codigo=codigo,
        nome=f"{golpe.nome} (Cópia)",
        tipo_id=golpe.tipo_id,
        categoria_id=golpe.categoria_id,
        expressao_dano=golpe.expressao_dano,
        precisao=golpe.precisao,
        prioridade=golpe.prioridade,
        descricao=golpe.descricao,
        efeitos=copy.deepcopy(golpe.efeitos),
        personalizado=True,
        ativo=False,
    )
    db.session.add(copia)
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="golpe",
        registro_id=copia.id,
        acao="duplicacao",
        antes={"origem_id": str(golpe.id)},
        depois=_snapshot_golpe(copia),
    )
    db.session.commit()
    return copia


def listar_formas_para_vinculo(
    *,
    termo: str = "",
    pagina: int = 1,
    por_pagina: int = 30,
) -> PaginaFormasVinculo:
    consulta = (
        select(FormaPokemon)
        .where(FormaPokemon.ativo.is_(True))
        .options(selectinload(FormaPokemon.especie))
        .join(FormaPokemon.especie)
    )
    termo = termo.strip()
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.where(
            or_(
                FormaPokemon.nome.ilike(padrao),
                FormaPokemon.codigo.ilike(padrao),
                EspeciePokemon.nome.ilike(padrao),
                EspeciePokemon.codigo.ilike(padrao),
            )
        )
    pagina = max(1, int(pagina or 1))
    subconsulta = consulta.with_only_columns(FormaPokemon.id).order_by(None).subquery()
    total = int(db.session.scalar(select(func.count()).select_from(subconsulta)) or 0)
    itens = list(
        db.session.execute(
            consulta.order_by(func.lower(FormaPokemon.nome))
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        ).scalars().unique()
    )
    return PaginaFormasVinculo(itens=itens, pagina=pagina, por_pagina=por_pagina, total=total)


def vinculos_golpe(golpe: Golpe) -> list[FormaPokemonGolpe]:
    return list(
        db.session.execute(
            select(FormaPokemonGolpe)
            .where(FormaPokemonGolpe.golpe_id == golpe.id)
            .options(
                selectinload(FormaPokemonGolpe.forma_pokemon).selectinload(FormaPokemon.especie)
            )
            .order_by(FormaPokemonGolpe.metodo, FormaPokemonGolpe.nivel_requerido)
        ).scalars()
    )


def salvar_vinculo_golpe(
    golpe: Golpe,
    formulario: Mapping[str, Any],
    *,
    usuario_id: str | uuid.UUID | None,
) -> tuple[FormaPokemonGolpe | None, list[str]]:
    erros: list[str] = []
    forma_id = _uuid(formulario.get("forma_pokemon_id"))
    forma = db.session.get(FormaPokemon, forma_id) if forma_id else None
    if forma is None or not forma.ativo:
        erros.append("Selecione uma forma Pokémon ativa.")
    metodo = str(formulario.get("metodo", "nivel")).strip()
    if metodo not in {item[0] for item in METODOS_APRENDIZADO}:
        erros.append("Selecione um método de aprendizado válido.")
    nivel_texto = str(formulario.get("nivel_requerido", "")).strip()
    nivel_requerido: int | None = None
    if nivel_texto:
        try:
            nivel_requerido = int(nivel_texto)
        except ValueError:
            erros.append("O nível necessário deve ser um número inteiro.")
        else:
            if nivel_requerido < 1 or nivel_requerido > 999:
                erros.append("O nível necessário deve ficar entre 1 e 999.")
    if metodo == "nivel" and nivel_requerido is None:
        erros.append("Informe o nível necessário para este vínculo.")
    if erros:
        return None, erros

    vinculo_id = _uuid(formulario.get("vinculo_id"))
    vinculo = None
    if vinculo_id:
        vinculo = db.session.execute(
            select(FormaPokemonGolpe).where(
                FormaPokemonGolpe.id == vinculo_id,
                FormaPokemonGolpe.golpe_id == golpe.id,
            )
        ).scalar_one_or_none()
        if vinculo is None:
            return None, ["O vínculo informado não foi encontrado."]

    duplicado = db.session.execute(
        select(FormaPokemonGolpe).where(
            FormaPokemonGolpe.forma_pokemon_id == forma.id,
            FormaPokemonGolpe.golpe_id == golpe.id,
            FormaPokemonGolpe.metodo == metodo,
            *([FormaPokemonGolpe.id != vinculo.id] if vinculo else []),
        )
    ).scalar_one_or_none()
    if duplicado is not None:
        if vinculo_id:
            return None, ["Esta forma já possui o mesmo golpe por esse método de aprendizado."]
        vinculo = duplicado

    existente = vinculo is not None
    antes = _snapshot_vinculo(vinculo) if vinculo else None
    vinculo = vinculo or FormaPokemonGolpe(
        forma_pokemon_id=forma.id,
        golpe_id=golpe.id,
        metodo=metodo,
    )
    vinculo.forma_pokemon_id = forma.id
    vinculo.metodo = metodo
    vinculo.nivel_requerido = nivel_requerido
    vinculo.observacoes = _texto(formulario.get("observacoes"), 3000) or None
    configuracoes_texto = str(formulario.get("configuracoes_json", "")).strip()
    if configuracoes_texto:
        try:
            configuracoes = json.loads(configuracoes_texto)
        except json.JSONDecodeError:
            return None, ["As configurações adicionais precisam ser um JSON válido."]
        if not isinstance(configuracoes, dict):
            return None, ["As configurações adicionais devem formar um objeto JSON."]
        vinculo.configuracoes = configuracoes
    else:
        vinculo.configuracoes = None
    if not existente:
        db.session.add(vinculo)
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="forma_pokemon_golpe",
        registro_id=vinculo.id,
        acao="edicao" if existente else "criacao",
        antes=antes,
        depois=_snapshot_vinculo(vinculo),
    )
    db.session.commit()
    return vinculo, []


def remover_vinculo_golpe(
    golpe: Golpe,
    vinculo_id: str | uuid.UUID,
    *,
    usuario_id: str | uuid.UUID | None,
) -> bool:
    identificador = _uuid(vinculo_id)
    if not identificador:
        return False
    vinculo = db.session.execute(
        select(FormaPokemonGolpe).where(
            FormaPokemonGolpe.id == identificador,
            FormaPokemonGolpe.golpe_id == golpe.id,
        )
    ).scalar_one_or_none()
    if vinculo is None:
        return False
    antes = _snapshot_vinculo(vinculo)
    registro_id = vinculo.id
    db.session.delete(vinculo)
    _auditar(
        usuario_id=usuario_id,
        entidade="forma_pokemon_golpe",
        registro_id=registro_id,
        acao="remocao",
        antes=antes,
        depois=None,
    )
    db.session.commit()
    return True
