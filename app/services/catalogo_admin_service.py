from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Atributo,
    EspeciePokemon,
    FormaPokemon,
    FormaPokemonAtributo,
    FormaPokemonTipo,
    HistoricoAlteracao,
    Natureza,
    NaturezaModificador,
    TipoPokemon,
)
from app.services.calculo_atributos import aplicar_aumento, aplicar_diminuicao, calcular_progressao
from app.services.importacao.utils import slug
from app.services.pokemon_db_service import carregar_regras_pokemon_db

CATEGORIAS_FORMA = (
    ("normal", "Normal"),
    ("regional", "Regional"),
    ("mega", "Mega Evolução"),
    ("alternativa", "Alternativa"),
    ("personalizada", "Personalizada"),
)


@dataclass(slots=True)
class PaginaFormas:
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
class OpcoesCatalogo:
    atributos: list[Atributo]
    tipos: list[TipoPokemon]
    especies: list[EspeciePokemon]
    naturezas: list[Natureza]
    estilos: list[str]


def _uuid(valor: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError):
        return None


def _decimal(valor: Any, *, padrao: Decimal = Decimal("0")) -> Decimal:
    try:
        texto = str(valor if valor is not None else "").strip().replace(",", ".")
        return Decimal(texto) if texto else padrao
    except (InvalidOperation, ValueError):
        return padrao


def _numero_json(valor: Decimal | int | None) -> int | float | None:
    if valor is None:
        return None
    decimal = Decimal(valor)
    return int(decimal) if decimal == decimal.to_integral_value() else float(decimal)


def _codigo_atributo(codigo: str) -> str:
    return str(codigo or "").strip().replace("-", "_")


def resumo_catalogo() -> dict[str, int]:
    def contar(modelo, *, ativos: bool | None = None) -> int:
        consulta = select(func.count(modelo.id))
        if ativos is not None:
            consulta = consulta.where(modelo.ativo.is_(ativos))
        return int(db.session.scalar(consulta) or 0)

    return {
        "especies": contar(EspeciePokemon),
        "especies_ativas": contar(EspeciePokemon, ativos=True),
        "formas": contar(FormaPokemon),
        "formas_ativas": contar(FormaPokemon, ativos=True),
        "tipos": contar(TipoPokemon, ativos=True),
    }


def listar_formas_admin(
    *,
    termo: str = "",
    categoria: str = "",
    situacao: str = "ativas",
    tipo_id: str = "",
    pagina: int = 1,
    por_pagina: int = 36,
) -> PaginaFormas:
    pagina = max(1, pagina)
    por_pagina = max(12, min(por_pagina, 96))
    consulta = (
        select(FormaPokemon)
        .join(FormaPokemon.especie)
        .options(
            selectinload(FormaPokemon.especie),
            selectinload(FormaPokemon.tipos).selectinload(FormaPokemonTipo.tipo),
            selectinload(FormaPokemon.atributos_base).selectinload(FormaPokemonAtributo.atributo),
        )
    )

    termo = termo.strip()
    if termo:
        padrao = f"%{termo.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(FormaPokemon.nome).like(padrao),
                func.lower(FormaPokemon.codigo).like(padrao),
                func.lower(EspeciePokemon.nome).like(padrao),
            )
        )
    if categoria in {item[0] for item in CATEGORIAS_FORMA}:
        consulta = consulta.where(FormaPokemon.categoria == categoria)
    if situacao == "ativas":
        consulta = consulta.where(FormaPokemon.ativo.is_(True))
    elif situacao == "inativas":
        consulta = consulta.where(FormaPokemon.ativo.is_(False))

    tipo_uuid = _uuid(tipo_id)
    if tipo_uuid:
        consulta = consulta.join(FormaPokemon.tipos).where(FormaPokemonTipo.tipo_id == tipo_uuid)

    subconsulta = consulta.with_only_columns(FormaPokemon.id).order_by(None).subquery()
    total = int(db.session.scalar(select(func.count()).select_from(subconsulta)) or 0)
    itens = list(
        db.session.execute(
            consulta.order_by(
                EspeciePokemon.numero.asc().nullslast(),
                func.lower(EspeciePokemon.nome),
                func.lower(FormaPokemon.nome),
            )
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        ).scalars().unique()
    )
    return PaginaFormas(itens=itens, pagina=pagina, por_pagina=por_pagina, total=total)


