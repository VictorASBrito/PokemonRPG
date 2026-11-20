"""Saneamento 10E.2.1.2 da Pokédex, com plano conferível antes de gravar.

A mudança permitida é somente preencher número nacional NULL de espécies
oficiais e separar a forma nidoran-2 da espécie feminina. Formas
personalizadas, objetos Pokemon e números já preenchidos não são alterados.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from app.extensions import db
from app.models.db import EspeciePokemon, FormaPokemon, HistoricoAlteracao
from app.services.auditoria_pokedex_service import (
    auditar_pokedex,
    construir_referencia_pokedex,
)
from app.services.importacao.utils import codigo_especie_oficial, uuid_legado

CODIGO_NIDORAN_MACHO = "nidoran-m"
CODIGO_FORMA_NIDORAN_MACHO = "nidoran-2"
CONFIRMACAO_SANEAMENTO = "SANEAR-POKEDEX-ANKAR"


@dataclass(frozen=True, slots=True)
class NumeroPendente:
    especie_id: uuid.UUID
    codigo: str
    numero: int


@dataclass(frozen=True, slots=True)
class PlanoSaneamento:
    assinatura: str
    numeros: tuple[NumeroPendente, ...]
    criar_nidoran_macho: bool
    religar_nidoran_macho: bool
    destino_nidoran_macho: uuid.UUID | None
    forma_nidoran_macho: uuid.UUID | None
    formas_extras: tuple[str, ...]
    bloqueios: tuple[str, ...]
    total_formas_fonte: int
    total_especies_fonte: int

    @property
    def operacoes(self) -> int:
        return len(self.numeros) + int(self.criar_nidoran_macho) + int(self.religar_nidoran_macho)


def planejar_saneamento(
    especies: Iterable[EspeciePokemon],
    formas: Iterable[FormaPokemon],
    registros_fonte: Iterable[Mapping[str, Any]],
) -> PlanoSaneamento:
    """Planeja sem fazer INSERT/UPDATE. Bloqueia qualquer surpresa no legado."""
    especies = list(especies)
    formas = list(formas)
    registros_fonte = list(registros_fonte)
    referencia_formas, referencia_especies = construir_referencia_pokedex(registros_fonte)
    bloqueios: list[str] = []
    numeros: list[NumeroPendente] = []

    if len(referencia_formas) != 1064 or len(referencia_especies) != 898:
        bloqueios.append(
            "A fonte original mudou: esperado 1064 formas e 898 especies; revisar antes de sanear."
        )

    por_id = {e.id: e for e in especies}
    por_codigo = {e.codigo: e for e in especies}
    formas_codigo = {f.codigo: f for f in formas}
    macho = por_codigo.get(CODIGO_NIDORAN_MACHO)
    forma_macho = formas_codigo.get(CODIGO_FORMA_NIDORAN_MACHO)
    criar_macho = macho is None
    religar_macho = False
    macho_id = macho.id if macho else uuid_legado("especie", CODIGO_NIDORAN_MACHO)

    if any(e.id == macho_id and e.codigo != CODIGO_NIDORAN_MACHO for e in especies):
        bloqueios.append("UUID reservado para nidoran-m pertence a outra especie.")
    if macho is not None and (macho.nome != "Nidoran♂" or macho.personalizada or not macho.ativo):
        bloqueios.append("nidoran-m existente nao corresponde a especie oficial Nidoran macho.")
    if forma_macho is None:
        bloqueios.append("Forma original nidoran-2 ausente; nada sera inferido.")
    elif forma_macho.nome != "Nidoran♂":
        bloqueios.append("Nome de nidoran-2 difere da origem; exige revisao humana.")

    for codigo, referencia in referencia_formas.items():
        forma = formas_codigo.get(codigo)
        if forma is None:
            bloqueios.append(f"Forma oficial ausente: {codigo}.")
            continue
        if forma.nome != referencia.nome:
            bloqueios.append(f"Nome da forma oficial alterado: {codigo}.")
        configuracoes = forma.configuracoes if isinstance(forma.configuracoes, dict) else {}
        if configuracoes.get("ordem_catalogo") != referencia.ordem:
            bloqueios.append(f"Indice da forma oficial alterado: {codigo}.")
        atual = por_id.get(forma.especie_id)
        if atual is None:
            bloqueios.append(f"Forma oficial sem especie cadastrada: {codigo}.")
            continue
        if codigo == CODIGO_FORMA_NIDORAN_MACHO:
            if atual.id != macho_id:
                if atual.codigo == "nidoran" and atual.nome == "Nidoran♀" and not atual.personalizada:
                    religar_macho = True
                else:
                    bloqueios.append("nidoran-2 tem vinculo inesperado; reparo automatico bloqueado.")
        elif atual.nome != referencia.especie or atual.personalizada or not atual.ativo:
            bloqueios.append(f"Vinculo de especie nao seguro para a forma: {codigo}.")

    # Só alteramos espécies oficiais cujo código coincide com a identidade da fonte.
    # Números já preenchidos, inclusive incorretamente, são preservados e bloqueiam
    # a aplicação, em vez de serem sobrescritos.
    for nome, numero in referencia_especies.items():
        codigo = codigo_especie_oficial(nome)
        especie = por_codigo.get(codigo)
        if especie is None:
            if codigo != CODIGO_NIDORAN_MACHO:
                bloqueios.append(f"Especie oficial ausente: {codigo}.")
            continue
        if especie.nome != nome or especie.personalizada or not especie.ativo:
            bloqueios.append(f"Especie {codigo} nao corresponde a fonte oficial.")
            continue
        if especie.numero is None:
            numeros.append(NumeroPendente(especie.id, codigo, numero))
        elif especie.numero != numero:
            bloqueios.append(
                f"Numero ja preenchido de {codigo} e {especie.numero}, esperado {numero}; "
                "nao sobrescrever cadastro existente."
            )

    # Um mesmo nome-base oficial não deve apontar para dois registros distintos.
    for nome in referencia_especies:
        encontrados = [e for e in especies if e.nome == nome and not e.personalizada]
        if len(encontrados) > 1:
            bloqueios.append(f"Especies oficiais duplicadas: {nome}.")
        if not encontrados and nome != "Nidoran♂":
            bloqueios.append(f"Especie oficial sem nome esperado: {nome}.")

    extras = tuple(sorted(c for c in formas_codigo if c not in referencia_formas))

    # A assinatura cobre os estados importantes do banco e a fonte completa,
    # evitando aplicar um plano já desatualizado.
    estado = {
        "fonte": [
            (r.get("id"), r.get("nome"), r.get("ordem_catalogo"))
            for r in registros_fonte
        ],
        "especies": sorted([
            (str(e.id), e.codigo, e.nome, e.numero, bool(e.personalizada), bool(e.ativo))
            for e in especies
        ]),
        "formas": sorted([
            (
                str(f.id), f.codigo, f.nome, str(f.especie_id), bool(f.ativo),
                (f.configuracoes or {}).get("ordem_catalogo")
                if isinstance(f.configuracoes, dict) else None,
            )
            for f in formas
        ]),
    }
    assinatura = hashlib.sha256(
        json.dumps(estado, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return PlanoSaneamento(
        assinatura=assinatura,
        numeros=tuple(sorted(numeros, key=lambda a: a.numero)),
        criar_nidoran_macho=criar_macho,
        religar_nidoran_macho=religar_macho,
        destino_nidoran_macho=macho_id if (criar_macho or religar_macho) else None,
        forma_nidoran_macho=forma_macho.id if forma_macho is not None else None,
        formas_extras=extras,
        bloqueios=tuple(sorted(set(bloqueios))),
        total_formas_fonte=len(referencia_formas),
        total_especies_fonte=len(referencia_especies),
    )


def aplicar_saneamento(
    plano: PlanoSaneamento,
    especies: Iterable[EspeciePokemon],
    formas: Iterable[FormaPokemon],
    registros_fonte: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    """Aplica uma única transação; chamador deve validar assinatura e backup.

    Não faz commit se surgir qualquer inconsistência ao finalizar.
    """
    if plano.bloqueios:
        raise ValueError("Plano possui bloqueios; nenhuma alteracao permitida.")
    especies = list(especies)
    formas = list(formas)
    registros_fonte = list(registros_fonte)
    por_codigo = {e.codigo: e for e in especies}
    por_forma = {f.codigo: f for f in formas}

    def registrar(entidade: str, identificador: uuid.UUID, acao: str,
                  antes: dict[str, Any] | None, depois: dict[str, Any] | None) -> None:
        db.session.add(HistoricoAlteracao(
            usuario_id=None,
            entidade=entidade,
            registro_id=identificador,
            acao=acao,
            dados_anteriores=antes,
            dados_novos=depois,
        ))

    if plano.criar_nidoran_macho:
        macho = EspeciePokemon(
            id=uuid_legado("especie", CODIGO_NIDORAN_MACHO),
            codigo=CODIGO_NIDORAN_MACHO,
            nome="Nidoran♂",
            numero=32,
            geracao=None,
            personalizada=False,
            ativo=True,
        )
        db.session.add(macho)
        especies.append(macho)
        registrar(
            "especie_pokemon", macho.id, "saneamento_pokedex", None,
            {"codigo": macho.codigo, "nome": macho.nome, "numero": 32},
        )

    if plano.religar_nidoran_macho:
        forma = por_forma[CODIGO_FORMA_NIDORAN_MACHO]
        antes = str(forma.especie_id)
        forma.especie_id = plano.destino_nidoran_macho
        registrar(
            "forma_pokemon", forma.id, "saneamento_pokedex",
            {"especie_id": antes, "codigo": forma.codigo},
            {"especie_id": str(plano.destino_nidoran_macho), "codigo": forma.codigo},
        )

    for ajuste in plano.numeros:
        especie = por_codigo[ajuste.codigo]
        if especie.id != ajuste.especie_id or especie.numero is not None:
            raise ValueError(f"Precondicao falhou para {ajuste.codigo}; rollback necessario.")
        especie.numero = ajuste.numero
        registrar(
            "especie_pokemon", especie.id, "saneamento_pokedex",
            {"codigo": especie.codigo, "numero": None},
            {"codigo": especie.codigo, "numero": ajuste.numero},
        )

    db.session.flush()
    resultado = auditar_pokedex(especies, formas, registros_fonte)
    if resultado.erros or any(a.tipo == "numero_nacional_ausente" for a in resultado.achados):
        raise ValueError(
            "Auditoria posterior encontrou vinculos/numero(s) pendentes; transacao nao deve ser confirmada."
        )

    return {
        "especies_criadas": int(plano.criar_nidoran_macho),
        "vinculos_corrigidos": int(plano.religar_nidoran_macho),
        "numeros_preenchidos": len(plano.numeros),
        "formas_extras_preservadas": len(plano.formas_extras),
    }
