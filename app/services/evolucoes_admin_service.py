"""Edição administrativa de evolução e parentesco de formas Pokémon.

10E.2.2 NÃO evolui Pokémon de jogadores. O estado persistido é só um
grafo de relações com requisitos e proveniência para revisão do mestre.
"""
from __future__ import annotations

import json
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import EspeciePokemon, EvolucaoPokemon, FormaPokemon, HistoricoAlteracao

TIPOS_RELACAO = (
    ("evolucao", "Evolução permanente"),
    ("mega", "Mega Evolução temporária"),
    ("alternativa", "Mudança de forma reversível"),
    ("regional", "Parentesco regional (sem transformação)"),
)
GATILHOS = (
    ("nivel", "Nível do treinador"),
    ("item", "Uso de item"),
    ("troca", "Troca"),
    ("amizade", "Amizade / revisão manual"),
    ("especial", "Evento ou condição especial"),
    ("mega_pedra", "Mega Pedra e Pedra Chave"),
    ("condicao", "Condição de forma"),
    ("linhagem", "Parentesco regional"),
)
GATILHOS_POR_RELACAO = {
    "evolucao": frozenset(("nivel", "item", "troca", "amizade", "especial")),
    "mega": frozenset(("mega_pedra", "especial")),
    "alternativa": frozenset(("condicao",)),
    "regional": frozenset(("linhagem",)),
}
FONTES = (
    ("mestre", "Regra própria de Ankar"),
    ("livro", "Manual Pokémon RPG 2.5"),
    ("pokeapi", "PokéAPI"),
    ("pokemondb", "Pokémon Database"),
    ("combinada", "Fontes cruzadas"),
)


def _uuid(valor: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError):
        return None


def _snapshot(relacao: EvolucaoPokemon) -> dict[str, Any]:
    return {
        "origem_id": str(relacao.forma_origem_id),
        "destino_id": str(relacao.forma_destino_id),
        "tipo_requisito": relacao.tipo_requisito,
        "requisitos": dict(relacao.requisitos or {}),
        "observacoes": relacao.observacoes,
        "ativo": relacao.ativo,
    }


def _auditar(
    relacao: EvolucaoPokemon,
    acao: str,
    antes: dict[str, Any] | None,
    *,
    usuario_id: str | uuid.UUID | None,
) -> None:
    db.session.add(HistoricoAlteracao(
        usuario_id=_uuid(usuario_id),
        entidade="evolucao_pokemon",
        registro_id=relacao.id,
        acao=acao,
        dados_anteriores=antes,
        dados_novos=_snapshot(relacao),
    ))


def listar_relacoes(forma_id: uuid.UUID) -> tuple[list[EvolucaoPokemon], list[EvolucaoPokemon]]:
    opcoes = (
        selectinload(EvolucaoPokemon.forma_origem).selectinload(FormaPokemon.especie),
        selectinload(EvolucaoPokemon.forma_destino).selectinload(FormaPokemon.especie),
    )
    consulta = select(EvolucaoPokemon).options(*opcoes)
    saida = list(db.session.scalars(
        consulta.where(EvolucaoPokemon.forma_origem_id == forma_id)
        .order_by(EvolucaoPokemon.ativo.desc(), EvolucaoPokemon.tipo_requisito)
    ).all())
    entrada = list(db.session.scalars(
        consulta.where(EvolucaoPokemon.forma_destino_id == forma_id)
        .order_by(EvolucaoPokemon.ativo.desc(), EvolucaoPokemon.tipo_requisito)
    ).all())
    return saida, entrada


def buscar_formas_relacao(termo: str, *, excluir_id: uuid.UUID, limite: int = 35) -> list[FormaPokemon]:
    termo = termo.strip()[:100]
    if len(termo) < 2:
        return []
    padrao = f"%{termo}%"
    return list(db.session.scalars(
        select(FormaPokemon)
        .join(FormaPokemon.especie)
        .options(selectinload(FormaPokemon.especie))
        .where(
            FormaPokemon.ativo.is_(True),
            EspeciePokemon.ativo.is_(True),
            FormaPokemon.id != excluir_id,
            or_(
                FormaPokemon.nome.ilike(padrao),
                FormaPokemon.codigo.ilike(padrao),
                EspeciePokemon.nome.ilike(padrao),
            ),
        )
        .order_by(func.lower(FormaPokemon.nome))
        .limit(limite)
    ).all())


