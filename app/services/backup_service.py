from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def criar_backup(caminho: str | Path, pasta_backup: str | Path | None = None) -> Path | None:
    origem = Path(caminho)
    if not origem.exists():
        return None

    destino_dir = Path(pasta_backup) if pasta_backup else origem.parent / "backups"
    destino_dir.mkdir(parents=True, exist_ok=True)

    horario = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destino = destino_dir / f"{origem.stem}_{horario}{origem.suffix}"
    shutil.copy2(origem, destino)
    return destino
