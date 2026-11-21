"""Ordenação de apresentação, sem alterar quantidades ou equipamentos."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import Item, Personagem, PersonagemItem
from app.services.inventario_apresentacao import BOLSAS, bolsa_item


def salvar_ordem(*, personagem_id, usuario_id, campanha_id, bolsa, itens):
    try:
        personagem_id = UUID(str(personagem_id))
        usuario_id = UUID(str(usuario_id))
        campanha_id = UUID(str(campanha_id))
        if not isinstance(itens, list) or not 1 <= len(itens) <= 2000:
            raise ValueError()
        ids = [UUID(str(i)) for i in itens]
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Ordem inválida.") from None
    if bolsa not in {b["codigo"] for b in BOLSAS} or len(ids) != len(set(ids)):
        raise ValueError("Ordem inválida.")
    personagem = db.session.scalar(select(Personagem).where(
        Personagem.id == personagem_id,
        Personagem.usuario_id == usuario_id,
        Personagem.campanha_id == campanha_id,
        Personagem.ativo.is_(True),
    ).with_for_update())
    if personagem is None:
        raise PermissionError("Inventário não autorizado.")
    registros = db.session.scalars(select(PersonagemItem).where(
        PersonagemItem.personagem_id == personagem_id,
        PersonagemItem.quantidade > 0,
    ).options(selectinload(PersonagemItem.item).selectinload(Item.categoria))
      .order_by(PersonagemItem.id).with_for_update()).all()
    atuais = {r.item_id: r for r in registros if bolsa_item(r.item) == bolsa}
    if set(ids) != set(atuais):
        raise ValueError("A bolsa mudou. Atualize a página e tente novamente.")
    for posicao, item_id in enumerate(ids, 1):
        atuais[item_id].ordem_bolsa = posicao
    db.session.commit()
