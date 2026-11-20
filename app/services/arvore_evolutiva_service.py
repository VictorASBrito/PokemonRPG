"""Leitura da árvore evolutiva 10E.2.3, sem mutação do catálogo.

Apenas relações ATIVAS de tipo 'evolucao' formam estágios e ramificações.
Megas, alternativas e vínculos regionais aparecem à parte; nenhum deles
concede uma evolução ou mudança de forma em fichas de jogadores.
"""
from __future__ import annotations

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import EvolucaoPokemon, FormaPokemon

MAX_NOS_ARVORE = 120


@dataclass(slots=True)
class LigacaoArvore:
    origem_id: uuid.UUID
    origem_nome: str
    requisito: str


@dataclass(slots=True)
class NoArvore:
    id: uuid.UUID
    codigo: str
    nome: str
    categoria: str
    imagem_url: str | None
    numero: int | None
    selecionado: bool
    predecessores: list[LigacaoArvore] = field(default_factory=list)


@dataclass(slots=True)
class ArvoreEvolutiva:
    camadas: list[list[NoArvore]]
    relacoes_especiais: list[EvolucaoPokemon]
    total_relacoes_permanentes: int
    truncada: bool = False
    ciclo_legado: bool = False

    @property
    def quantidade_formas(self) -> int:
        return sum(len(camada) for camada in self.camadas)


def _evolucao_permanente(relacao: EvolucaoPokemon) -> bool:
    requisitos = relacao.requisitos if isinstance(relacao.requisitos, dict) else {}
    # Registros legados sem tipo_relacao são interpretados com cautela.
    return requisitos.get("tipo_relacao", "evolucao") == "evolucao"


def descrever_requisito(relacao: EvolucaoPokemon) -> str:
    requisitos = relacao.requisitos if isinstance(relacao.requisitos, dict) else {}
    nivel = requisitos.get("nivel")
    item = requisitos.get("item_nome")
    condicao = requisitos.get("condicao")
    partes: list[str] = []
    if relacao.tipo_requisito == "nivel" and nivel is not None:
        partes.append(f"Nível {nivel} do treinador")
    elif relacao.tipo_requisito in {"item", "mega_pedra"} and item:
        partes.append(f"Item: {item}")
    elif relacao.tipo_requisito == "troca":
        partes.append("Troca (revisão do mestre)")
    elif relacao.tipo_requisito == "amizade":
        partes.append("Amizade: requer regra narrativa de Ankar")
    elif relacao.tipo_requisito:
        partes.append(relacao.tipo_requisito.replace("_", " ").capitalize())
    if condicao:
        partes.append(str(condicao)[:180])
    return " · ".join(partes) or "Requisito não documentado"


