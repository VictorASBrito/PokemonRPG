from __future__ import annotations

import json
import os
import tempfile
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

_LOCK = threading.RLock()


def ler_json(caminho: str | Path, padrao: Any = None) -> Any:
    arquivo = Path(caminho)

    if not arquivo.exists():
        return deepcopy(padrao)

    try:
        with arquivo.open("r", encoding="utf-8") as entrada:
            return json.load(entrada)
    except json.JSONDecodeError as erro:
        raise ValueError(f"JSON inválido em {arquivo}: {erro}") from erro


def salvar_json(caminho: str | Path, dados: Any) -> None:
    """Salva em arquivo temporário e substitui o original de forma atômica."""
    arquivo = Path(caminho)
    arquivo.parent.mkdir(parents=True, exist_ok=True)

    with _LOCK:
        descritor, temporario = tempfile.mkstemp(
            prefix=f".{arquivo.name}.",
            suffix=".tmp",
            dir=str(arquivo.parent),
        )

        try:
            with os.fdopen(descritor, "w", encoding="utf-8") as saida:
                json.dump(dados, saida, ensure_ascii=False, indent=2)
                saida.write("\n")
                saida.flush()
                os.fsync(saida.fileno())

            os.replace(temporario, arquivo)
        except Exception:
            try:
                os.unlink(temporario)
            except FileNotFoundError:
                pass
            raise
