"""Regras conservadoras para detectar naturezas importadas como equipamentos.

Este módulo não consulta nem escreve no banco; usado pelo comando de reparo
apenas com registros inequivocamente originados do importador das fichas.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def _normalizar(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold().strip()


def _slug(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-") or "registro"


def campo_item_repetido_da_natureza(nome_item: Any, nome_natureza: Any) -> bool:
    """Detecta o erro observado em todas as 49 fichas de origem, sem inferir outros campos."""
    return bool(_normalizar(nome_item) and _normalizar(nome_item) == _normalizar(nome_natureza))


def elegivel_para_desvincular(
    *,
    codigo_item: str,
    nome_item: str,
    nome_natureza: str,
    personalizado: bool,
    equipavel: bool,
    categoria_id: Any,
    preco: Any,
    consumivel: bool,
    uso_em_batalha: bool,
    efeitos: Any,
    aparece_em_inventario: bool,
) -> bool:
    """Exige proveniência inequívoca e ausência de uso legítimo conhecido.

    Mesmo quando verdadeiro, a função apenas sugere; a alteração real exige
    execução explícita do comando com --aplicar.
    """
    if not campo_item_repetido_da_natureza(nome_item, nome_natureza):
        return False
    if str(codigo_item) != (f"importado-ficha-{_slug(nome_item)}")[:140]:
        return False
    return (
        personalizado is True
        and equipavel is True
        and categoria_id is None
        and type(preco) is int
        and preco == 0
        and consumivel is False
        and uso_em_batalha is False
        and efeitos in (None, [], {})
        and not aparece_em_inventario
    )
