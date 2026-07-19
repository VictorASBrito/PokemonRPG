from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.attributes import Atributo
    from app.models.db.pokemon_catalog import FormaPokemon, TipoPokemon
    from app.models.db.pokemon_instance import Pokemon, PokemonGolpe, PokemonStatus


class CategoriaGolpe(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "categorias_golpe"

    codigo: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descricao: Mapped[str | None] = mapped_column(Text)

    golpes: Mapped[list[Golpe]] = relationship(back_populates="categoria")


class Golpe(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "golpes"
    __table_args__ = (
        CheckConstraint(
            "precisao IS NULL OR (precisao >= 0 AND precisao <= 100)",
            name="precisao_percentual_valida",
        ),
        Index(
            "ix_golpes_nome_trgm",
            "nome",
            postgresql_using="gin",
            postgresql_ops={"nome": "gin_trgm_ops"},
        ),
    )

    codigo: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    tipo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tipos_pokemon.id", ondelete="RESTRICT"),
        index=True,
    )
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categorias_golpe.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    expressao_dano: Mapped[str | None] = mapped_column(String(80))
    precisao: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    prioridade: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    descricao: Mapped[str | None] = mapped_column(Text)
    efeitos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON_DOCUMENT)
    personalizado: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )

    tipo: Mapped[TipoPokemon | None] = relationship()
    categoria: Mapped[CategoriaGolpe] = relationship(back_populates="golpes")
    formas: Mapped[list[FormaPokemonGolpe]] = relationship(
        back_populates="golpe",
        cascade="all, delete-orphan",
    )
    pokemons: Mapped[list[PokemonGolpe]] = relationship(
        back_populates="golpe",
        cascade="all, delete-orphan",
    )


class FormaPokemonGolpe(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "forma_pokemon_golpes"
    __table_args__ = (
        UniqueConstraint("forma_pokemon_id", "golpe_id", "metodo", name="forma_golpe_metodo"),
        CheckConstraint("nivel_requerido IS NULL OR nivel_requerido > 0", name="nivel_positivo"),
    )

    forma_pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    golpe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("golpes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metodo: Mapped[str] = mapped_column(String(40), nullable=False)
    nivel_requerido: Mapped[int | None] = mapped_column(Integer)
    configuracoes: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    observacoes: Mapped[str | None] = mapped_column(Text)

    forma_pokemon: Mapped[FormaPokemon] = relationship(back_populates="golpes_disponiveis")
    golpe: Mapped[Golpe] = relationship(back_populates="formas")


class Natureza(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "naturezas"

    codigo: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    descricao: Mapped[str | None] = mapped_column(Text)

    modificadores: Mapped[list[NaturezaModificador]] = relationship(
        back_populates="natureza",
        cascade="all, delete-orphan",
    )
    pokemons: Mapped[list[Pokemon]] = relationship(back_populates="natureza")


class NaturezaModificador(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "natureza_modificadores"
    __table_args__ = (
        UniqueConstraint("natureza_id", "atributo_id", name="natureza_atributo"),
        CheckConstraint(
            "tipo_modificador IN ('percentual', 'fixo')",
            name="tipo_modificador_valido",
        ),
    )

    natureza_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("naturezas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atributo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("atributos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo_modificador: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    natureza: Mapped[Natureza] = relationship(back_populates="modificadores")
    atributo: Mapped[Atributo] = relationship()


class StatusCondicao(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "status_condicoes"

    codigo: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    descricao: Mapped[str | None] = mapped_column(Text)
    efeitos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON_DOCUMENT)

    pokemons: Mapped[list[PokemonStatus]] = relationship(
        back_populates="status",
        cascade="all, delete-orphan",
    )