def carregar_forma_admin(forma_id: str | uuid.UUID) -> FormaPokemon | None:
    identificador = _uuid(forma_id)
    if not identificador:
        return None
    return db.session.execute(
        select(FormaPokemon)
        .where(FormaPokemon.id == identificador)
        .options(
            selectinload(FormaPokemon.especie),
            selectinload(FormaPokemon.tipos).selectinload(FormaPokemonTipo.tipo),
            selectinload(FormaPokemon.atributos_base).selectinload(FormaPokemonAtributo.atributo),
        )
    ).scalar_one_or_none()


def opcoes_catalogo(campanha_id: str | uuid.UUID | None = None) -> OpcoesCatalogo:
    atributos = list(
        db.session.execute(
            select(Atributo)
            .where(Atributo.ativo.is_(True), Atributo.escopo.in_(["pokemon", "ambos"]))
            .order_by(Atributo.ordem, func.lower(Atributo.nome))
        ).scalars()
    )
    tipos = list(
        db.session.execute(
            select(TipoPokemon).where(TipoPokemon.ativo.is_(True)).order_by(func.lower(TipoPokemon.nome))
        ).scalars()
    )
    especies = list(
        db.session.execute(
            select(EspeciePokemon).where(EspeciePokemon.ativo.is_(True)).order_by(
                EspeciePokemon.numero.asc().nullslast(), func.lower(EspeciePokemon.nome)
            )
        ).scalars()
    )
    naturezas = list(
        db.session.execute(
            select(Natureza)
            .where(Natureza.ativo.is_(True))
            .options(selectinload(Natureza.modificadores).selectinload(NaturezaModificador.atributo))
            .order_by(func.lower(Natureza.nome))
        ).scalars()
    )
    estilos: list[str] = []
    campanha_uuid = _uuid(campanha_id)
    if campanha_uuid:
        estilos = sorted(carregar_regras_pokemon_db(campanha_uuid).get("estilos_combate", {}).keys())
    return OpcoesCatalogo(
        atributos=atributos,
        tipos=tipos,
        especies=especies,
        naturezas=naturezas,
        estilos=estilos,
    )


def _existe_codigo(modelo, codigo: str, *, ignorar_id: uuid.UUID | None = None) -> bool:
    consulta = select(modelo.id).where(func.lower(modelo.codigo) == codigo.lower())
    if ignorar_id:
        consulta = consulta.where(modelo.id != ignorar_id)
    return db.session.execute(consulta).first() is not None


def _snapshot_especie(especie: EspeciePokemon) -> dict[str, Any]:
    return {
        "codigo": especie.codigo,
        "nome": especie.nome,
        "numero": especie.numero,
        "geracao": especie.geracao,
        "descricao": especie.descricao,
        "personalizada": especie.personalizada,
        "ativo": especie.ativo,
    }