def montar_arvore_evolutiva(
    selecionada: FormaPokemon,
    *,
    todas_relacoes: list[EvolucaoPokemon] | None = None,
) -> ArvoreEvolutiva:
    """Monta grafo dirigido inteiro da família da forma selecionada.

    Percorre conexões para frente e para trás, incluindo ramificações e
    ancestrais, mas não atravessa Mega/regionais/alternativas para
    fabricar uma árvore evolutiva. Protege contra ciclos legados.
    """
    if todas_relacoes is None:
        todas_relacoes = list(db.session.scalars(
            select(EvolucaoPokemon)
            .where(EvolucaoPokemon.ativo.is_(True))
            .options(
                selectinload(EvolucaoPokemon.forma_origem)
                .selectinload(FormaPokemon.especie),
                selectinload(EvolucaoPokemon.forma_destino)
                .selectinload(FormaPokemon.especie),
            )
        ).all())
    else:
        todas_relacoes = [r for r in todas_relacoes if r.ativo]

    relacoes_evolucao = [r for r in todas_relacoes if _evolucao_permanente(r)]
    vizinhos: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for relacao in relacoes_evolucao:
        o, d = relacao.forma_origem_id, relacao.forma_destino_id
        vizinhos[o].add(d)
        vizinhos[d].add(o)

    familia: set[uuid.UUID] = {selecionada.id}
    fila: deque[uuid.UUID] = deque([selecionada.id])
    truncada = False
    while fila:
        atual = fila.popleft()
        for vizinho in sorted(vizinhos.get(atual, ()), key=str):
            if vizinho in familia:
                continue
            if len(familia) == MAX_NOS_ARVORE:
                truncada = True
                break
            familia.add(vizinho)
            fila.append(vizinho)
        if truncada:
            break

    caminhos = [
        r for r in relacoes_evolucao
        if r.forma_origem_id in familia and r.forma_destino_id in familia
    ]
    especiais = [
        r for r in todas_relacoes
        if not _evolucao_permanente(r)
        and (r.forma_origem_id in familia or r.forma_destino_id in familia)
    ]
    especiais.sort(key=lambda r: (
        r.forma_origem.nome.casefold(), r.forma_destino.nome.casefold(),
        str(r.id),
    ))
    formas: dict[uuid.UUID, FormaPokemon] = {selecionada.id: selecionada}
    for relacao in caminhos + especiais:
        for forma in (relacao.forma_origem, relacao.forma_destino):
            if forma.id in familia:
                formas[forma.id] = forma

    entradas: dict[uuid.UUID, list[EvolucaoPokemon]] = defaultdict(list)
    saidas: dict[uuid.UUID, list[EvolucaoPokemon]] = defaultdict(list)
    graus: dict[uuid.UUID, int] = {identificador: 0 for identificador in familia}
    for r in caminhos:
        entradas[r.forma_destino_id].append(r)
        saidas[r.forma_origem_id].append(r)
        graus[r.forma_destino_id] += 1

    def chave(identificador: uuid.UUID) -> tuple[int, str, str]:
        forma = formas[identificador]
        numero = forma.especie.numero if forma.especie else None
        return (numero if numero is not None else 999999, forma.nome.casefold(), str(identificador))

    # Kahn em camadas: todas as origens no estágio 0; uma forma que
    # converge de dois ramos fica após todos os predecessores.
    remanescentes = graus.copy()
    prontas = sorted((x for x, grau in remanescentes.items() if grau == 0), key=chave)
    estagios: dict[uuid.UUID, int] = {x: 0 for x in prontas}
    processadas: set[uuid.UUID] = set()
    while prontas:
        atual = prontas.pop(0)
        processadas.add(atual)
        for relacao in saidas.get(atual, ()):
            destino = relacao.forma_destino_id
            estagios[destino] = max(estagios.get(destino, 0), estagios[atual] + 1)
            remanescentes[destino] -= 1
            if remanescentes[destino] == 0:
                prontas.append(destino)
        prontas.sort(key=chave)

    ciclo_legado = len(processadas) != len(familia)
    if ciclo_legado:
        # Registros antigos não são corrigidos silenciosamente.
        # Mostrar nós restantes isolados no fim, sem recursão infinita.
        limite = max(estagios.values(), default=-1) + 1
        for identificador in sorted(familia - processadas, key=chave):
            estagios[identificador] = limite

    camadas_por_nivel: dict[int, list[NoArvore]] = defaultdict(list)
    for identificador in familia:
        forma = formas[identificador]
        anteriores = sorted(entradas[identificador], key=lambda r: chave(r.forma_origem_id))
        camadas_por_nivel[estagios[identificador]].append(NoArvore(
            id=identificador,
            codigo=forma.codigo,
            nome=forma.nome,
            categoria=forma.categoria,
            imagem_url=forma.imagem_url,
            numero=forma.especie.numero if forma.especie else None,
            selecionado=identificador == selecionada.id,
            predecessores=[
                LigacaoArvore(
                    origem_id=r.forma_origem_id,
                    origem_nome=r.forma_origem.nome,
                    requisito=descrever_requisito(r),
                )
                for r in anteriores
            ],
        ))
    camadas = [
        sorted(camada, key=lambda no: (
            no.numero if no.numero is not None else 999999,
            no.nome.casefold(),
        ))
        for _, camada in sorted(camadas_por_nivel.items())
    ]
    return ArvoreEvolutiva(
        camadas=camadas,
        relacoes_especiais=especiais,
        total_relacoes_permanentes=len(caminhos),
        truncada=truncada,
        ciclo_legado=ciclo_legado,
    )
