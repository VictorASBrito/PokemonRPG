"""Adversários temporários do Campo, independentes das fichas e Boxes."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class GrupoNPCEmCampo(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "grupos_npc_campo"
    __table_args__ = (
        CheckConstraint("tipo IN ('npc', 'horda')", name="tipo_valido"),
        CheckConstraint("time_numero BETWEEN 1 AND 16", name="time_valido"),
    )

    campanha_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    time_numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    campanha = relationship("Campanha")
    pokemons: Mapped[list[PokemonNPCEmCampo]] = relationship(
        back_populates="grupo", cascade="all, delete-orphan",
        order_by="PokemonNPCEmCampo.criado_em"
    )


class PokemonNPCEmCampo(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "pokemons_npc_campo"
    __table_args__ = (
        CheckConstraint("nivel BETWEEN 1 AND 100", name="nivel_valido"),
        CheckConstraint("pv_maximo >= 1", name="pv_maximo_valido"),
        CheckConstraint("pv_atual BETWEEN 0 AND pv_maximo", name="pv_atual_valido"),
    )

    grupo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grupos_npc_campo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    forma_pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    nivel: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    pv_maximo: Mapped[int] = mapped_column(Integer, nullable=False)
    pv_atual: Mapped[int] = mapped_column(Integer, nullable=False)
    shiny: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    grupo: Mapped[GrupoNPCEmCampo] = relationship(back_populates="pokemons")
    forma_pokemon = relationship("FormaPokemon")
