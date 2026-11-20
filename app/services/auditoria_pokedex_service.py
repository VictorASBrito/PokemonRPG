"""Auditoria 10E.2.1, estritamente de leitura, da Pokédex de Ankar.

A origem tem 1.064 formas em ordem_catalogo e 898 espécies nacionais.
Nunca usar ordem_catalogo como número nacional ou normalizar os símbolos
♀/♂ pelo slug legado, que produz uma colisão entre as duas espécies.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.services.importacao.utils import nome_especie


@dataclass(frozen=True, slots=True)
class ReferenciaForma:
    codigo: str
    nome: str
    especie: str
    numero: int
    ordem: int


@dataclass(frozen=True, slots=True)
class AchadoPokedex:
    nivel: str
    tipo: str
    codigo: str
    mensagem: str
    pokemons_ativos: int = 0


@dataclass(slots=True)
class ResultadoAuditoriaPokedex:
    formas_fonte: int
    especies_fonte: int
    formas_banco: int
    especies_banco: int
    formas_oficiais_presentes: int
    especies_personalizadas: int
    achados: list[AchadoPokedex]

    @property
    def erros(self) -> int:
        return sum(achado.nivel == "erro" for achado in self.achados)

    @property
    def avisos(self) -> int:
        return sum(achado.nivel == "aviso" for achado in self.achados)

    @property
    def tipos(self) -> dict[str, int]:
        return dict(sorted(Counter(achado.tipo for achado in self.achados).items()))

    def para_dict(self) -> dict[str, Any]:
        return {
            "modo": "somente_leitura",
            "fonte": {
                "formas": self.formas_fonte,
                "especies": self.especies_fonte,
            },
            "banco": {
                "formas": self.formas_banco,
                "especies": self.especies_banco,
                "formas_oficiais_presentes": self.formas_oficiais_presentes,
                "especies_personalizadas": self.especies_personalizadas,
            },
            "erros": self.erros,
            "avisos": self.avisos,
            "tipos": self.tipos,
            "achados": [asdict(achado) for achado in self.achados],
        }


def carregar_fonte_pokedex(caminho: Path | None = None) -> list[dict[str, Any]]:
    """Lê a fonte versionada, não os dados sensíveis do PostgreSQL."""
    arquivo = caminho or (
        Path(__file__).resolve().parents[2] / "data" / "catalogo" / "pokemons.json"
    )
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    if not isinstance(dados, dict) or not isinstance(dados.get("pokemons"), list):
        raise ValueError("Fonte da Pokédex inválida: falta a lista 'pokemons'.")
    if not dados["pokemons"]:
        raise ValueError("Fonte da Pokédex está vazia.")
    if dados.get("total") is not None and dados["total"] != len(dados["pokemons"]):
        raise ValueError("Total declarado na fonte não coincide com os registros.")
    return dados["pokemons"]


def construir_referencia_pokedex(
    registros: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, ReferenciaForma], dict[str, int]]:
    """Reconstrói números por primeira espécie na ordem das FORMAS.

    A validação estrita evita que uma fonte incompleta/corrompida produza
    diagnósticos ou números nacionais enganosos.
    """
    ordenados: list[tuple[int, str, str]] = []
    codigos: set[str] = set()
    indices: set[int] = set()
    for registro in registros:
        if not isinstance(registro, Mapping):
            raise ValueError("Há registros não estruturados na fonte da Pokédex.")
        codigo = str(registro.get("id") or "").strip()
        nome = str(registro.get("nome") or "").strip()
        indice = registro.get("ordem_catalogo")
        if not codigo or not nome or type(indice) is not int or indice < 1:
            raise ValueError(f"Forma sem código, nome ou ordem válida: {codigo!r}.")
        if codigo in codigos or indice in indices:
            raise ValueError(f"Código ou ordem duplicados na fonte: {codigo!r}.")
        codigos.add(codigo)
        indices.add(indice)
        ordenados.append((indice, codigo, nome))

    if not ordenados:
        raise ValueError("Nenhuma forma foi encontrada na referência da Pokédex.")

    especies: dict[str, int] = {}
    formas: dict[str, ReferenciaForma] = {}
    for indice, codigo, nome in sorted(ordenados):
        especie = nome_especie(nome)
        # Nidoran♀ e Nidoran♂ são nomes exatos DISTINTOS.
        if especie not in especies:
            especies[especie] = len(especies) + 1
        formas[codigo] = ReferenciaForma(
            codigo=codigo,
            nome=nome,
            especie=especie,
            numero=especies[especie],
            ordem=indice,
        )
    return formas, especies


def auditar_pokedex(
    especies: Iterable[Any],
    formas: Iterable[Any],
    registros_fonte: Iterable[Mapping[str, Any]],
    *,
    pokemons_por_forma: Mapping[Any, int] | None = None,
) -> ResultadoAuditoriaPokedex:
    """Compara fonte e banco sem escrever em nenhuma instância ORM.

    Ausências esperadas durante importações parciais e números NULL são
    avisos; vínculos errados ou números nacionais preenchidos incorretamente
    são erros. Contagens de Pokémon não revelam dados dos jogadores.
    """
    referencia_formas, referencia_especies = construir_referencia_pokedex(registros_fonte)
    especies_banco = list(especies)
    formas_banco = list(formas)
    especie_por_id = {especie.id: especie for especie in especies_banco}
    forma_por_codigo = {forma.codigo: forma for forma in formas_banco}
    contagens = pokemons_por_forma or {}
    achados: list[AchadoPokedex] = []

    def registrar(
        nivel: str,
        tipo: str,
        codigo: str,
        mensagem: str,
        *,
        forma: Any | None = None,
    ) -> None:
        achados.append(AchadoPokedex(
            nivel=nivel,
            tipo=tipo,
            codigo=codigo,
            mensagem=mensagem,
            pokemons_ativos=int(contagens.get(forma.id, 0)) if forma is not None else 0,
        ))

    formas_presentes = 0
    for codigo, referencia in referencia_formas.items():
        forma = forma_por_codigo.get(codigo)
        if forma is None:
            registrar(
                "aviso", "forma_oficial_ausente", codigo,
                f"Forma não encontrada no banco: {referencia.nome} "
                f"(#{referencia.numero:03d}).",
            )
            continue
        formas_presentes += 1
        especie = especie_por_id.get(forma.especie_id)
        if especie is None:
            registrar(
                "erro", "vinculo_sem_especie", codigo,
                f"Forma {referencia.nome} aponta para espécie inexistente.",
                forma=forma,
            )
        else:
            if especie.nome != referencia.especie:
                registrar(
                    "erro", "vinculo_especie_incorreto", codigo,
                    f"Espécie atual: {especie.nome} [{especie.codigo}]; "
                    f"esperada: {referencia.especie} (#{referencia.numero:03d}).",
                    forma=forma,
                )
            if especie.personalizada:
                registrar(
                    "aviso", "forma_oficial_em_especie_personalizada", codigo,
                    "Forma da fonte oficial vinculada a espécie marcada como personalizada.",
                    forma=forma,
                )
            if forma.ativo and not especie.ativo:
                registrar(
                    "erro", "forma_ativa_especie_inativa", codigo,
                    "Forma ativa pertence a uma espécie inativa.",
                    forma=forma,
                )

        if forma.nome != referencia.nome:
            registrar(
                "aviso", "nome_forma_divergente", codigo,
                f"Nome no banco: {forma.nome!r}; fonte: {referencia.nome!r}.",
                forma=forma,
            )
        configuracoes = forma.configuracoes if isinstance(forma.configuracoes, dict) else {}
        indice_atual = configuracoes.get("ordem_catalogo")
        if indice_atual != referencia.ordem:
            registrar(
                "aviso", "ordem_forma_divergente", codigo,
                f"ordem_catalogo atual: {indice_atual!r}; "
                f"esperada: {referencia.ordem}.",
                forma=forma,
            )

    # Os números são propriedade das espécies, não das 1.064 formas.
    # Nenhum número é preenchido automaticamente por esta auditoria.
    oficiais_por_nome: dict[str, list[Any]] = {}
    for especie in especies_banco:
        if not especie.personalizada:
            oficiais_por_nome.setdefault(especie.nome, []).append(especie)

    for nome, numero in referencia_especies.items():
        candidatos = oficiais_por_nome.get(nome, [])
        if not candidatos:
            algum_presente = any(
                forma.codigo in forma_por_codigo and forma.especie == nome
                for forma in referencia_formas.values()
            )
            registrar(
                "erro" if algum_presente else "aviso",
                "especie_oficial_ausente",
                nome,
                f"Espécie oficial {nome} (#{numero:03d}) não cadastrada "
                "como espécie não personalizada.",
            )
            continue
        if len(candidatos) > 1:
            registrar(
                "erro", "especie_oficial_duplicada", nome,
                f"Existem {len(candidatos)} registros oficiais para {nome}.",
            )
        for especie in candidatos:
            if especie.numero is None:
                registrar(
                    "aviso", "numero_nacional_ausente", especie.codigo,
                    f"{nome}: número nacional não preenchido; esperado #{numero:03d}.",
                )
            elif especie.numero != numero:
                registrar(
                    "erro", "numero_nacional_incorreto", especie.codigo,
                    f"{nome}: número cadastrado #{especie.numero}; "
                    f"esperado #{numero:03d}.",
                )

    # Números personalizados podem ser regionais; sinalize colisões com a
    # Pokédex nacional sem presumir automaticamente que sejam erros.
    numeros_oficiais = set(referencia_especies.values())
    for especie in especies_banco:
        if especie.personalizada and especie.numero in numeros_oficiais:
            registrar(
                "aviso", "numero_personalizado_colide_nacional", especie.codigo,
                f"{especie.nome}: número personalizado #{especie.numero:03d} "
                "coincide com a Pokédex nacional; revisar intenção.",
            )

    achados.sort(key=lambda item: (0 if item.nivel == "erro" else 1, item.tipo, item.codigo))
    return ResultadoAuditoriaPokedex(
        formas_fonte=len(referencia_formas),
        especies_fonte=len(referencia_especies),
        formas_banco=len(formas_banco),
        especies_banco=len(especies_banco),
        formas_oficiais_presentes=formas_presentes,
        especies_personalizadas=sum(bool(e.personalizada) for e in especies_banco),
        achados=achados,
    )
