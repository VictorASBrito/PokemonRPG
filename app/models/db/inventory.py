from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.character import Personagem
    from app.models.db.pokemon_instance import Pokemon


class CategoriaItem(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "categorias_item"

    codigo: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    descricao: Mapped[str | None] = mapped_column(Text)

    itens: Mapped[list[Item]] = relationship(back_populates="categoria")


class Item(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "itens"
    __table_args__ = (
        Index(
            "ix_itens_nome_trgm",
            "nome",
            postgresql_using="gin",
            postgresql_ops={"nome": "gin_trgm_ops"},
        ),
    )

    codigo: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categorias_item.id", ondelete="SET NULL"),
        index=True,
    )
    descricao: Mapped[str | None] = mapped_column(Text)
    imagem_url: Mapped[str | None] = mapped_column(String(500))
    efeitos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON_DOCUMENT)
    personalizado: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )

    categoria: Mapped[CategoriaItem | None] = relationship(back_populates="itens")
    inventarios: Mapped[list[PersonagemItem]] = relationship(back_populates="item")
    pokemons_equipados: Mapped[list[Pokemon]] = relationship(back_populates="item_equipado")


class PersonagemItem(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "personagem_itens"
    __table_args__ = (
        UniqueConstraint("personagem_id", "item_id", name="personagem_item"),
        CheckConstraint("quantidade >= 0", name="quantidade_nao_negativa"),
    )

    personagem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("personagens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("itens.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantidade: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    personagem: Mapped[Personagem] = relationship(back_populates="inventario")
    item: Mapped[Item] = relationship(back_populates="inventarios")


class Insignia(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "insignias"

    codigo: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    imagem_url: Mapped[str | None] = mapped_column(String(500))

    personagens: Mapped[list[PersonagemInsignia]] = relationship(
        back_populates="insignia",
        cascade="all, delete-orphan",
    )


class PersonagemInsignia(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "personagem_insignias"
    __table_args__ = (
        UniqueConstraint("personagem_id", "insignia_id", name="personagem_insignia"),
    )

    personagem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("personagens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insignia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("insignias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    observacoes: Mapped[str | None] = mapped_column(Text)

    personagem: Mapped[Personagem] = relationship(back_populates="insignias")
    insignia: Mapped[Insignia] = relationship(back_populates="personagens")
