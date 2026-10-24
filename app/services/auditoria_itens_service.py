"""Verificação conservadora, somente de leitura, de dados do catálogo de itens.

Não corrige registros e não importa regras da Pokédex ou catálogos externos.
Recebe dicionários simples para permitir testes sem um banco PostgreSQL.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


TIPOS_EFEITO = frozenset({
    "texto", "recuperar_pv", "remover_status", "alterar_atributo",
    "causar_dano", "modificar_calculo", "evolucao", "mega_evolucao",
})
ALVOS = frozenset({"personagem", "pokemon", "portador", "grupo"})
OPERACOES = frozenset({"fixo", "percentual", "dados"})
PRECO_MAXIMO = 999_999_999


@dataclass(frozen=True)
class AchadoAuditoria:
    nivel: str  # "erro" ou "aviso"
    codigo: str
    mensagem: str


@dataclass
class ResultadoAuditoria:
    total_itens: int = 0
    total_categorias: int = 0
    ativos: int = 0
    categorias: dict[str, int] = field(default_factory=dict)
    achados: list[AchadoAuditoria] = field(default_factory=list)

    @property
    def erros(self) -> int:
        return sum(a.nivel == "erro" for a in self.achados)

    @property
    def avisos(self) -> int:
        return sum(a.nivel == "aviso" for a in self.achados)


def _identificador(value: Any) -> str:
    return str(value) if value is not None else ""


def _normalizar(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _inteiro_positivo(value: Any) -> bool:
    return type(value) is int and value > 0


def _validar_efeitos(
    resultado: ResultadoAuditoria,
    item_codigo: str,
    efeitos: Any,
    *,
    status: set[str],
    atributos: set[str],
    tipos: set[str],
) -> None:
    def registrar(nivel: str, mensagem: str) -> None:
        resultado.achados.append(AchadoAuditoria(nivel, item_codigo, mensagem))

    if efeitos is None or efeitos == []:
        return  # Catálogo permite itens sem efeitos automáticos.
    if isinstance(efeitos, dict):
        if "efeitos" in efeitos or "versao" in efeitos:
            if efeitos.get("versao") != 1:
                registrar("aviso", "Versão de efeitos ausente/diferente de 1; verificar compatibilidade.")
            lista = efeitos.get("efeitos")
            if not isinstance(lista, list):
                registrar("erro", "Documento de efeitos sem lista 'efeitos' válida.")
                return
        elif "tipo" in efeitos:
            registrar("aviso", "Efeito legado em objeto único (fora do formato versionado).")
            lista = [efeitos]
        elif "texto" in efeitos:
            registrar("aviso", "Efeito textual legado sem formato versionado.")
            lista = [{"tipo": "texto", "texto": efeitos.get("texto")}]
        else:
            registrar("aviso", "Documento de efeitos legado não reconhecido; verificar manualmente.")
            return
    elif isinstance(efeitos, list):
        registrar("aviso", "Lista de efeitos em formato legado, sem versão.")
        lista = efeitos
    else:
        registrar("erro", "Efeitos armazenados em formato inesperado (esperado JSON objeto/lista).")
        return

    if len(lista) > 20:
        registrar("erro", f"Possui {len(lista)} efeitos; limite do editor: 20.")

    for i, efeito in enumerate(lista, 1):
        rotulo = f"Efeito {i}"
        if not isinstance(efeito, dict):
            registrar("erro", f"{rotulo}: não é um objeto JSON.")
            continue
        tipo = efeito.get("tipo") or "texto"
        if not isinstance(tipo, str) or tipo not in TIPOS_EFEITO:
            registrar("erro", f"{rotulo}: tipo desconhecido ({tipo!s}).")
            continue
        alvo = efeito.get("alvo") or "pokemon"
        if not isinstance(alvo, str) or alvo not in ALVOS:
            registrar("erro", f"{rotulo}: alvo inválido ({alvo!s}).")
        if tipo == "texto" and not str(efeito.get("texto") or "").strip():
            registrar("erro", f"{rotulo}: descrição textual vazia.")
        elif tipo == "recuperar_pv":
            operacao = efeito.get("operacao") or "fixo"
            if not isinstance(operacao, str) or operacao not in OPERACOES:
                registrar("erro", f"{rotulo}: operação de recuperação inválida.")
            elif operacao == "dados":
                if not str(efeito.get("expressao") or "").strip():
                    registrar("erro", f"{rotulo}: expressão de dados vazia.")
            elif not _inteiro_positivo(efeito.get("valor")):
                registrar("erro", f"{rotulo}: recuperação exige valor inteiro positivo.")
        elif tipo == "remover_status":
            status_id = _identificador(efeito.get("status_id"))
            if status_id and status_id not in status:
                registrar("erro", f"{rotulo}: status inexistente/inativo.")
            if not status_id and not efeito.get("todos"):
                registrar("aviso", f"{rotulo}: não seleciona status nem 'todos'.")
        elif tipo == "alterar_atributo":
            if not isinstance(efeito.get("atributo"), str) or efeito.get("atributo") not in atributos:
                registrar("erro", f"{rotulo}: atributo inexistente/inativo.")
            if not isinstance((efeito.get("operacao") or "fixo"), str) or (efeito.get("operacao") or "fixo") not in {"fixo", "percentual"}:
                registrar("erro", f"{rotulo}: operação de atributo inválida.")
        elif tipo == "causar_dano":
            if not str(efeito.get("expressao") or "").strip():
                registrar("erro", f"{rotulo}: expressão de dano vazia.")
        elif tipo == "modificar_calculo":
            if not str(efeito.get("chave") or "").strip():
                registrar("erro", f"{rotulo}: chave de cálculo vazia.")
            if not isinstance((efeito.get("operacao") or "percentual"), str) or (efeito.get("operacao") or "percentual") not in OPERACOES:
                registrar("erro", f"{rotulo}: operação de cálculo desconhecida.")
            tipo_id = _identificador(efeito.get("tipo_id"))
            if tipo_id and tipo_id not in tipos:
                registrar("erro", f"{rotulo}: tipo Pokémon inexistente/inativo.")


def auditar_itens(
    itens: Iterable[Mapping[str, Any]],
    categorias: Iterable[Mapping[str, Any]],
    *,
    status_ativos: Iterable[str] = (),
    atributos_ativos: Iterable[str] = (),
    tipos_ativos: Iterable[str] = (),
) -> ResultadoAuditoria:
    """Retorna achados verificáveis e avisos, sem realizar nenhuma escrita."""
    dados_itens = list(itens)
    dados_categorias = list(categorias)
    resultado = ResultadoAuditoria(
        total_itens=len(dados_itens),
        total_categorias=len(dados_categorias),
        ativos=sum(item.get("ativo") is True for item in dados_itens),
    )
    status, atributos, tipos = set(status_ativos), set(atributos_ativos), set(tipos_ativos)
    por_id_categoria = {_identificador(c.get("id")): c for c in dados_categorias}

    def registrar(nivel: str, codigo: str, mensagem: str) -> None:
        resultado.achados.append(AchadoAuditoria(nivel, codigo, mensagem))

    nomes_categoria: dict[str, list[str]] = defaultdict(list)
    codigos_categoria: dict[str, list[str]] = defaultdict(list)
    for categoria in dados_categorias:
        cod = _identificador(categoria.get("codigo")) or "(sem código)"
        if not str(categoria.get("nome") or "").strip():
            registrar("erro", cod, "Categoria sem nome.")
        nomes_categoria[_normalizar(categoria.get("nome"))].append(cod)
        codigos_categoria[_normalizar(categoria.get("codigo"))].append(cod)

    for grupos, rotulo in ((nomes_categoria, "nome"), (codigos_categoria, "código")):
        for chave, associados in grupos.items():
            if chave and len(associados) > 1:
                registrar("aviso", "categorias", f"Categorias com {rotulo} equivalente: {', '.join(associados)}.")

    por_codigo: dict[str, list[str]] = defaultdict(list)
    por_nome_categoria: dict[tuple[str, str], list[str]] = defaultdict(list)
    totais_categoria: Counter[str] = Counter()

    for item in dados_itens:
        codigo = _identificador(item.get("codigo")) or "(sem código)"
        nome = str(item.get("nome") or "").strip()
        codigo_normalizado = _normalizar(codigo)
        if codigo == "(sem código)":
            registrar("erro", codigo, "Item sem código.")
        if not nome:
            registrar("erro", codigo, "Item sem nome.")
        por_codigo[codigo_normalizado].append(codigo)

        cid = _identificador(item.get("categoria_id"))
        categoria = por_id_categoria.get(cid) if cid else None
        categoria_codigo = _identificador(categoria.get("codigo")) if categoria else "(sem categoria)"
        totais_categoria[categoria_codigo] += 1
        if not cid:
            registrar("aviso", codigo, "Item sem categoria; confirmar classificação.")
        elif categoria is None:
            registrar("erro", codigo, "Referência a categoria inexistente.")
        elif item.get("ativo") and not categoria.get("ativo"):
            registrar("erro", codigo, "Item ativo vinculado a categoria inativa.")
        if nome:
            por_nome_categoria[(cid, _normalizar(nome))].append(codigo)

        preco = item.get("preco")
        if type(preco) is not int or preco < 0 or preco > PRECO_MAXIMO:
            registrar("erro", codigo, "Preço inválido ou fora do limite do formulário.")
        _validar_efeitos(
            resultado, codigo, item.get("efeitos"),
            status=status, atributos=atributos, tipos=tipos,
        )

    for codigo_normalizado, encontrados in por_codigo.items():
        if codigo_normalizado and len(encontrados) > 1:
            registrar("erro", "itens", f"Códigos equivalentes (ignorando caixa/espaços): {', '.join(encontrados)}.")
    for (_, nome), encontrados in por_nome_categoria.items():
        if nome and len(encontrados) > 1:
            registrar("aviso", "itens", f"Possíveis nomes duplicados na mesma categoria: {', '.join(encontrados)}.")

    resultado.categorias = dict(sorted(totais_categoria.items(), key=lambda par: par[0].casefold()))
    return resultado