def _forma_valida(forma: FormaPokemon | None) -> bool:
    return bool(forma is not None and forma.ativo and forma.especie and forma.especie.ativo)


def _cria_ciclo(origem: uuid.UUID, destino: uuid.UUID, *, ignorar_id: uuid.UUID | None) -> bool:
    """Grafo acíclico SOMENTE para evoluções permanentes."""
    arestas = db.session.execute(
        select(EvolucaoPokemon.id, EvolucaoPokemon.forma_origem_id,
               EvolucaoPokemon.forma_destino_id, EvolucaoPokemon.requisitos,
               EvolucaoPokemon.tipo_requisito)
        .where(EvolucaoPokemon.ativo.is_(True))
    ).all()
    adjacencias: dict[uuid.UUID, set[uuid.UUID]] = {}
    for identificador, de, para, requisitos, gatilho in arestas:
        if identificador == ignorar_id:
            continue
        # Legado sem tipo_relacao deve ser tratado conservadoramente
        # como evolução permanente, não como transformação.
        if (requisitos or {}).get("tipo_relacao", "evolucao") != "evolucao":
            continue
        adjacencias.setdefault(de, set()).add(para)

    visitados: set[uuid.UUID] = set()
    fila = [destino]
    while fila:
        atual = fila.pop()
        if atual == origem:
            return True
        if atual in visitados:
            continue
        visitados.add(atual)
        fila.extend(adjacencias.get(atual, set()) - visitados)
    return False


def _validar_url(url: str) -> bool:
    if not url:
        return True
    partes = urlsplit(url)
    return partes.scheme == "https" and bool(partes.hostname) and not partes.username and not partes.password


