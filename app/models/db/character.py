from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.db.base import JSON_DOCUMENT, ActiveMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.db.attributes import PersonagemAtributo
    from app.models.db.auth import Campanha, Usuario
    from app.models.db.inventory import PersonagemInsignia, PersonagemItem
    from app.models.db.pokemon_instance import Pokemon


class Personagem(UUIDPrimaryKeyMixin, TimestampMixin, ActiveMixin, db.Model):
    __tablename__ = "personagens"
    __table_args__ = (
        UniqueConstraint("usuario_id", "campanha_id", name="usuario_campanha"),
        CheckConstraint("nivel > 0", name="nivel_positivo"),
        CheckConstraint("pokedolares >= 0", name="pokedolares_nao_negativos"),
        CheckConstraint("pv_atual >= 0", name="pv_atual_nao_negativo"),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    campanha_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campanhas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    foto_url: Mapped[str | None] = mapped_column(String(500))
    nivel: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    idade: Mapped[int | None] = mapped_column(Integer)
    genero: Mapped[str | None] = mapped_column(String(60))
    origem: Mapped[str | None] = mapped_column(String(160))
    classe: Mapped[str | None] = mapped_column(String(160))
    estilo_combate: Mapped[str | None] = mapped_column(String(160))
    numeros_shiny: Mapped[list[int] | None] = mapped_column(JSON_DOCUMENT)
    pokedolares: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    pv_atual: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    beneficios_habilidades: Mapped[str | None] = mapped_column(Text)
    anotacoes: Mapped[str | None] = mapped_column(Text)

    usuario: Mapped[Usuario] = relationship(back_populates="personagens")
    campanha: Mapped[Campanha] = relationship(back_populates="personagens")
    atributos: Mapped[list[PersonagemAtributo]] = relationship(
        back_populates="personagem",
        cascade="all, delete-orphan",
    )
    pokemons: Mapped[list[Pokemon]] = relationship(
        back_populates="personagem",
        cascade="all, delete-orphan",
    )
    inventario: Mapped[list[PersonagemItem]] = relationship(
        back_populates="personagem",
        cascade="all, delete-orphan",
    )
    insignias: Mapped[list[PersonagemInsignia]] = relationship(
        back_populates="personagem",
        cascade="all, delete-orphan",
    )