def _snapshot_forma(forma: FormaPokemon) -> dict[str, Any]:
    return {
        "especie_id": str(forma.especie_id),
        "codigo": forma.codigo,
        "nome": forma.nome,
        "categoria": forma.categoria,
        "imagem_url": forma.imagem_url,
        "imagem_shiny_url": forma.imagem_shiny_url,
        "ativo": forma.ativo,
        "tipos": [
            {"tipo_id": str(item.tipo_id), "posicao": item.posicao}
            for item in sorted(forma.tipos, key=lambda rel: rel.posicao)
        ],
        "atributos": {
            item.atributo.codigo: _numero_json(item.valor_base)
            for item in forma.atributos_base
        },
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


def _validar_campos_forma(formulario: Mapping[str, Any], *, forma: FormaPokemon | None = None) -> tuple[dict[str, Any], list[str]]:
    erros: list[str] = []
    nome = str(formulario.get("forma_nome", "")).strip()
    codigo = slug(formulario.get("forma_codigo") or nome, padrao="forma")
    categoria = str(formulario.get("categoria", "normal")).strip()
    if not nome:
        erros.append("Informe o nome da forma Pokémon.")
    if categoria not in {item[0] for item in CATEGORIAS_FORMA}:
        erros.append("Selecione uma categoria de forma válida.")
    if _existe_codigo(FormaPokemon, codigo, ignorar_id=forma.id if forma else None):
        erros.append(f'O código de forma "{codigo}" já está em uso.')
    return {
        "nome": nome,
        "codigo": codigo,
        "categoria": categoria,
        "imagem_url": str(formulario.get("imagem_url", "")).strip() or None,
        "imagem_shiny_url": str(formulario.get("imagem_shiny_url", "")).strip() or None,
    }, erros


def _preencher_especie(
    especie: EspeciePokemon,
    formulario: Mapping[str, Any],
    *,
    validar_codigo: bool,
) -> list[str]:
    erros: list[str] = []
    nome = str(formulario.get("especie_nome", "")).strip()
    codigo = slug(formulario.get("especie_codigo") or nome, padrao="especie")
    if not nome:
        erros.append("Informe o nome da espécie.")
    if validar_codigo and _existe_codigo(EspeciePokemon, codigo, ignorar_id=especie.id):
        erros.append(f'O código de espécie "{codigo}" já está em uso.')
    numero_texto = str(formulario.get("numero", "")).strip()
    geracao_texto = str(formulario.get("geracao", "")).strip()
    numero = int(numero_texto) if numero_texto.isdigit() else None
    geracao = int(geracao_texto) if geracao_texto.isdigit() else None
    if numero is not None and numero < 1:
        erros.append("O número da Pokédex deve ser positivo.")
    if geracao is not None and geracao < 1:
        erros.append("A geração deve ser positiva.")
    especie.nome = nome
    especie.codigo = codigo
    especie.numero = numero
    especie.geracao = geracao
    especie.descricao = str(formulario.get("especie_descricao", "")).strip() or None
    especie.personalizada = str(formulario.get("especie_personalizada", "")) == "1"
    return erros


def _sincronizar_tipos(forma: FormaPokemon, formulario: Mapping[str, Any]) -> list[str]:
    erros: list[str] = []
    ids: list[uuid.UUID] = []
    for campo in ("tipo_primario_id", "tipo_secundario_id"):
        valor = _uuid(formulario.get(campo))
        if valor:
            ids.append(valor)
    if not ids:
        erros.append("Selecione pelo menos o tipo primário.")
        return erros
    if len(ids) != len(set(ids)):
        erros.append("O tipo primário e o secundário devem ser diferentes.")
        return erros
    encontrados = {
        item.id: item
        for item in db.session.execute(
            select(TipoPokemon).where(TipoPokemon.id.in_(ids), TipoPokemon.ativo.is_(True))
        ).scalars()
    }
    if len(encontrados) != len(ids):
        erros.append("Um dos tipos selecionados não existe ou está inativo.")
        return erros
    for item in list(forma.tipos):
        db.session.delete(item)
    db.session.flush()
    for posicao, tipo_id in enumerate(ids, start=1):
        db.session.add(FormaPokemonTipo(forma_pokemon=forma, tipo=encontrados[tipo_id], posicao=posicao))
    return erros


def _sincronizar_atributos(forma: FormaPokemon, formulario: Mapping[str, Any]) -> list[str]:
    erros: list[str] = []
    atributos = list(
        db.session.execute(
            select(Atributo)
            .where(Atributo.ativo.is_(True), Atributo.escopo.in_(["pokemon", "ambos"]))
            .order_by(Atributo.ordem)
        ).scalars()
    )
    atuais = {item.atributo_id: item for item in forma.atributos_base}
    for atributo in atributos:
        bruto = formulario.get(f"atributo_{atributo.codigo}")
        valor = _decimal(bruto)
        if valor < 0:
            erros.append(f"{atributo.nome} não pode possuir valor base negativo.")
            continue
        registro = atuais.get(atributo.id)
        if registro is None:
            db.session.add(
                FormaPokemonAtributo(forma_pokemon=forma, atributo=atributo, valor_base=valor)
            )
        else:
            registro.valor_base = valor
    return erros


def criar_forma_admin(
    formulario: Mapping[str, Any],
    *,
    usuario_id: str | uuid.UUID | None,
) -> tuple[FormaPokemon | None, list[str]]:
    forma_dados, erros = _validar_campos_forma(formulario)
    usar_nova_especie = str(formulario.get("nova_especie", "")) == "1"
    especie = None
    if usar_nova_especie:
        especie = EspeciePokemon(codigo="temporario", nome="temporario", personalizada=True, ativo=True)
        db.session.add(especie)
        db.session.flush()
        erros.extend(_preencher_especie(especie, formulario, validar_codigo=True))
    else:
        especie_id = _uuid(formulario.get("especie_id"))
        especie = db.session.get(EspeciePokemon, especie_id) if especie_id else None
        if especie is None or not especie.ativo:
            erros.append("Selecione uma espécie ativa ou marque a criação de uma nova espécie.")

    if erros:
        db.session.rollback()
        return None, erros

    forma = FormaPokemon(especie=especie, ativo=True, **forma_dados)
    db.session.add(forma)
    db.session.flush()
    erros.extend(_sincronizar_tipos(forma, formulario))
    erros.extend(_sincronizar_atributos(forma, formulario))
    if erros:
        db.session.rollback()
        return None, erros

    _auditar(
        usuario_id=usuario_id,
        entidade="forma_pokemon",
        registro_id=forma.id,
        acao="criacao",
        antes=None,
        depois=_snapshot_forma(forma),
    )
    if usar_nova_especie:
        _auditar(
            usuario_id=usuario_id,
            entidade="especie_pokemon",
            registro_id=especie.id,
            acao="criacao",
            antes=None,
            depois=_snapshot_especie(especie),
        )
    db.session.commit()
    return forma, []


def atualizar_forma_admin(
    forma: FormaPokemon,
    formulario: Mapping[str, Any],
    *,
    usuario_id: str | uuid.UUID | None,
) -> list[str]:
    antes_forma = _snapshot_forma(forma)
    antes_especie = _snapshot_especie(forma.especie)
    forma_dados, erros = _validar_campos_forma(formulario, forma=forma)
    erros.extend(_preencher_especie(forma.especie, formulario, validar_codigo=True))
    if erros:
        db.session.rollback()
        return erros
    for chave, valor in forma_dados.items():
        setattr(forma, chave, valor)
    forma.especie.ativo = str(formulario.get("especie_ativa", "1")) == "1"
    erros.extend(_sincronizar_tipos(forma, formulario))
    erros.extend(_sincronizar_atributos(forma, formulario))
    if erros:
        db.session.rollback()
        return erros
    db.session.flush()
    depois_forma = _snapshot_forma(forma)
    depois_especie = _snapshot_especie(forma.especie)
    if antes_forma != depois_forma:
        _auditar(
            usuario_id=usuario_id,
            entidade="forma_pokemon",
            registro_id=forma.id,
            acao="edicao",
            antes=antes_forma,
            depois=depois_forma,
        )
    if antes_especie != depois_especie:
        _auditar(
            usuario_id=usuario_id,
            entidade="especie_pokemon",
            registro_id=forma.especie.id,
            acao="edicao",
            antes=antes_especie,
            depois=depois_especie,
        )
    db.session.commit()
    return []


def alterar_atividade_forma(
    forma: FormaPokemon,
    *,
    ativo: bool,
    usuario_id: str | uuid.UUID | None,
) -> None:
    antes = _snapshot_forma(forma)
    forma.ativo = ativo
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="forma_pokemon",
        registro_id=forma.id,
        acao="reativacao" if ativo else "desativacao",
        antes=antes,
        depois=_snapshot_forma(forma),
    )
    db.session.commit()


