"""Negociação bilateral de Pokémon, com histórico persistente."""
from __future__ import annotations

import uuid
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, TimestampMixin, UUIDPrimaryKeyMixin


class TrocaPokemon(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "trocas_pokemon"
    __table_args__ = (
        CheckConstraint("proponente_id <> destinatario_id", name="participantes_distintos"),
        CheckConstraint("estado IN ('pendente', 'negociacao', 'concluida', 'recusada', 'cancelada')", name="estado_valido"),
        CheckConstraint("revisao >= 0", name="revisao_valida"),
    )
    campanha_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campanhas.id", ondelete="CASCADE"), index=True)
    proponente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personagens.id", ondelete="CASCADE"), index=True)
    destinatario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personagens.id", ondelete="CASCADE"), index=True)
    estado: Mapped[str] = mapped_column(String(20), default="pendente", server_default="pendente")
    revisao: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    versao_lock: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    __mapper_args__ = {"version_id_col": versao_lock}
    oferta_a: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list)
    oferta_b: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list)
    confirmou_a: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    confirmou_b: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
