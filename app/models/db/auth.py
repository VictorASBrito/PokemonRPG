from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.audit import HistoricoAlteracao
    from app.models.db.character import Personagem
    from app.models.db.rules import ConjuntoRegras


class Usuario(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "perfil IN ('administrador', 'mestre', 'tester', 'jogador')",
            name="perfil_valido",
        ),
    )

    login: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="jogador",
        server_default="jogador",
    )

    membros_campanha: Mapped[list[CampanhaMembro]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    personagens: Mapped[list[Personagem]] = relationship(back_populates="usuario")
    alteracoes: Mapped[list[HistoricoAlteracao]] = relationship(
        back_populates="usuario"
    )


class Campanha(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "campanhas"

    codigo: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(2000))

    membros: Mapped[list[CampanhaMembro]] = relationship(
        back_populates="campanha",
        cascade="all, delete-orphan",
    )
    personagens: Mapped[list[Personagem]] = relationship(back_populates="campanha")
    conjuntos_regras: Mapped[list[ConjuntoRegras]] = relationship(
        back_populates="campanha"
    )


class CampanhaMembro(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "campanha_membros"
    __table_args__ = (
        UniqueConstraint(
            "campanha_id",
            "usuario_id",
            name="campanha_usuario",
        ),
        CheckConstraint(
            "papel IN ('mestre', 'jogador', 'observador')",
            name="papel_valido",
        ),
    )

    campanha_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campanhas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    papel: Mapped[str] = mapped_column(String(20), nullable=False)

    campanha: Mapped[Campanha] = relationship(back_populates="membros")
    usuario: Mapped[Usuario] = relationship(back_populates="membros_campanha")