def duplicar_forma_admin(
    forma: FormaPokemon,
    *,
    usuario_id: str | uuid.UUID | None,
) -> FormaPokemon:
    codigo_base = f"{forma.codigo}-copia"
    codigo = codigo_base
    sequencia = 2
    while _existe_codigo(FormaPokemon, codigo):
        codigo = f"{codigo_base}-{sequencia}"
        sequencia += 1
    copia = FormaPokemon(
        especie=forma.especie,
        codigo=codigo,
        nome=f"{forma.nome} (Cópia)",
        categoria=forma.categoria,
        imagem_url=forma.imagem_url,
        imagem_shiny_url=forma.imagem_shiny_url,
        configuracoes=forma.configuracoes,
        ativo=False,
    )
    db.session.add(copia)
    db.session.flush()
    for relacao in forma.tipos:
        db.session.add(FormaPokemonTipo(forma_pokemon=copia, tipo_id=relacao.tipo_id, posicao=relacao.posicao))
    for atributo in forma.atributos_base:
        db.session.add(
            FormaPokemonAtributo(
                forma_pokemon=copia,
                atributo_id=atributo.atributo_id,
                valor_base=atributo.valor_base,
            )
        )
    db.session.flush()
    _auditar(
        usuario_id=usuario_id,
        entidade="forma_pokemon",
        registro_id=copia.id,
        acao="duplicacao",
        antes={"origem_id": str(forma.id)},
        depois=_snapshot_forma(copia),
    )
    db.session.commit()
    return copia


