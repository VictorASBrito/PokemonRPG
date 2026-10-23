from __future__ import annotations

import copy
import json
import math
import uuid
from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Atributo,
    CategoriaItem,
    HistoricoAlteracao,
    Item,
    PersonagemItem,
    Pokemon,
    StatusCondicao,
    TipoPokemon,
)
from app.services.importacao.utils import slug

TIPOS_EFEITO_ITEM = (
    ("texto", "Efeito textual"),
    ("recuperar_pv", "Recuperar PV"),
    ("remover_status", "Remover status"),
    ("alterar_atributo", "Alterar atributo"),
    ("causar_dano", "Causar dano"),
    ("modificar_calculo", "Modificar cálculo"),
    ("evolucao", "Evolução"),
    ("mega_evolucao", "Mega Evolução"),
)

ALVOS_EFEITO_ITEM = (
    ("personagem", "Personagem"),
    ("pokemon", "Pokémon escolhido"),
    ("portador", "Pokémon portador"),
    ("grupo", "Grupo"),
)

OPERACOES_ITEM = (
    ("fixo", "Valor fixo"),
    ("percentual", "Percentual"),
    ("dados", "Expressão de dados"),
)

PRECO_MAXIMO_ITEM = 999_999_999  # Mesmo limite do formulário HTML.


@dataclass(slots=True)
class PaginaItens:
    itens: list[Item]
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
class OpcoesItens:
    categorias: list[CategoriaItem]
    atributos: list[Atributo]
    status: list[StatusCondicao]
    tipos: list[TipoPokemon]


def _uuid(valor: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError):
        return None


def _texto(valor: Any, limite: int = 4000) -> str:
    return str(valor or "").strip()[:limite]


def _inteiro(valor: Any, *, padrao: int = 0) -> int:
    try:
        return int(str(valor if valor is not None else "").strip() or padrao)
    except (TypeError, ValueError):
        return padrao


def _bool_form(valor: Any) -> bool:
    return str(valor or "").strip().lower() in {"1", "true", "on", "sim"}


def _validar_preco_item(valor: Any, erros: list[str]) -> int:
    """Não converter silenciosamente um preço malformado para zero."""
    texto = str(valor if valor is not None else "").strip()
    if not texto:
        return 0
    try:
        preco = int(texto)
    except (TypeError, ValueError):
        erros.append("O preço deve ser um número inteiro em Pokédolares.")
        return 0
    if preco < 0:
        erros.append("O preço não pode ser negativo.")
    elif preco > PRECO_MAXIMO_ITEM:
        erros.append(f"O preço não pode ultrapassar {PRECO_MAXIMO_ITEM} Pokédolares.")
    return preco


def _auditar(
    *,
    usuario_id: str | uuid.UUID | None,
    entidade: str,
    registro_id: uuid.UUID | None,
    acao: str,
    antes: dict[str, Any] | None,
    depois: dict[str, Any] | None,
) -> None:
    responsavel = _uuid(usuario_id)
    db.session.add(
        HistoricoAlteracao(
            usuario_id=responsavel,
            entidade=entidade,
            registro_id=registro_id,
            acao=acao,
            dados_anteriores=antes,
            dados_novos=depois,
        )
    )


def _snapshot(item: Item) -> dict[str, Any]:
    return {
        "codigo": item.codigo,
        "nome": item.nome,
        "categoria_id": str(item.categoria_id) if item.categoria_id else None,
        "descricao": item.descricao,
        "imagem_url": item.imagem_url,
        "preco": item.preco,
        "consumivel": item.consumivel,
        "equipavel": item.equipavel,
        "uso_em_batalha": item.uso_em_batalha,
        "efeitos": copy.deepcopy(item.efeitos),
        "personalizado": item.personalizado,
        "ativo": item.ativo,
    }