def salvar_relacao(
    origem: FormaPokemon,
    formulario: Mapping[str, Any],
    *,
    usuario_id: str | uuid.UUID | None,
) -> tuple[EvolucaoPokemon | None, list[str]]:
    """Salva uma aresta com validação; não muda Pokemon.forma_pokemon_id."""
    erros: list[str] = []
    relacao_id = _uuid(formulario.get("relacao_id"))
    destino_id = _uuid(formulario.get("destino_id"))
    existente = db.session.get(EvolucaoPokemon, relacao_id) if relacao_id else None
    destino = db.session.get(FormaPokemon, destino_id) if destino_id else None
    if formulario.get("relacao_id") and existente is None:
        erros.append("Relação a editar não foi encontrada.")
    if existente is not None and existente.forma_origem_id != origem.id:
        erros.append("A relação não pertence à forma selecionada.")
    if not _forma_valida(origem) or not _forma_valida(destino):
        erros.append("Origem e destino devem ser formas ativas de espécies ativas.")
    if destino_id == origem.id:
        erros.append("Uma forma não pode se relacionar consigo mesma.")

    tipo = str(formulario.get("tipo_relacao", "evolucao")).strip()
    gatilho = str(formulario.get("tipo_requisito", "")).strip()
    if gatilho not in GATILHOS_POR_RELACAO.get(tipo, frozenset()):
        erros.append("O requisito escolhido não é compatível com o tipo de relação.")

    nivel: int | None = None
    texto_nivel = str(formulario.get("nivel", "")).strip()
    if texto_nivel:
        try:
            nivel = int(texto_nivel)
            if not 1 <= nivel <= 999:
                raise ValueError
        except (ValueError, TypeError):
            erros.append("O nível deve ser um inteiro entre 1 e 999.")
    if gatilho == "nivel" and nivel is None:
        erros.append("Informe o nível exigido para evolução.")

    item = str(formulario.get("item_nome", "")).strip()[:140]
    condicao = str(formulario.get("condicao", "")).strip()[:500]
    if gatilho in {"item", "mega_pedra"} and not item:
        erros.append("Informe o item ou a Mega Pedra exigidos.")
    # A permissão Mega é uma regra do TREINADOR já validada no serviço
    # de transformação. Relações Mega com gatilho "especial" não exigem
    # texto adicional, Pedra Chave, Mega Pedra ou item no inventário.
    mega_por_permissao = tipo == "mega" and gatilho == "especial"
    if gatilho in {"especial", "condicao", "linhagem", "amizade", "troca"} and not condicao and not mega_por_permissao:
        erros.append("Descreva a condição ou autorização narrativa necessária.")

    fonte = str(formulario.get("fonte", "mestre")).strip()
    if fonte not in {chave for chave, _ in FONTES}:
        erros.append("Fonte de consulta desconhecida.")
    url = str(formulario.get("fonte_url", "")).strip()[:500]
    if not _validar_url(url):
        erros.append("A referência deve ser uma URL HTTPS válida.")
    observacoes = str(formulario.get("observacoes", "")).strip()[:1500]

    if destino is not None and origem is not None:
        if tipo == "mega" and (destino.categoria != "mega" or origem.categoria == "mega"
                              or destino.especie_id != origem.especie_id):
            erros.append("Mega Evolução precisa conectar forma base à Mega da mesma espécie.")
        elif tipo == "alternativa" and (
            destino.especie_id != origem.especie_id or destino.categoria != "alternativa"
        ):
            erros.append("Forma alternativa deve pertencer à mesma espécie e ter categoria alternativa.")
        elif tipo == "regional" and (
            destino.especie_id != origem.especie_id or destino.categoria != "regional"
        ):
            erros.append("Parentesco regional exige variante regional da mesma espécie.")
        elif tipo == "evolucao" and (
            origem.categoria == "mega" or destino.categoria == "mega"
        ):
            erros.append("Mega Evoluções não podem ser cadastradas como evoluções permanentes.")

        if existente is None:
            duplicada = db.session.scalar(
                select(EvolucaoPokemon.id).where(
                    EvolucaoPokemon.forma_origem_id == origem.id,
                    EvolucaoPokemon.forma_destino_id == destino.id,
                )
            )
            if duplicada:
                erros.append("Já existe uma relação entre estas formas; edite a existente.")
        elif existente.forma_destino_id != destino.id:
            duplicada = db.session.scalar(
                select(EvolucaoPokemon.id).where(
                    EvolucaoPokemon.forma_origem_id == origem.id,
                    EvolucaoPokemon.forma_destino_id == destino.id,
                    EvolucaoPokemon.id != existente.id,
                )
            )
            if duplicada:
                erros.append("Já existe outra relação para esse destino.")
        if tipo == "evolucao" and _cria_ciclo(
            origem.id, destino.id, ignorar_id=existente.id if existente else None
        ):
            erros.append("A relação criaria um ciclo de evoluções permanentes.")

    if erros:
        return None, erros

    if existente is None:
        relacao = EvolucaoPokemon(
            forma_origem_id=origem.id, forma_destino_id=destino.id,
            tipo_requisito=gatilho, requisitos={},
        )
        db.session.add(relacao)
        db.session.flush()
        antes = None
        acao = "criar_relacao"
    else:
        relacao = existente
        antes = _snapshot(relacao)
        acao = "editar_relacao"
    relacao.forma_destino_id = destino.id
    relacao.tipo_requisito = gatilho
    requisitos_preservados = {}
    if existente is not None:
        # Editar metadados não deve retirar proteção individual do mestre
        # das relações especiais importadas de forma controlada.
        for chave in (
            "origem_importacao", "requer_liberacao_mestre",
            "liberacao_individual", "liberacao",
            "detalhes_pokeapi", "gatilho_pokeapi",
            "item_codigo_pokeapi",
        ):
            if chave in (existente.requisitos or {}):
                requisitos_preservados[chave] = existente.requisitos[chave]
    relacao.requisitos = {
        **requisitos_preservados,
        "tipo_relacao": tipo,
        "nivel": nivel,
        "item_nome": item or None,
        "condicao": condicao or None,
        "fonte": fonte,
        "fonte_url": url or None,
        "aprovado_mestre": True,
        # Apenas dados declarativos; nunca implicam elegibilidade automática.
    }
    relacao.observacoes = observacoes or None
    relacao.ativo = True
    _auditar(relacao, acao, antes, usuario_id=usuario_id)
    db.session.commit()
    return relacao, []


def desativar_relacao(
    origem: FormaPokemon,
    relacao_id: str,
    *,
    usuario_id: str | uuid.UUID | None,
) -> bool:
    identificador = _uuid(relacao_id)
    relacao = db.session.get(EvolucaoPokemon, identificador) if identificador else None
    if relacao is None or relacao.forma_origem_id != origem.id or not relacao.ativo:
        return False
    antes = _snapshot(relacao)
    relacao.ativo = False
    _auditar(relacao, "desativar_relacao", antes, usuario_id=usuario_id)
    db.session.commit()
    return True