def simular_atributos_forma(
    *,
    campanha_id: str | uuid.UUID,
    atributos_base: Mapping[str, Any],
    nivel: int,
    shiny: bool,
    natureza_id: str | None = None,
    estilo: str = "",
) -> dict[str, int]:
    campanha_uuid = _uuid(campanha_id)
    if not campanha_uuid:
        raise ValueError("Campanha inválida para a simulação.")
    regras = carregar_regras_pokemon_db(campanha_uuid)
    nivel = max(1, min(int(nivel or 1), 999))
    bases = {_codigo_atributo(chave): int(_decimal(valor)) for chave, valor in atributos_base.items()}
    bonus_shiny = {
        _codigo_atributo(chave): int(_decimal(valor))
        for chave, valor in (regras.get("bonus_shiny", {}) if shiny else {}).items()
    }
    valores: dict[str, int] = {}
    for codigo, base in bases.items():
        base_com_shiny = base + bonus_shiny.get(codigo, 0)
        faixas = regras.get("progressao_pv", []) if codigo == "pv" else regras.get("progressao_atributos", [])
        valores[codigo] = calcular_progressao(base_com_shiny, nivel, faixas)

    natureza_uuid = _uuid(natureza_id)
    if natureza_uuid:
        natureza = db.session.execute(
            select(Natureza)
            .where(Natureza.id == natureza_uuid, Natureza.ativo.is_(True))
            .options(selectinload(Natureza.modificadores).selectinload(NaturezaModificador.atributo))
        ).scalar_one_or_none()
        if natureza:
            for modificador in natureza.modificadores:
                codigo = _codigo_atributo(modificador.atributo.codigo)
                if codigo not in valores:
                    continue
                numero = float(modificador.valor)
                if modificador.tipo_modificador == "percentual":
                    valores[codigo] = (
                        aplicar_aumento(valores[codigo], numero)
                        if numero >= 0
                        else aplicar_diminuicao(valores[codigo], abs(numero))
                    )
                else:
                    valores[codigo] = max(0, valores[codigo] + int(numero))

    modificadores_estilo = (regras.get("estilos_combate", {}).get(estilo, {}) or {})
    for codigo_bruto, percentual in modificadores_estilo.items():
        codigo = _codigo_atributo(codigo_bruto)
        if codigo in valores:
            valores[codigo] = aplicar_aumento(valores[codigo], float(percentual))
    return valores
