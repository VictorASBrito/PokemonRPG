from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.auth import Campanha


class ConjuntoRegras(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "conjuntos_regras"
    __table_args__ = (
        UniqueConstraint("campanha_id", "versao", name="campanha_versao"),
        Index(
            "uq_conjuntos_regras_campanha_em_uso",
            "campanha_id",
            unique=True,
            postgresql_where=text("em_uso"),
        ),
    )

    campanha_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campanhas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    versao: Mapped[str] = mapped_column(String(40), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    em_uso: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    campanha: Mapped[Campanha] = relationship(back_populates="conjuntos_regras")
    valores: Mapped[list[RegraValor]] = relationship(
        back_populates="conjunto_regras",
        cascade="all, delete-orphan",
    )


class Regra(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "regras"
    __table_args__ = (
        CheckConstraint(
            "tipo_valor IN ('inteiro', 'decimal', 'texto', 'booleano', 'json')",
            name="tipo_valor_valido",
        ),
    )

    codigo: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(80), nullable=False)
    tipo_valor: Mapped[str] = mapped_column(String(20), nullable=False)
    valor_padrao: Mapped[Any | None] = mapped_column(JSON_DOCUMENT)

    valores: Mapped[list[RegraValor]] = relationship(
        back_populates="regra",
        cascade="all, delete-orphan",
    )


class RegraValor(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "regra_valores"
    __table_args__ = (
        UniqueConstraint(
            "conjunto_regras_id",
            "regra_id",
            name="conjunto_regra",
        ),
    )

    conjunto_regras_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conjuntos_regras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    regra_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("regras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    valor: Mapped[Any] = mapped_column(JSON_DOCUMENT, nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text)

    conjunto_regras: Mapped[ConjuntoRegras] = relationship(back_populates="valores")
    regra: Mapped[Regra] = relationship(back_populates="valores")
