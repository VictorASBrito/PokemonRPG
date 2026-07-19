from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from app.services.importacao.utils import uuid_legado
from app.services.json_service import ler_json


def buscar_jogador_legado_por_usuario(
    data_dir: str | Path,
    campanha_codigo: str,
    usuario_id_banco: UUID | str,
) -> dict[str, Any] | None:
    """Localiza o JSON legado associado ao UUID do usuário importado.

    Esta ponte existe apenas enquanto ficha, Pokémon e Box ainda usam os
    serviços JSON. A autenticação e a gestão de acessos já usam PostgreSQL.
    """
    pasta = Path(data_dir) / "campanhas" / campanha_codigo / "jogadores"
    if not pasta.exists():
        return None

    usuario_uuid = str(usuario_id_banco)
    for arquivo in sorted(pasta.glob("*.json")):
        jogador = ler_json(arquivo, None)
        if not jogador:
            continue
        usuario_legado = str(jogador.get("usuario_id", "")).strip()
        if not usuario_legado:
            continue
        if str(uuid_legado("usuario", usuario_legado)) == usuario_uuid:
            jogador["_arquivo"] = arquivo
            return jogador
    return None


def buscar_id_jogador_legado(
    data_dir: str | Path,
    campanha_codigo: str,
    usuario_id_banco: UUID | str,
) -> str | None:
    jogador = buscar_jogador_legado_por_usuario(
        data_dir,
        campanha_codigo,
        usuario_id_banco,
    )
    if not jogador:
        return None
    jogador_id = str(jogador.get("id", "")).strip()
    return jogador_id or None
