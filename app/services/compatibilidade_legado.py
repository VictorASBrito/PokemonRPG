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


def sincronizar_ficha_legada(
    *,
    data_dir: str | Path,
    campanha_codigo: str,
    usuario_id_banco: UUID | str,
    ficha_banco: dict[str, Any],
) -> bool:
    """Atualiza apenas a ponte JSON ainda usada por Pokémon e Box.

    A ficha e o dashboard não leem mais estes campos como fonte oficial. A
    cópia temporária existe para que os cálculos dos Pokémon continuem usando
    nível e estilo de combate atualizados até a conversão da equipe/Box.
    """
    jogador = buscar_jogador_legado_por_usuario(
        data_dir,
        campanha_codigo,
        usuario_id_banco,
    )
    if not jogador:
        return False

    jogador.pop("_arquivo", None)
    jogador["treinador"] = dict(ficha_banco.get("treinador", {}))
    jogador["inventario"] = list(ficha_banco.get("inventario", []))
    jogador["insigneas"] = list(ficha_banco.get("insigneas", []))

    # Imports locais evitam que a camada de compatibilidade se torne uma
    # dependência circular dos serviços novos.
    from app.services.jogador_service import salvar_jogador
    from app.services.pokemon_service import sincronizar_pokemons_com_nivel_jogador

    sincronizar_pokemons_com_nivel_jogador(jogador, Path(data_dir))
    salvar_jogador(
        data_dir=data_dir,
        campanha_id=campanha_codigo,
        jogador=jogador,
    )
    return True
