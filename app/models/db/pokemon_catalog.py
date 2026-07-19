from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.attributes import FormaPokemonAtributo
    from app.models.db.combat_catalog import FormaPokemonGolpe, Golpe
    from app.models.db.pokemon_instance import Pokemon


class TipoPokemon(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "tipos_pokemon"

    codigo: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    cor: Mapped[str | None] = mapped_column(String(20))
    icone_url: Mapped[str | None] = mapped_column(String(500))
    descricao: Mapped[str | None] = mapped_column(Text)

    formas: Mapped[list[FormaPokemonTipo]] = relationship(
        back_populates="tipo",
        cascade="all, delete-orphan",
    )
    efetividades_como_atacante: Mapped[list[EfetividadeTipo]] = relationship(
        back_populates="tipo_atacante",
        foreign_keys="EfetividadeTipo.tipo_atacante_id",
        cascade="all, delete-orphan",
    )
    efetividades_como_defensor: Mapped[list[EfetividadeTipo]] = relationship(
        back_populates="tipo_defensor",
        foreign_keys="EfetividadeTipo.tipo_defensor_id",
        cascade="all, delete-orphan",
    )


class EfetividadeTipo(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "efetividades_tipo"
    __table_args__ = (
        UniqueConstraint(
            "tipo_atacante_id",
            "tipo_defensor_id",
            name="atacante_defensor",
        ),
        CheckConstraint("multiplicador >= 0", name="multiplicador_nao_negativo"),
    )

    tipo_atacante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tipos_pokemon.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_defensor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tipos_pokemon.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    multiplicador: Mapped[Decimal] = mapped_column(
        Numeric(6, 3),
        nullable=False,
        default=1,
        server_default="1",
    )

    tipo_atacante: Mapped[TipoPokemon] = relationship(
        back_populates="efetividades_como_atacante",
        foreign_keys=[tipo_atacante_id],
    )
    tipo_defensor: Mapped[TipoPokemon] = relationship(
        back_populates="efetividades_como_defensor",
        foreign_keys=[tipo_defensor_id],
    )


class EspeciePokemon(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "especies_pokemon"
    __table_args__ = (
        Index(
            "ix_especies_pokemon_nome_trgm",
            "nome",
            postgresql_using="gin",
            postgresql_ops={"nome": "gin_trgm_ops"},
        ),
    )

    codigo: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    numero: Mapped[int | None] = mapped_column(Integer, index=True)
    geracao: Mapped[int | None] = mapped_column(SmallInteger)
    descricao: Mapped[str | None] = mapped_column(Text)
    personalizada: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )

    formas: Mapped[list[FormaPokemon]] = relationship(
        back_populates="especie",
        cascade="all, delete-orphan",
    )


class FormaPokemon(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "formas_pokemon"
    __table_args__ = (
        UniqueConstraint("especie_id", "codigo", name="especie_codigo_forma"),
        CheckConstraint(
            "categoria IN ('normal', 'regional', 'mega', 'alternativa', 'personalizada')",
            name="categoria_valida",
        ),
        Index(
            "ix_formas_pokemon_nome_trgm",
            "nome",
            postgresql_using="gin",
            postgresql_ops={"nome": "gin_trgm_ops"},
        ),
    )

    especie_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("especies_pokemon.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    categoria: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    imagem_url: Mapped[str | None] = mapped_column(String(500))
    imagem_shiny_url: Mapped[str | None] = mapped_column(String(500))
    configuracoes: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)

    especie: Mapped[EspeciePokemon] = relationship(back_populates="formas")
    tipos: Mapped[list[FormaPokemonTipo]] = relationship(
        back_populates="forma_pokemon",
        cascade="all, delete-orphan",
        order_by="FormaPokemonTipo.posicao",
    )
    atributos_base: Mapped[list[FormaPokemonAtributo]] = relationship(
        back_populates="forma_pokemon",
        cascade="all, delete-orphan",
    )
    golpes_disponiveis: Mapped[list[FormaPokemonGolpe]] = relationship(
        back_populates="forma_pokemon",
        cascade="all, delete-orphan",
    )
    pokemons: Mapped[list[Pokemon]] = relationship(back_populates="forma_pokemon")
    evolucoes_origem: Mapped[list[EvolucaoPokemon]] = relationship(
        back_populates="forma_origem",
        foreign_keys="EvolucaoPokemon.forma_origem_id",
        cascade="all, delete-orphan",
    )
    evolucoes_destino: Mapped[list[EvolucaoPokemon]] = relationship(
        back_populates="forma_destino",
        foreign_keys="EvolucaoPokemon.forma_destino_id",
    )


class FormaPokemonTipo(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "forma_pokemon_tipos"
    __table_args__ = (
        UniqueConstraint("forma_pokemon_id", "posicao", name="forma_posicao_tipo"),
        UniqueConstraint("forma_pokemon_id", "tipo_id", name="forma_tipo"),
        CheckConstraint("posicao IN (1, 2)", name="posicao_valida"),
    )

    forma_pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tipos_pokemon.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    posicao: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    forma_pokemon: Mapped[FormaPokemon] = relationship(back_populates="tipos")
    tipo: Mapped[TipoPokemon] = relationship(back_populates="formas")


class EvolucaoPokemon(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "evolucoes_pokemon"
    __table_args__ = (
        UniqueConstraint("forma_origem_id", "forma_destino_id", name="origem_destino"),
        CheckConstraint("forma_origem_id <> forma_destino_id", name="formas_distintas"),
    )

    forma_origem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forma_destino_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo_requisito: Mapped[str] = mapped_column(String(60), nullable=False)
    requisitos: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    observacoes: Mapped[str | None] = mapped_column(Text)

    forma_origem: Mapped[FormaPokemon] = relationship(
        back_populates="evolucoes_origem",
        foreign_keys=[forma_origem_id],
    )
    forma_destino: Mapped[FormaPokemon] = relationship(
        back_populates="evolucoes_destino",
        foreign_keys=[forma_destino_id],
    )
