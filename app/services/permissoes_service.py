"""Permissões reais do usuário, obtidas sempre do banco.

O campo de sessão "perfil" representa somente a navegação mestre/jogador.
As autorizações de criar Pokémon e editar características protegidas usam o
perfil atual no PostgreSQL, inclusive
quando o mestre muda o acesso de alguém que já estava conectado.
"""
from __future__ import annotations

import uuid

from app.extensions import db
from app.models.db import Usuario

PERFIS_MESTRE = frozenset({"mestre", "administrador"})
PERFIS_JOGADOR = frozenset({"jogador", "tester"})
PERFIS_PERMITIDOS_GESTAO = frozenset({"jogador", "tester"})


def perfil_usuario_atual(usuario_id: str | uuid.UUID | None) -> str | None:
    try:
        identificador = uuid.UUID(str(usuario_id))
    except (TypeError, ValueError, AttributeError):
        return None
    usuario = db.session.get(Usuario, identificador)
    return usuario.perfil if usuario is not None and usuario.ativo else None


def pode_criar_pokemon(usuario_id: str | uuid.UUID | None) -> bool:
    return perfil_usuario_atual(usuario_id) in (PERFIS_MESTRE | {"tester"})


def pode_gerar_item(usuario_id: str | uuid.UUID | None) -> bool:
    return perfil_usuario_atual(usuario_id) in PERFIS_MESTRE


def pode_editar_identidade_pokemon(usuario_id: str | uuid.UUID | None) -> bool:
    """Mestre/Admin e Tester podem editar a identidade dos próprios Pokémon.

    A rota do mestre continua restrita ao mestre; o Tester só alcança
    as rotas pessoais. O perfil é consultado no PostgreSQL a cada operação.
    """
    return perfil_usuario_atual(usuario_id) in (PERFIS_MESTRE | {"tester"})