def opcoes_itens() -> OpcoesItens:
    categorias = list(
        db.session.execute(
            select(CategoriaItem)
            .where(CategoriaItem.ativo.is_(True))
            .order_by(func.lower(CategoriaItem.nome))
        ).scalars()
    )
    atributos = list(
        db.session.execute(
            select(Atributo)
            .where(Atributo.ativo.is_(True))
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
    tipos = list(
        db.session.execute(
            select(TipoPokemon)
            .where(TipoPokemon.ativo.is_(True))
            .order_by(func.lower(TipoPokemon.nome))
        ).scalars()
    )
    return OpcoesItens(categorias=categorias, atributos=atributos, status=status, tipos=tipos)


def resumo_itens() -> dict[str, int]:
    return {
        "itens": int(db.session.scalar(select(func.count(Item.id))) or 0),
        "itens_ativos": int(
            db.session.scalar(select(func.count(Item.id)).where(Item.ativo.is_(True))) or 0
        ),
        "categorias_item": int(
            db.session.scalar(
                select(func.count(CategoriaItem.id)).where(CategoriaItem.ativo.is_(True))
            )
            or 0
        ),
        "itens_inventario": int(db.session.scalar(select(func.count(PersonagemItem.id))) or 0),
        "itens_equipados": int(
            db.session.scalar(
                select(func.count(Pokemon.id)).where(Pokemon.item_equipado_id.is_not(None))
            )
            or 0
        ),
    }


def listar_itens_admin(
    *,
    termo: str = "",
    categoria_id: str = "",
    situacao: str = "ativos",
    origem: str = "todas",
    uso: str = "todos",
    pagina: int = 1,
    por_pagina: int = 36,
) -> PaginaItens:
    consulta = select(Item).options(selectinload(Item.categoria)).outerjoin(CategoriaItem)
    termo = termo.strip()
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.where(
            or_(
                Item.nome.ilike(padrao),
                Item.codigo.ilike(padrao),
                Item.descricao.ilike(padrao),
                cast(Item.efeitos, String).ilike(padrao),
                CategoriaItem.nome.ilike(padrao),
            )
        )
    categoria_uuid = _uuid(categoria_id)
    if categoria_uuid:
        consulta = consulta.where(Item.categoria_id == categoria_uuid)
    if situacao == "ativos":
        consulta = consulta.where(Item.ativo.is_(True))
    elif situacao == "inativos":
        consulta = consulta.where(Item.ativo.is_(False))
    if origem == "personalizados":
        consulta = consulta.where(Item.personalizado.is_(True))
    elif origem == "oficiais":
        consulta = consulta.where(Item.personalizado.is_(False))
    if uso == "consumiveis":
        consulta = consulta.where(Item.consumivel.is_(True))
    elif uso == "equipaveis":
        consulta = consulta.where(Item.equipavel.is_(True))
    elif uso == "batalha":
        consulta = consulta.where(Item.uso_em_batalha.is_(True))

    pagina = max(1, int(pagina or 1))
    subconsulta = consulta.with_only_columns(Item.id).order_by(None).subquery()
    total = int(db.session.scalar(select(func.count()).select_from(subconsulta)) or 0)
    itens = list(
        db.session.execute(
            consulta.order_by(func.lower(Item.nome))
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        ).scalars().unique()
    )
    return PaginaItens(itens=itens, pagina=pagina, por_pagina=por_pagina, total=total)


def carregar_item_admin(item_id: str | uuid.UUID) -> Item | None:
    identificador = _uuid(item_id)
    if not identificador:
        return None
    return db.session.execute(
        select(Item).where(Item.id == identificador).options(selectinload(Item.categoria))
    ).scalar_one_or_none()


def efeitos_item_para_editor(efeitos: Any) -> list[dict[str, Any]]:
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


def _validar_efeitos(valor: str | None) -> tuple[dict[str, Any] | None, list[str]]:
    if not valor or not valor.strip():
        return None, []
    try:
        bruto = json.loads(valor)
    except json.JSONDecodeError:
        return None, ["O editor de efeitos enviou um conteúdo inválido."]
    itens = bruto.get("efeitos", []) if isinstance(bruto, dict) else bruto
    if not isinstance(itens, list):
        return None, ["A estrutura dos efeitos deve conter uma lista."]
    if len(itens) > 20:
        return None, ["Um item pode possuir no máximo 20 efeitos configurados."]

    opcoes = opcoes_itens()
    status_ids = {str(item.id) for item in opcoes.status}
    atributos = {item.codigo for item in opcoes.atributos}
    tipos_ids = {str(item.id) for item in opcoes.tipos}
    tipos_validos = {item[0] for item in TIPOS_EFEITO_ITEM}
    alvos_validos = {item[0] for item in ALVOS_EFEITO_ITEM}
    operacoes_validas = {item[0] for item in OPERACOES_ITEM}
    normalizados: list[dict[str, Any]] = []
    erros: list[str] = []

    for indice, efeito in enumerate(itens, start=1):
        if not isinstance(efeito, dict):
            erros.append(f"Efeito {indice}: conteúdo inválido.")
            continue
        tipo = _texto(efeito.get("tipo"), 60) or "texto"
        alvo = _texto(efeito.get("alvo"), 40) or "pokemon"
        if tipo not in tipos_validos:
            erros.append(f"Efeito {indice}: tipo desconhecido.")
            continue
        if alvo not in alvos_validos:
            erros.append(f"Efeito {indice}: alvo inválido.")
            continue
        normalizado: dict[str, Any] = {"tipo": tipo, "alvo": alvo}
        observacao = _texto(efeito.get("observacao"), 500)
        if observacao:
            normalizado["observacao"] = observacao

        if tipo == "texto":
            texto = _texto(efeito.get("texto"), 4000)
            if not texto:
                erros.append(f"Efeito {indice}: informe a descrição textual.")
            normalizado["texto"] = texto
        elif tipo == "recuperar_pv":
            operacao = _texto(efeito.get("operacao"), 30) or "fixo"
            if operacao not in operacoes_validas:
                erros.append(f"Efeito {indice}: modo de recuperação inválido.")
            normalizado["operacao"] = operacao
            if operacao == "dados":
                expressao = _texto(efeito.get("expressao"), 80)
                if not expressao:
                    erros.append(f"Efeito {indice}: informe a expressão de recuperação.")
                normalizado["expressao"] = expressao
            else:
                valor = _inteiro(efeito.get("valor"), padrao=0)
                if valor <= 0:
                    erros.append(f"Efeito {indice}: a recuperação deve ser maior que zero.")
                normalizado["valor"] = valor
        elif tipo == "remover_status":
            status_id = _texto(efeito.get("status_id"), 80)
            if status_id and status_id not in status_ids:
                erros.append(f"Efeito {indice}: status inexistente ou inativo.")
            normalizado["status_id"] = status_id or None
            normalizado["todos"] = bool(efeito.get("todos"))
        elif tipo == "alterar_atributo":
            atributo = _texto(efeito.get("atributo"), 120)
            operacao = _texto(efeito.get("operacao"), 30) or "fixo"
            if atributo not in atributos:
                erros.append(f"Efeito {indice}: atributo inválido.")
            if operacao not in {"fixo", "percentual"}:
                erros.append(f"Efeito {indice}: operação inválida.")
            normalizado.update(
                atributo=atributo,
                operacao=operacao,
                valor=_inteiro(efeito.get("valor"), padrao=0),
            )
        elif tipo == "causar_dano":
            expressao = _texto(efeito.get("expressao"), 80)
            if not expressao:
                erros.append(f"Efeito {indice}: informe a expressão de dano.")
            normalizado["expressao"] = expressao
        elif tipo == "modificar_calculo":
            chave = _texto(efeito.get("chave"), 160)
            if not chave:
                erros.append(f"Efeito {indice}: informe a chave do cálculo.")
            normalizado.update(
                chave=chave,
                operacao=_texto(efeito.get("operacao"), 30) or "percentual",
                valor=_inteiro(efeito.get("valor"), padrao=0),
                tipo_id=_texto(efeito.get("tipo_id"), 80) or None,
            )
            if normalizado["tipo_id"] and normalizado["tipo_id"] not in tipos_ids:
                erros.append(f"Efeito {indice}: tipo Pokémon inválido.")
        elif tipo in {"evolucao", "mega_evolucao"}:
            normalizado["requisito"] = _texto(efeito.get("requisito"), 1000)

        normalizados.append(normalizado)
    return ({"versao": 1, "efeitos": normalizados} if normalizados else None), erros


def _categoria_do_formulario(formulario: Mapping[str, Any], erros: list[str]) -> uuid.UUID | None:
    categoria_id = _uuid(formulario.get("categoria_id"))
    nova_categoria = _texto(formulario.get("nova_categoria"), 120)
    if nova_categoria:
        codigo = slug(nova_categoria) or f"categoria-{uuid.uuid4().hex[:8]}"
        categoria = db.session.execute(
            select(CategoriaItem).where(
                or_(
                    func.lower(CategoriaItem.codigo) == codigo.lower(),
                    func.lower(CategoriaItem.nome) == nova_categoria.lower(),
                )
            )
        ).scalar_one_or_none()
        if categoria is None:
            categoria = CategoriaItem(codigo=codigo, nome=nova_categoria, ativo=True)
            db.session.add(categoria)
            db.session.flush()
        else:
            categoria.ativo = True
        return categoria.id
    if not categoria_id:
        erros.append("Selecione uma categoria ou informe uma nova.")
        return None
    categoria = db.session.get(CategoriaItem, categoria_id)
    if categoria is None or not categoria.ativo:
        erros.append("A categoria selecionada não existe ou está inativa.")
        return None
    return categoria.id


def _validar_dados(
    formulario: Mapping[str, Any],
    *,
    item: Item | None = None,
) -> tuple[dict[str, Any], list[str]]:
    erros: list[str] = []
    nome = _texto(formulario.get("nome"), 180)
    if not nome:
        erros.append("Informe o nome do item.")
    codigo = slug(_texto(formulario.get("codigo"), 140) or nome)
    if not codigo:
        erros.append("Não foi possível gerar um código para o item.")
    existente = db.session.execute(
        select(Item.id).where(
            func.lower(Item.codigo) == codigo.lower(),
            *([Item.id != item.id] if item else []),
        )
    ).scalar_one_or_none()
    if existente:
        erros.append("Já existe um item com esse código.")

    categoria_id = _categoria_do_formulario(formulario, erros)
    preco = _validar_preco_item(formulario.get("preco"), erros)
    efeitos, erros_efeitos = _validar_efeitos(_texto(formulario.get("efeitos_json"), 50000))
    erros.extend(erros_efeitos)
    return {
        "nome": nome,
        "codigo": codigo,
        "categoria_id": categoria_id,
        "descricao": _texto(formulario.get("descricao"), 6000) or None,
        "imagem_url": _texto(formulario.get("imagem_url"), 500) or None,
        "preco": preco,
        "consumivel": _bool_form(formulario.get("consumivel")),
        "equipavel": _bool_form(formulario.get("equipavel")),
        "uso_em_batalha": _bool_form(formulario.get("uso_em_batalha")),
        "efeitos": efeitos,
        "personalizado": _bool_form(formulario.get("personalizado")),
    }, erros


def criar_item_admin(
    formulario: Mapping[str, Any],
    *,
    usuario_id: str | uuid.UUID | None,
) -> tuple[Item | None, list[str]]:
    dados, erros = _validar_dados(formulario)
    if erros:
        db.session.rollback()
        return None, erros
    item = Item(ativo=True, **dados)
    db.session.add(item)
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="item",
        registro_id=item.id,
        acao="criacao",
        antes=None,
        depois=_snapshot(item),
    )
    db.session.commit()
    return item, []


def atualizar_item_admin(
    item: Item,
    formulario: Mapping[str, Any],
    *,
    usuario_id: str | uuid.UUID | None,
) -> list[str]:
    antes = _snapshot(item)
    dados, erros = _validar_dados(formulario, item=item)
    if erros:
        db.session.rollback()
        return erros
    for chave, valor in dados.items():
        setattr(item, chave, valor)
    db.session.flush()
    depois = _snapshot(item)
    if antes != depois:
        _auditar(
            usuario_id=usuario_id,
            entidade="item",
            registro_id=item.id,
            acao="edicao",
            antes=antes,
            depois=depois,
        )
    db.session.commit()
    return []


def alterar_atividade_item(
    item: Item,
    *,
    ativo: bool,
    usuario_id: str | uuid.UUID | None,
) -> None:
    antes = _snapshot(item)
    item.ativo = ativo
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="item",
        registro_id=item.id,
        acao="reativacao" if ativo else "desativacao",
        antes=antes,
        depois=_snapshot(item),
    )
    db.session.commit()


def duplicar_item_admin(
    item: Item,
    *,
    usuario_id: str | uuid.UUID | None,
) -> Item:
    codigo_base = f"{item.codigo}-copia"
    codigo = codigo_base
    sequencia = 2
    while db.session.execute(
        select(Item.id).where(func.lower(Item.codigo) == codigo.lower())
    ).scalar_one_or_none():
        codigo = f"{codigo_base}-{sequencia}"
        sequencia += 1
    copia = Item(
        codigo=codigo,
        nome=f"{item.nome} (Cópia)",
        categoria_id=item.categoria_id,
        descricao=item.descricao,
        imagem_url=item.imagem_url,
        preco=item.preco,
        consumivel=item.consumivel,
        equipavel=item.equipavel,
        uso_em_batalha=item.uso_em_batalha,
        efeitos=copy.deepcopy(item.efeitos),
        personalizado=True,
        ativo=False,
    )
    db.session.add(copia)
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="item",
        registro_id=copia.id,
        acao="duplicacao",
        antes={"origem_id": str(item.id)},
        depois=_snapshot(copia),
    )
    db.session.commit()
    return copia
