from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.attributes import PokemonBonusAtributo
    from app.models.db.character import Personagem
    from app.models.db.combat_catalog import Golpe, Natureza, StatusCondicao
    from app.models.db.inventory import Item
    from app.models.db.pokemon_catalog import FormaPokemon


class Pokemon(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "pokemons"
    __table_args__ = (
        UniqueConstraint(
            "personagem_id",
            "localizacao",
            "posicao",
            name="personagem_localizacao_posicao",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "localizacao IS NULL OR localizacao IN ('equipe', 'box')",
            name="localizacao_valida",
        ),
        CheckConstraint("posicao IS NULL OR posicao > 0", name="posicao_positiva"),
        CheckConstraint("pv_atual >= 0", name="pv_atual_nao_negativo"),
    )

    personagem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("personagens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forma_pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    apelido: Mapped[str | None] = mapped_column(String(160))
    genero: Mapped[str | None] = mapped_column(String(40))
    shiny: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )
    natureza_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("naturezas.id", ondelete="SET NULL"),
        index=True,
    )
    pv_atual: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    item_equipado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("itens.id", ondelete="SET NULL"),
        index=True,
    )
    localizacao: Mapped[str | None] = mapped_column(String(20), index=True)
    posicao: Mapped[int | None] = mapped_column(SmallInteger)
    anotacoes: Mapped[str | None] = mapped_column(Text)

    personagem: Mapped[Personagem] = relationship(back_populates="pokemons")
    forma_pokemon: Mapped[FormaPokemon] = relationship(back_populates="pokemons")
    natureza: Mapped[Natureza | None] = relationship(back_populates="pokemons")
    item_equipado: Mapped[Item | None] = relationship(back_populates="pokemons_equipados")
    bonus_atributos: Mapped[list[PokemonBonusAtributo]] = relationship(
        back_populates="pokemon",
        cascade="all, delete-orphan",
    )
    golpes: Mapped[list[PokemonGolpe]] = relationship(
        back_populates="pokemon",
        cascade="all, delete-orphan",
        order_by="PokemonGolpe.posicao",
    )
    status_ativos: Mapped[list[PokemonStatus]] = relationship(
        back_populates="pokemon",
        cascade="all, delete-orphan",
    )


class PokemonGolpe(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "pokemon_golpes"
    __table_args__ = (
        UniqueConstraint("pokemon_id", "posicao", name="pokemon_posicao_golpe"),
        UniqueConstraint("pokemon_id", "golpe_id", name="pokemon_golpe"),
        CheckConstraint("posicao BETWEEN 1 AND 4", name="posicao_valida"),
    )

    pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pokemons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    golpe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("golpes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    posicao: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    pokemon: Mapped[Pokemon] = relationship(back_populates="golpes")
    golpe: Mapped[Golpe] = relationship(back_populates="pokemons")


class PokemonStatus(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "pokemon_status"
    __table_args__ = (
        UniqueConstraint(
            "pokemon_id",
            "status_id",
            name="uq_pokemon_status_pokemon_id_status_id",
        ),
    )

    pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pokemons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("status_condicoes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    aplicado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    dados: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)

    pokemon: Mapped[Pokemon] = relationship(back_populates="status_ativos")
    status: Mapped[StatusCondicao] = relationship(back_populates="pokemons")