@lru_cache(maxsize=1)
def _referencias_verificadas() -> tuple[dict[str, Any], ...]:
    caminho = (
        Path(__file__).resolve().parents[2]
        / "data" / "referencias" / "evolucoes_verificadas_10e2.json"
    )
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return tuple(dados["relacoes"])


@lru_cache(maxsize=1)
def _referencias_revisadas_10e2_3() -> tuple[dict[str, Any], ...]:
    """Expansão editorial local: não consulta internet nem altera catálogo."""
    caminho = (
        Path(__file__).resolve().parents[2]
        / "data" / "referencias" / "evolucoes_revisadas_10e2_3.json"
    )
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    propostas = dados.get("relacoes")
    if not isinstance(propostas, list):
        raise ValueError("Fonte de revisões evolutivas sem lista de relações.")
    chaves: set[tuple[str, str]] = set()
    for proposta in propostas:
        if not isinstance(proposta, dict):
            raise ValueError("Referência evolutiva inválida.")
        chave = (proposta.get("origem"), proposta.get("destino"))
        if not all(isinstance(valor, str) and valor for valor in chave):
            raise ValueError("Referência evolutiva sem origem ou destino.")
        if chave in chaves:
            raise ValueError("Duas propostas foram cadastradas para a mesma evolução.")
        if proposta.get("status") not in {"aprovavel", "pendente_decisao"}:
            raise ValueError("Referência com status de revisão desconhecido.")
        chaves.add(chave)
    return tuple(propostas)


def _todas_sugestoes() -> tuple[dict[str, Any], ...]:
    originais = [dict(item, status="aprovavel", tipo_requisito="nivel")
                 for item in _referencias_verificadas()]
    extras = list(_referencias_revisadas_10e2_3())
    chaves = [(p["origem"], p["destino"]) for p in originais + extras]
    if len(chaves) != len(set(chaves)):
        raise ValueError("Evoluções duplicadas nas fontes editoriais.")
    return tuple(originais + extras)


def sugestoes_verificadas(forma: FormaPokemon) -> list[dict[str, Any]]:
    """Fonte editorial local, auditada fora do sistema; sem requisição externa."""
    existentes = {
        r.forma_destino.codigo
        for r in db.session.scalars(
            select(EvolucaoPokemon)
            .where(EvolucaoPokemon.forma_origem_id == forma.id)
            .options(selectinload(EvolucaoPokemon.forma_destino))
        )
    }
    return [
        dict(item)
        for item in _todas_sugestoes()
        if item["origem"] == forma.codigo and item["destino"] not in existentes
    ]


def cadastrar_sugestao(
    origem: FormaPokemon,
    destino_codigo: str,
    *,
    usuario_id: str | uuid.UUID | None,
) -> tuple[EvolucaoPokemon | None, list[str]]:
    """Aprovação individual; propostas conflitantes NUNCA cadastram por POST."""
    proposta = next(
        (item for item in _todas_sugestoes()
         if item["origem"] == origem.codigo and item["destino"] == destino_codigo),
        None,
    )
    if not proposta:
        return None, ["A evolução solicitada não está nas referências revisadas."]
    if proposta.get("status") != "aprovavel":
        return None, [
            "Esta evolução depende de decisão narrativa do mestre. "
            "Revise o livro e as fontes e cadastre uma regra manual na pesquisa."
        ]
    destino = db.session.scalar(
        select(FormaPokemon).where(FormaPokemon.codigo == destino_codigo)
    )
    if destino is None:
        return None, ["A forma de destino ainda não existe no catálogo."]
    tipo_requisito = proposta.get("tipo_requisito", "nivel")
    observacoes = [
        "Sugestão revisada: PokéAPI, Pokémon Database e livro PKMRPG v2.5.",
        proposta.get("criterio", ""),
        proposta.get("alerta_ankar", ""),
        proposta.get("livro", ""),
        "Regras de Ankar prevalecem; aprovação não concede evolução automática.",
    ]
    return salvar_relacao(origem, {
        "destino_id": str(destino.id),
        "tipo_relacao": "evolucao",
        "tipo_requisito": tipo_requisito,
        "nivel": str(proposta["nivel"]) if tipo_requisito == "nivel" else "",
        "item_nome": proposta.get("item_nome") or "",
        "fonte": "combinada",
        "fonte_url": proposta["pokeapi"],
        "observacoes": " ".join(p for p in observacoes if p),
    }, usuario_id=usuario_id)
