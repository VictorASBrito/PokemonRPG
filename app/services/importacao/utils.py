from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

NAMESPACE_IMPORTACAO = uuid.UUID("fb92e1a1-7290-4977-a03e-fd1baf8313cc")


def slug(valor: Any, *, padrao: str = "registro") -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto or padrao


def uuid_legado(entidade: str, codigo: Any) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE_IMPORTACAO, f"{entidade}:{codigo}")


def inteiro(valor: Any, padrao: int = 0) -> int:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return padrao


def decimal(valor: Any, padrao: str = "0") -> Decimal:
    try:
        return Decimal(str(valor).replace(",", "."))
    except Exception:
        return Decimal(padrao)


def booleano(valor: Any, padrao: bool = False) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return padrao
    return str(valor).strip().lower() in {"1", "true", "sim", "s", "yes", "on"}


def data_hora(valor: Any) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def nome_especie(nome_forma: str) -> str:
    return str(nome_forma).split(" (", 1)[0].strip()


def categoria_forma(registro: dict[str, Any]) -> str:
    codigo = str(registro.get("id", "")).lower()
    nome = str(registro.get("nome", "")).lower()
    if "mega" in codigo or "(mega" in nome:
        return "mega"
    if any(regiao in codigo or f"({regiao}" in nome for regiao in ("alola", "galar", "hisui", "paldea")):
        return "regional"
    if "(" in nome:
        if "(normal" in nome:
            return "normal"
        return "alternativa"
    return "normal"


def arquivo_relativo(caminho: Path, raiz: Path) -> str:
    try:
        return caminho.resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return str(caminho)
