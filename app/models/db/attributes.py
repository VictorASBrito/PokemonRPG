from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.character import Personagem
    from app.models.db.pokemon_catalog import FormaPokemon
    from app.models.db.pokemon_instance import Pokemon


class Atributo(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "atributos"
    __table_args__ = (
        CheckConstraint(
            "escopo IN ('personagem', 'pokemon', 'ambos')",
            name="escopo_valido",
        ),
        CheckConstraint(
            "tipo_valor IN ('inteiro', 'decimal')",
            name="tipo_valor_valido",
        ),
    )

    codigo: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    escopo: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo_valor: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="inteiro",
        server_default="inteiro",
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    valores_personagem: Mapped[list[PersonagemAtributo]] = relationship(
        back_populates="atributo",
        cascade="all, delete-orphan",
    )
    valores_forma: Mapped[list[FormaPokemonAtributo]] = relationship(
        back_populates="atributo",
        cascade="all, delete-orphan",
    )
    bonus_pokemon: Mapped[list[PokemonBonusAtributo]] = relationship(
        back_populates="atributo",
        cascade="all, delete-orphan",
    )


class PersonagemAtributo(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "personagem_atributos"
    __table_args__ = (
        UniqueConstraint("personagem_id", "atributo_id", name="personagem_atributo"),
    )

    personagem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("personagens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atributo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("atributos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)

    personagem: Mapped[Personagem] = relationship(back_populates="atributos")
    atributo: Mapped[Atributo] = relationship(back_populates="valores_personagem")


class FormaPokemonAtributo(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "forma_pokemon_atributos"
    __table_args__ = (
        UniqueConstraint("forma_pokemon_id", "atributo_id", name="forma_atributo"),
    )

    forma_pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atributo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("atributos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    valor_base: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)

    forma_pokemon: Mapped[FormaPokemon] = relationship(back_populates="atributos_base")
    atributo: Mapped[Atributo] = relationship(back_populates="valores_forma")


class PokemonBonusAtributo(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "pokemon_bonus_atributos"
    __table_args__ = (
        UniqueConstraint("pokemon_id", "atributo_id", name="pokemon_atributo"),
    )

    pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pokemons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atributo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("atributos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    valor: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=0,
        server_default="0",
    )

    pokemon: Mapped[Pokemon] = relationship(back_populates="bonus_atributos")
    atributo: Mapped[Atributo] = relationship(back_populates="bonus_pokemon")
