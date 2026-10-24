from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.auth import Campanha
    from app.models.db.character import Personagem
    from app.models.db.combat_catalog import Natureza
    from app.models.db.pokemon_catalog import FormaPokemon


class PokemonCapturavel(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "pokemons_capturaveis"
    __table_args__ = (
        UniqueConstraint("campanha_id", "ordem", name="campanha_ordem_capturavel"),
        CheckConstraint(
            "ordem IS NULL OR (ordem >= 1 AND ordem <= 15)",
            name="ordem_capturavel_valida",
        ),
    )

    campanha_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campanhas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forma_pokemon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formas_pokemon.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    encontrado_por_personagem_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("personagens.id", ondelete="SET NULL"),
        index=True,
    )
    natureza_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("naturezas.id", ondelete="SET NULL"),
        index=True,
    )
    genero: Mapped[str | None] = mapped_column(String(40))
    shiny: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )
    ordem: Mapped[int | None] = mapped_column(SmallInteger)
    observacoes: Mapped[str | None] = mapped_column(Text)

    campanha: Mapped[Campanha] = relationship()
    forma_pokemon: Mapped[FormaPokemon] = relationship()
    encontrado_por: Mapped[Personagem | None] = relationship()
    natureza: Mapped[Natureza | None] = relationship()
