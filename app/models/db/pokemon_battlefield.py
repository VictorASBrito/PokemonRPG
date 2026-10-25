"""Posição temporária dos Pokémon de uma campanha no campo compartilhado."""
from __future__ import annotations

import uuid
from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from app.models.db.base import UUIDPrimaryKeyMixin, TimestampMixin


class PokemonEmCampo(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "pokemons_em_campo"
    __table_args__ = (
        UniqueConstraint("pokemon_id", name="pokemon_unico_no_campo"),
        CheckConstraint("time_numero BETWEEN 1 AND 16", name="time_valido"),
    )

    campanha_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pokemons.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    time_numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    campanha = relationship("Campanha")
    pokemon = relationship("Pokemon")
