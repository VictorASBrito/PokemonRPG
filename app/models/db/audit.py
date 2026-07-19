from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.auth import Usuario


class HistoricoAlteracao(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "historico_alteracoes"

    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        index=True,
    )
    entidade: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    registro_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    acao: Mapped[str] = mapped_column(String(40), nullable=False)
    dados_anteriores: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON_DOCUMENT)
    dados_novos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON_DOCUMENT)

    usuario: Mapped[Usuario | None] = relationship(back_populates="alteracoes")
