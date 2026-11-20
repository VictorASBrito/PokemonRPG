"""Carga segura das relações evolutivas oficiais de Ankar (10E.2.4).

A fonte PokeAPI é versionada no repositório: nenhuma chamada externa
durante execução. Simulação é somente SELECT; aplicação é aditiva,
idempotente e transacional, sem modificar relações existentes ou Pokémon
dos jogadores. Condições especiais sempre exigem liberação INDIVIDUAL
pelo mestre na etapa de evolução de Pokémon de jogadores.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import EvolucaoPokemon, FormaPokemon, HistoricoAlteracao

FRASE_CONFIRMACAO = "GERAR-ARVORES-ANKAR"
ARQUIVO_FONTE = (
    Path(__file__).resolve().parents[2]
    / "data" / "referencias" / "pokedex_evolucoes_898_10e2_4.json"
)


@lru_cache(maxsize=1)
def carregar_base_evolutiva() -> dict[str, Any]:
    dados = json.loads(ARQUIVO_FONTE.read_text(encoding="utf-8"))
    registros = dados.get("relacoes")
    if dados.get("numero_maximo") != 898 or len(registros or []) != 430:
        raise ValueError("Base evolutiva inesperada: exigir versão oficial de 898 espécies e 430 relações.")
    pares = [(r["origem"], r["destino"]) for r in registros]
    if len(set(pares)) != len(pares):
        raise ValueError("Fonte evolutiva contém pares repetidos.")
    contagem = Counter(r.get("classe") for r in registros)
    if contagem != {"automatica": 340, "mestre": 90}:
        raise ValueError("Classificações automáticas/manuais divergentes da fonte revisada.")
    for r in registros:
        if not isinstance(r.get("origem"), str) or not isinstance(r.get("destino"), str):
            raise ValueError("Referência evolutiva sem códigos.")
        automatico = r["classe"] == "automatica"
        metodo = r.get("metodo")
        if automatico and (
            r.get("requer_liberacao_mestre") is not False
            or metodo not in {"nivel", "pedra"}
            or (metodo == "nivel" and (type(r.get("nivel")) is not int or r["nivel"] < 1))
            or (metodo == "pedra" and not r.get("pedra_codigo"))
        ):
            raise ValueError(f"Relação automática incompleta: {r['destino']}.")
        if not automatico and r.get("requer_liberacao_mestre") is not True:
            raise ValueError(f"Relação especial sem proteção de mestre: {r['destino']}.")
    for codigo in ("espeon", "umbreon", "sylveon"):
        row = next((r for r in registros if r["destino"] == codigo), None)
        if row is None or row["classe"] != "mestre":
            raise ValueError("Evolução especial de Eevee não pode ser liberada automaticamente.")
    return dados


@dataclass(frozen=True, slots=True)
class VinculoPendente:
    origem_id: uuid.UUID
    destino_id: uuid.UUID
    registro: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PlanoImportacaoEvolucoes:
    assinatura: str
    pendentes: tuple[VinculoPendente, ...]
    ja_existentes: int
    bloqueios: tuple[str, ...]
    auto_fonte: int
    mestre_fonte: int

    @property
    def automaticas_pendentes(self) -> int:
        return sum(x.registro["classe"] == "automatica" for x in self.pendentes)

    @property
    def mestre_pendentes(self) -> int:
        return sum(x.registro["classe"] == "mestre" for x in self.pendentes)


def _alcancavel(destino: uuid.UUID, origem: uuid.UUID, adj: dict[uuid.UUID, set[uuid.UUID]]) -> bool:
    vistos: set[uuid.UUID] = set()
    pendentes = [destino]
    while pendentes:
        atual = pendentes.pop()
        if atual == origem:
            return True
        if atual in vistos:
            continue
        vistos.add(atual)
        pendentes.extend(adj.get(atual, set()) - vistos)
    return False


def planejar_importacao_evolucoes(
    formas: Iterable[FormaPokemon],
    relacoes: Iterable[EvolucaoPokemon],
    fonte: Iterable[Mapping[str, Any]],
) -> PlanoImportacaoEvolucoes:
    """Sem mutação: preserva relações manuais e bloqueia sobrescritas e ciclos."""
    formas = list(formas)
    relacoes = list(relacoes)
    fonte = list(fonte)
    indices = {f.codigo: f for f in formas}
    ids = {f.id: f for f in formas}
    existentes = {(r.forma_origem_id, r.forma_destino_id) for r in relacoes}
    adj: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for relacao in relacoes:
        requisitos = relacao.requisitos or {}
        if relacao.ativo and requisitos.get("tipo_relacao", "evolucao") == "evolucao":
            adj[relacao.forma_origem_id].add(relacao.forma_destino_id)

    bloqueios: list[str] = []
    adicionadas: list[VinculoPendente] = []
    puladas = 0
    vistos: set[tuple[str, str]] = set()
    for r in fonte:
        origem_codigo, destino_codigo = r["origem"], r["destino"]
        codigo_par = (origem_codigo, destino_codigo)
        if codigo_par in vistos:
            bloqueios.append(f"Duplicidade na fonte: {origem_codigo} → {destino_codigo}.")
            continue
        vistos.add(codigo_par)
        origem, destino = indices.get(origem_codigo), indices.get(destino_codigo)
        if origem is None or destino is None:
            bloqueios.append(f"Forma ausente: {origem_codigo} → {destino_codigo}.")
            continue
        if origem.id == destino.id:
            bloqueios.append(f"Origem igual ao destino: {origem_codigo}.")
            continue
        for f, numero in ((origem, r["origem_numero"]), (destino, r["destino_numero"])):
            if f.especie and f.especie.numero is not None and f.especie.numero != numero:
                bloqueios.append(f"Número nacional inesperado: {f.codigo}.")
            if not f.ativo or (f.especie and not f.especie.ativo):
                bloqueios.append(f"Forma ou espécie inativa: {f.codigo}.")
        ids_par = (origem.id, destino.id)
        if ids_par in existentes:
            puladas += 1
            continue  # Não reativar nem alterar vínculos manuais/desativados.
        if _alcancavel(destino.id, origem.id, adj):
            bloqueios.append(f"Possível ciclo evolutivo: {origem_codigo} → {destino_codigo}.")
            continue
        adicionadas.append(VinculoPendente(origem.id, destino.id, r))
        adj[origem.id].add(destino.id)

    estado = {
        "fonte": fonte,
        "formas": sorted(
            (str(f.id), f.codigo, str(f.especie_id), bool(f.ativo),
             f.especie.numero if f.especie else None,
             bool(f.especie.ativo) if f.especie else False)
            for f in formas
        ),
        "relacoes": sorted(
            (str(r.id), str(r.forma_origem_id), str(r.forma_destino_id),
             r.tipo_requisito, bool(r.ativo),
             json.dumps(r.requisitos, sort_keys=True, ensure_ascii=True))
            for r in relacoes
        ),
    }
    assinatura = hashlib.sha256(
        json.dumps(estado, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()

    categorias = Counter(r["classe"] for r in fonte)
    return PlanoImportacaoEvolucoes(
        assinatura=assinatura,
        pendentes=tuple(adicionadas),
        ja_existentes=puladas,
        bloqueios=tuple(sorted(set(bloqueios))),
        auto_fonte=categorias["automatica"],
        mestre_fonte=categorias["mestre"],
    )


def consultar_plano_evolucoes(*, bloquear: bool = False) -> PlanoImportacaoEvolucoes:
    fonte = carregar_base_evolutiva()["relacoes"]
    consulta_formas = select(FormaPokemon).options(selectinload(FormaPokemon.especie))
    consulta_vinculos = select(EvolucaoPokemon)
    if bloquear:
        consulta_formas = consulta_formas.with_for_update(of=FormaPokemon)
        consulta_vinculos = consulta_vinculos.with_for_update()
    with db.session.no_autoflush:
        formas = list(db.session.scalars(consulta_formas).all())
        vinculos = list(db.session.scalars(consulta_vinculos).all())
        return planejar_importacao_evolucoes(formas, vinculos, fonte)


def aplicar_plano_evolucoes(
    plano: PlanoImportacaoEvolucoes, *, usuario_id: uuid.UUID | None = None
) -> dict[str, int]:
    """Responsabilidade do chamador: validar assinatura/backup e COMMIT ou rollback."""
    if plano.bloqueios:
        raise ValueError("Plano possui bloqueios; não aplicar alterações.")
    for pendente in plano.pendentes:
        r = pendente.registro
        simples = r["classe"] == "automatica"
        gatilho = "nivel" if r["metodo"] == "nivel" else ("item" if r["metodo"] == "pedra" else "especial")
        requisitos: dict[str, Any] = {
            "tipo_relacao": "evolucao",
            "nivel": r.get("nivel") if gatilho == "nivel" else None,
            "item_nome": r.get("pedra") if gatilho == "item" else None,
            "item_codigo_pokeapi": r.get("pedra_codigo"),
            "fonte": "pokeapi",
            "fonte_url": r.get("fonte_url"),
            "origem_importacao": "10E.2.4",
            "requer_liberacao_mestre": not simples,
            "liberacao_individual": not simples,
            "liberacao": "mestre_por_pokemon" if not simples else "requisito_regular",
            "aprovado_mestre": False,
            "detalhes_pokeapi": r.get("condicoes_api", {}),
            "gatilho_pokeapi": r.get("gatilho_api"),
        }
        # 'aprovado_mestre' false aqui significa "nenhuma autorização
        # individual registrada"; não significa falta de revisão da fonte.
        observacao = (
            "Evolução especial: aprovação individual do mestre obrigatória. "
            "Não liberar por amizade, troca ou outros itens automaticamente."
            if not simples else
            "Evolução padrão por nível ou pedra. Não evoluir a instância "
            "sem escolha do treinador e validação da condição."
        )
        relacao = EvolucaoPokemon(
            id=uuid.uuid4(),
            forma_origem_id=pendente.origem_id,
            forma_destino_id=pendente.destino_id,
            tipo_requisito=gatilho,
            requisitos=requisitos,
            observacoes=observacao,
            ativo=True,
        )
        db.session.add(relacao)
        db.session.add(HistoricoAlteracao(
            usuario_id=usuario_id,
            entidade="evolucao_pokemon",
            registro_id=relacao.id,
            acao="importacao_catalogo_evolucoes",
            dados_anteriores=None,
            dados_novos={
                "forma_origem_id": str(relacao.forma_origem_id),
                "forma_destino_id": str(relacao.forma_destino_id),
                "tipo_requisito": gatilho,
                "requer_liberacao_mestre": not simples,
                "fonte": "10E.2.4",
            },
        ))
    db.session.flush()
    return {
        "criadas": len(plano.pendentes),
        "automatica": plano.automaticas_pendentes,
        "mestre": plano.mestre_pendentes,
        "preservadas": plano.ja_existentes,
    }


def verificar_liberacao_individual(
    relacao: EvolucaoPokemon, *, autorizada_pelo_mestre: bool
) -> bool:
    """Guarda obrigatória para futura etapa 10E.3; não evolui Pokémon.

    Parâmetro de autorização deverá vir de um registro transacional
    associado ao Pokémon e ao mestre, NUNCA diretamente do cliente.
    """
    req = relacao.requisitos if isinstance(relacao.requisitos, dict) else {}
    if not relacao.ativo or req.get("tipo_relacao", "evolucao") != "evolucao":
        return False
    if req.get("requer_liberacao_mestre", False):
        return bool(autorizada_pelo_mestre)
    return True
