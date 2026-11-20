"""Autorizações narrativas por Pokémon individual, não por espécie."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.auth import Usuario
    from app.models.db.pokemon_catalog import EvolucaoPokemon, FormaPokemon
    from app.models.db.pokemon_instance import Pokemon


class AutorizacaoEvolucaoPokemon(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "autorizacoes_evolucao_pokemon"
    __table_args__ = (
        UniqueConstraint("pokemon_id", "relacao_id", name="autorizacao_pokemon_relacao"),
        Index("ix_autorizacoes_evolucao_pokemon_ativo", "pokemon_id", "ativo"),
    )

    pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pokemons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evolucoes_pokemon.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    forma_origem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="RESTRICT"), nullable=False
    )
    autorizado_por_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    justificativa: Mapped[str] = mapped_column(Text, nullable=False)
    autorizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revogado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    motivo_revogacao: Mapped[str | None] = mapped_column(Text)

    pokemon: Mapped[Pokemon] = relationship(foreign_keys=[pokemon_id])
    relacao: Mapped[EvolucaoPokemon] = relationship(foreign_keys=[relacao_id])
    forma_origem: Mapped[FormaPokemon] = relationship(foreign_keys=[forma_origem_id])
    autorizado_por: Mapped[Usuario] = relationship(foreign_keys=[autorizado_por_id])
    revogado_por: Mapped[Usuario | None] = relationship(foreign_keys=[revogado_por_id])
