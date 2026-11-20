"""Catálogo de treinadores NPC fixos, separado das instâncias de batalha."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin


class NPCModelo(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "npcs_catalogo"

    campanha_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    local_id: Mapped[str] = mapped_column(String(120), nullable=False)
    zona_nome: Mapped[str] = mapped_column(String(120), nullable=False)
    terreno: Mapped[str] = mapped_column(String(120), nullable=False)
    equipe: Mapped[list] = mapped_column(JSON_DOCUMENT, nullable=False)

    campanha = relationship("Campanha")
