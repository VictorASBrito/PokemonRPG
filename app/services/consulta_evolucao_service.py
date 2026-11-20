"""10E.3.1 — Consulta somente leitura de opções evolutivas de um Pokémon.

A elegibilidade é por INSTÂNCIA: forma de origem, nível compartilhado do
treinador e quantidade na mochila do próprio personagem. Relações
narrativas/condicionais são sempre encaminhadas ao mestre, nunca
desbloqueadas pelo flag de aprovação editorial do catálogo.
Não altera Pokémon, itens, autorizações ou outros registros.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    AutorizacaoEvolucaoPokemon, EvolucaoPokemon, FormaPokemon, Item, Personagem, PersonagemItem, Pokemon,
)

# Itens comuns admitidos como requisito direto. Itens específicos,
# troca, amizade e pedras com condições adicionais ficam restritos.
PEDRAS_COMUNS: dict[str, tuple[str, ...]] = {
    "Pedra da Água": ("water-stone", "pedra-agua", "pedra-de-agua"),
    "Pedra do Fogo": ("fire-stone", "pedra-fogo", "pedra-de-fogo"),
    "Pedra do Trovão": ("thunder-stone", "pedra-trovao", "pedra-de-trovao"),
    "Pedra da Folha": ("leaf-stone", "pedra-folha", "pedra-de-folha"),
    "Pedra da Lua": ("moon-stone", "pedra-lua", "pedra-de-lua"),
    "Pedra do Sol": ("sun-stone", "pedra-sol", "pedra-de-sol"),
    "Pedra Brilhante": ("shiny-stone", "pedra-brilhante"),
    "Pedra do Crepúsculo": ("dusk-stone", "pedra-crepusculo", "pedra-do-crepusculo"),
    "Pedra da Alvorada": ("dawn-stone", "pedra-alvorada", "pedra-da-alvorada"),
    "Pedra do Gelo": ("ice-stone", "pedra-gelo", "pedra-de-gelo"),
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


PEDRAS_ALIAS: dict[str, str] = {}
for _nome_pedra, _codigos in PEDRAS_COMUNS.items():
    for _codigo in (_nome_pedra, *_codigos):
        PEDRAS_ALIAS[_normalizar(_codigo)] = _nome_pedra


@dataclass(frozen=True, slots=True)
class OpcaoEvolucao:
    relacao_id: uuid.UUID
    destino_id: uuid.UUID
    destino_nome: str
    destino_codigo: str
    destino_imagem: str | None
    estado: str  # disponivel, nivel_insuficiente, pedra_ausente, requer_mestre, liberada_mestre
    estado_texto: str
    requisito_texto: str
    orientacao: str
    nivel_necessario: int | None = None
    pedra: str | None = None
    quantidade_pedra: int | None = None


@dataclass(frozen=True, slots=True)
class ConsultaEvolucao:
    pokemon_id: uuid.UUID
    origem_nome: str
    nivel_treinador: int
    opcoes: tuple[OpcaoEvolucao, ...]

    @property
    def possui_evolucoes(self) -> bool:
        return bool(self.opcoes)


def _inventario_pedras(personagem_id: uuid.UUID) -> dict[str, int]:
    """Somente mochila real, sem considerar item equipado ou catálogo."""
    registros = db.session.execute(
        select(Item.codigo, Item.nome, PersonagemItem.quantidade)
        .join(PersonagemItem, PersonagemItem.item_id == Item.id)
        .where(
            PersonagemItem.personagem_id == personagem_id,
            PersonagemItem.quantidade > 0,
            Item.ativo.is_(True),
        )
    ).all()
    saldos: dict[str, int] = {}
    for codigo, nome, quantidade in registros:
        # Código específico do item tem prioridade, quando reconhecido.
        referencia = PEDRAS_ALIAS.get(_normalizar(codigo)) or PEDRAS_ALIAS.get(
            _normalizar(nome)
        )
        if referencia:
            saldos[referencia] = saldos.get(referencia, 0) + int(quantidade)
    return saldos


def _tem_condicoes_especiais(
    relacao: EvolucaoPokemon, requisitos: dict[str, Any]
) -> bool:
    """Falha fechada para metadata desconhecida e cadastros legados."""
    campos_conhecidos = {
        "tipo_relacao", "nivel", "item_nome", "item_codigo_pokeapi",
        "fonte", "fonte_url", "origem_importacao", "requer_liberacao_mestre",
        "liberacao_individual", "liberacao", "aprovado_mestre",
        "detalhes_pokeapi", "gatilho_pokeapi", "condicao",
        "nivel_informativo", "item_especifico_pokeapi",
        "forma_regional_origem", "forma_regional_destino",
    }
    # Cadastros particulares com outros requisitos não podem ser
    # interpretados automaticamente como um nível/pedra simples.
    if set(requisitos) - campos_conhecidos:
        return True
    if any(
        requisitos.get(chave) not in (None, False)
        for chave in ("requer_liberacao_mestre", "liberacao_individual")
    ):
        return True
    if requisitos.get("liberacao") not in (None, "requisito_regular"):
        return True
    if relacao.tipo_requisito in {"amizade", "troca", "especial"}:
        return True
    if relacao.tipo_requisito not in {"nivel", "item"}:
        return True
    if any(requisitos.get(campo) for campo in (
        "condicao", "detalhes_pokeapi", "nivel_informativo",
        "item_especifico_pokeapi",
    )):
        return True
    if relacao.tipo_requisito == "item":
        # Pedra + nível ou qualquer segunda condição não é caminho simples.
        if requisitos.get("nivel") not in (None, ""):
            return True
        nome = requisitos.get("item_nome")
        if not isinstance(nome, str) or _normalizar(nome) not in PEDRAS_ALIAS:
            return True
        codigo = requisitos.get("item_codigo_pokeapi")
        if codigo and PEDRAS_ALIAS.get(_normalizar(str(codigo))) != PEDRAS_ALIAS[_normalizar(nome)]:
            return True
    if relacao.tipo_requisito == "nivel":
        nivel = requisitos.get("nivel")
        if type(nivel) is not int or not 1 <= nivel <= 999:
            return True
        # Um nível isolado com item adicional não é evolução simples.
        if requisitos.get("item_nome") or requisitos.get("item_codigo_pokeapi"):
            return True
    return False


def _texto_condicao(relacao: EvolucaoPokemon, requisitos: dict[str, Any]) -> str:
    partes = []
    descricao = requisitos.get("condicao")
    if descricao:
        partes.append(str(descricao)[:220])
    nivel_informativo = requisitos.get("nivel_informativo")
    if nivel_informativo is not None:
        partes.append(f"Nível informado pela fonte: {nivel_informativo}")
    item = requisitos.get("item_especifico_pokeapi") or requisitos.get("item_nome")
    if item:
        partes.append(f"Item ou material: {item}")
    if not partes:
        gatilho = relacao.tipo_requisito.replace("_", " ")
        partes.append(f"Requisito especial: {gatilho}")
    return " · ".join(partes)


def consultar_evolucoes_pokemon(
    pokemon: Pokemon, personagem: Personagem
) -> ConsultaEvolucao:
    """Calcula opções para Pokémon ativo, de personagem ativo e dono exato.

    A rota também verifica o proprietário pela sessão. Esta camada
    recusa objetos de donos diferentes, reduzindo uso acidental fora
    do escopo correto. 'Disponível' é apenas diagnóstico; nunca POST.
    """
    if pokemon.personagem_id != personagem.id:
        raise ValueError("Pokémon não pertence ao treinador consultado.")
    if not pokemon.ativo or not personagem.ativo:
        raise ValueError("Pokémon ou treinador inativo.")
    nivel_atual = int(personagem.nivel)
    origem = pokemon.forma_pokemon
    if origem is None:
        raise ValueError("Pokémon sem forma cadastrada.")

    relacoes = list(db.session.scalars(
        select(EvolucaoPokemon)
        .where(
            EvolucaoPokemon.forma_origem_id == pokemon.forma_pokemon_id,
            EvolucaoPokemon.ativo.is_(True),
        )
        .options(
            selectinload(EvolucaoPokemon.forma_destino)
            .selectinload(FormaPokemon.especie),
        )
        .order_by(EvolucaoPokemon.tipo_requisito, EvolucaoPokemon.forma_destino_id)
    ).all())
    saldos = _inventario_pedras(personagem.id) if relacoes else {}
    # Autorização não é herança por espécie: relaciona Pokémon, destino
    # e forma de origem; revogações são desconsideradas.
    autorizadas = {
        a.relacao_id for a in db.session.scalars(
            select(AutorizacaoEvolucaoPokemon).where(
                AutorizacaoEvolucaoPokemon.pokemon_id == pokemon.id,
                AutorizacaoEvolucaoPokemon.forma_origem_id == pokemon.forma_pokemon_id,
                AutorizacaoEvolucaoPokemon.ativo.is_(True),
                AutorizacaoEvolucaoPokemon.revogado_em.is_(None),
            )
        ).all()
    } if relacoes else set()
    opcoes: list[OpcaoEvolucao] = []
    for relacao in relacoes:
        requisitos = relacao.requisitos if isinstance(relacao.requisitos, dict) else {}
        if requisitos.get("tipo_relacao", "evolucao") != "evolucao":
            continue
        destino = relacao.forma_destino
        if not destino or not destino.ativo or not destino.especie or not destino.especie.ativo:
            continue
        if _tem_condicoes_especiais(relacao, requisitos):
            liberada = relacao.id in autorizadas
            estado = "liberada_mestre" if liberada else "requer_mestre"
            rotulo = "Liberada pelo mestre" if liberada else "Depende do mestre"
            requisito = _texto_condicao(relacao, requisitos)
            orientacao = (
                "O mestre liberou este destino somente para este Pokémon. "
                "A evolução ainda não foi executada e não consome itens nesta etapa."
                if liberada else
                "Esta evolução requer liberação individual para este Pokémon. "
                "O cadastro da árvore não constitui autorização."
            )
            nivel = None
            pedra = None
            quantidade = None
        elif relacao.tipo_requisito == "nivel":
            nivel = int(requisitos["nivel"])
            pedra = None
            quantidade = None
            requisito = f"Nível {nivel} do treinador"
            if nivel_atual >= nivel:
                estado, rotulo = "disponivel", "Requisito atendido"
                orientacao = "Nível suficiente. A evolução será opcional quando a ação for implementada."
            else:
                estado, rotulo = "nivel_insuficiente", "Nível insuficiente"
                orientacao = f"Faltam {nivel - nivel_atual} nível(is) de treinador."
        else:
            nivel = None
            pedra = PEDRAS_ALIAS[_normalizar(requisitos["item_nome"])]
            quantidade = saldos.get(pedra, 0)
            requisito = f"{pedra} na mochila"
            if quantidade > 0:
                estado, rotulo = "disponivel", "Requisito atendido"
                orientacao = (
                    f"{quantidade} unidade(s) na mochila. Nenhum item foi consumido."
                )
            else:
                estado, rotulo = "pedra_ausente", "Pedra não encontrada"
                orientacao = (
                    "A pedra necessária não foi encontrada no inventário ativo "
                    "deste treinador."
                )
        opcoes.append(OpcaoEvolucao(
            relacao_id=relacao.id,
            destino_id=destino.id,
            destino_nome=destino.nome,
            destino_codigo=destino.codigo,
            destino_imagem=destino.imagem_url,
            estado=estado,
            estado_texto=rotulo,
            requisito_texto=requisito,
            orientacao=orientacao,
            nivel_necessario=nivel,
            pedra=pedra,
            quantidade_pedra=quantidade,
        ))
    # Ordenação estável por situação, depois destino.
    ordem = {"disponivel": 0, "nivel_insuficiente": 1, "pedra_ausente": 2, "liberada_mestre": 3, "requer_mestre": 4}
    opcoes.sort(key=lambda x: (ordem[x.estado], x.destino_nome.casefold(), str(x.relacao_id)))
    return ConsultaEvolucao(
        pokemon_id=pokemon.id,
        origem_nome=origem.nome,
        nivel_treinador=nivel_atual,
        opcoes=tuple(opcoes),
    )
