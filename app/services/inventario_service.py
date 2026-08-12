from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    HistoricoAlteracao,
    Item,
    Personagem,
    PersonagemItem,
    Pokemon,
)


@dataclass(slots=True)
class ContextoInventario:
    personagem: Personagem
    inventario: list[PersonagemItem]
    pokemons: list[Pokemon]
    destinatarios: list[Personagem]
    catalogo: list[Item]

    @property
    def total_unidades(self) -> int:
        return sum(registro.quantidade for registro in self.inventario)

    @property
    def total_itens(self) -> int:
        return len(self.inventario)

    @property
    def total_equipados(self) -> int:
        return sum(1 for pokemon in self.pokemons if pokemon.item_equipado_id)


def _uuid(valor: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError):
        return None


def _inteiro(valor: Any, *, padrao: int = 0) -> int:
    try:
        return int(str(valor if valor is not None else "").strip() or padrao)
    except (TypeError, ValueError):
        return padrao


def _carregar_personagem_autorizado(
    personagem_id: uuid.UUID,
    campanha_id: str | uuid.UUID | None = None,
) -> Personagem | None:
    consulta = select(Personagem).where(
        Personagem.id == personagem_id,
        Personagem.ativo.is_(True),
    )
    campanha_uuid = _uuid(campanha_id)
    if campanha_id is not None and campanha_uuid is None:
        return None
    if campanha_uuid is not None:
        consulta = consulta.where(Personagem.campanha_id == campanha_uuid)
    return db.session.execute(consulta).scalar_one_or_none()


def _auditar(
    *,
    usuario_id: str | uuid.UUID | None,
    personagem_id: uuid.UUID,
    acao: str,
    antes: dict[str, Any] | None,
    depois: dict[str, Any] | None,
) -> None:
    db.session.add(
        HistoricoAlteracao(
            usuario_id=_uuid(usuario_id),
            entidade="inventario",
            registro_id=personagem_id,
            acao=acao,
            dados_anteriores=antes,
            dados_novos=depois,
        )
    )


def _snapshot_registro(registro: PersonagemItem | None) -> dict[str, Any] | None:
    if registro is None:
        return None
    return {
        "personagem_id": str(registro.personagem_id),
        "item_id": str(registro.item_id),
        "item": registro.item.nome if registro.item else None,
        "quantidade": registro.quantidade,
    }


def carregar_contexto_inventario(
    personagem_id: str | uuid.UUID,
    *,
    campanha_id: str | uuid.UUID | None = None,
) -> ContextoInventario | None:
    identificador = _uuid(personagem_id)
    if not identificador:
        return None
    consulta_personagem = select(Personagem).where(
        Personagem.id == identificador,
        Personagem.ativo.is_(True),
    )
    campanha_uuid = _uuid(campanha_id)
    if campanha_id is not None and campanha_uuid is None:
        return None
    if campanha_uuid is not None:
        consulta_personagem = consulta_personagem.where(
            Personagem.campanha_id == campanha_uuid
        )
    personagem = db.session.execute(
        consulta_personagem.options(
            selectinload(Personagem.usuario),
            selectinload(Personagem.campanha),
        )
    ).scalar_one_or_none()
    if personagem is None:
        return None

    inventario = list(
        db.session.execute(
            select(PersonagemItem)
            .where(
                PersonagemItem.personagem_id == personagem.id,
                PersonagemItem.quantidade > 0,
            )
            .options(selectinload(PersonagemItem.item).selectinload(Item.categoria))
            .join(Item, Item.id == PersonagemItem.item_id)
            .order_by(func.lower(Item.nome))
        ).scalars()
    )
    pokemons = list(
        db.session.execute(
            select(Pokemon)
            .where(Pokemon.personagem_id == personagem.id, Pokemon.ativo.is_(True))
            .options(
                selectinload(Pokemon.forma_pokemon),
                selectinload(Pokemon.item_equipado).selectinload(Item.categoria),
            )
            .order_by(Pokemon.localizacao, Pokemon.posicao)
        ).scalars()
    )
    destinatarios = list(
        db.session.execute(
            select(Personagem)
            .where(
                Personagem.campanha_id == personagem.campanha_id,
                Personagem.id != personagem.id,
                Personagem.ativo.is_(True),
            )
            .order_by(func.lower(Personagem.nome))
        ).scalars()
    )
    catalogo = list(
        db.session.execute(
            select(Item)
            .where(Item.ativo.is_(True))
            .options(selectinload(Item.categoria))
            .order_by(func.lower(Item.nome))
        ).scalars()
    )
    return ContextoInventario(
        personagem=personagem,
        inventario=inventario,
        pokemons=pokemons,
        destinatarios=destinatarios,
        catalogo=catalogo,
    )


def _registro_inventario(
    personagem_id: uuid.UUID,
    item_id: uuid.UUID,
    *,
    bloquear: bool = False,
) -> PersonagemItem | None:
    consulta = select(PersonagemItem).where(
        PersonagemItem.personagem_id == personagem_id,
        PersonagemItem.item_id == item_id,
    ).options(selectinload(PersonagemItem.item))
    if bloquear:
        consulta = consulta.with_for_update()
    return db.session.execute(consulta).scalar_one_or_none()


def _somar_sem_commit(personagem: Personagem, item: Item, quantidade: int) -> PersonagemItem:
    registro = _registro_inventario(personagem.id, item.id, bloquear=True)
    if registro is None:
        registro = PersonagemItem(personagem=personagem, item=item, quantidade=0)
        db.session.add(registro)
        db.session.flush()
    registro.quantidade += quantidade
    return registro


def _retirar_sem_commit(personagem: Personagem, item: Item, quantidade: int) -> PersonagemItem:
    registro = _registro_inventario(personagem.id, item.id, bloquear=True)
    if registro is None or registro.quantidade < quantidade:
        raise ValueError(f"Quantidade insuficiente de {item.nome} no inventário.")
    registro.quantidade -= quantidade
    return registro


def ajustar_quantidade_item(
    *,
    personagem_id: str | uuid.UUID,
    item_id: str | uuid.UUID,
    quantidade: Any,
    usuario_id: str | uuid.UUID | None,
    campanha_id: str | uuid.UUID | None = None,
) -> None:
    personagem_uuid = _uuid(personagem_id)
    item_uuid = _uuid(item_id)
    if not personagem_uuid or not item_uuid:
        raise ValueError("Personagem ou item inválido.")
    personagem = _carregar_personagem_autorizado(personagem_uuid, campanha_id)
    item = db.session.get(Item, item_uuid)
    if personagem is None or not personagem.ativo:
        raise ValueError("Personagem não encontrado.")
    if item is None:
        raise ValueError("Item não encontrado.")
    nova_quantidade = _inteiro(quantidade, padrao=-1)
    if nova_quantidade < 0 or nova_quantidade > 999999:
        raise ValueError("A quantidade deve ficar entre 0 e 999999.")

    registro = _registro_inventario(personagem.id, item.id, bloquear=True)
    antes = _snapshot_registro(registro)
    if registro is None:
        if nova_quantidade > 0:
            registro = PersonagemItem(
                personagem=personagem,
                item=item,
                quantidade=nova_quantidade,
            )
            db.session.add(registro)
            db.session.flush()
    else:
        registro.quantidade = nova_quantidade
        if nova_quantidade == 0:
            db.session.delete(registro)
            registro = None
    _auditar(
        usuario_id=usuario_id,
        personagem_id=personagem.id,
        acao="ajuste_quantidade",
        antes=antes,
        depois=_snapshot_registro(registro),
    )
    db.session.commit()


def adicionar_item(
    *,
    personagem_id: str | uuid.UUID,
    item_id: str | uuid.UUID,
    quantidade: Any,
    usuario_id: str | uuid.UUID | None,
    campanha_id: str | uuid.UUID | None = None,
) -> None:
    personagem_uuid = _uuid(personagem_id)
    item_uuid = _uuid(item_id)
    quantidade_int = _inteiro(quantidade, padrao=0)
    if not personagem_uuid or not item_uuid:
        raise ValueError("Personagem ou item inválido.")
    if quantidade_int < 1 or quantidade_int > 999999:
        raise ValueError("Informe uma quantidade entre 1 e 999999.")
    personagem = _carregar_personagem_autorizado(personagem_uuid, campanha_id)
    item = db.session.get(Item, item_uuid)
    if personagem is None or not personagem.ativo:
        raise ValueError("Personagem não encontrado.")
    if item is None or not item.ativo:
        raise ValueError("Selecione um item ativo do catálogo.")
    registro_atual = _registro_inventario(personagem.id, item.id, bloquear=True)
    antes = _snapshot_registro(registro_atual)
    registro = _somar_sem_commit(personagem, item, quantidade_int)
    _auditar(
        usuario_id=usuario_id,
        personagem_id=personagem.id,
        acao="adicao_item",
        antes=antes,
        depois=_snapshot_registro(registro),
    )
    db.session.commit()


def usar_item_consumivel(
    *,
    personagem_id: str | uuid.UUID,
    item_id: str | uuid.UUID,
    quantidade: Any = 1,
    usuario_id: str | uuid.UUID | None,
    campanha_id: str | uuid.UUID | None = None,
) -> None:
    personagem_uuid = _uuid(personagem_id)
    item_uuid = _uuid(item_id)
    quantidade_int = _inteiro(quantidade, padrao=1)
    if not personagem_uuid or not item_uuid:
        raise ValueError("Personagem ou item inválido.")
    if quantidade_int < 1 or quantidade_int > 999:
        raise ValueError("Informe uma quantidade válida para uso.")
    personagem = _carregar_personagem_autorizado(personagem_uuid, campanha_id)
    item = db.session.get(Item, item_uuid)
    if personagem is None or item is None:
        raise ValueError("Personagem ou item não encontrado.")
    if not item.consumivel:
        raise ValueError("Este item não está marcado como consumível.")
    registro = _registro_inventario(personagem.id, item.id, bloquear=True)
    antes = _snapshot_registro(registro)
    registro = _retirar_sem_commit(personagem, item, quantidade_int)
    depois = _snapshot_registro(registro) if registro.quantidade > 0 else None
    if registro.quantidade == 0:
        db.session.delete(registro)
    _auditar(
        usuario_id=usuario_id,
        personagem_id=personagem.id,
        acao="uso_item",
        antes=antes,
        depois={
            "inventario": depois,
            "usado": quantidade_int,
            "efeitos": item.efeitos,
        },
    )
    db.session.commit()


def equipar_item_pokemon(
    *,
    personagem_id: str | uuid.UUID,
    item_id: str | uuid.UUID,
    pokemon_id: str | uuid.UUID,
    usuario_id: str | uuid.UUID | None,
    campanha_id: str | uuid.UUID | None = None,
) -> None:
    personagem_uuid = _uuid(personagem_id)
    item_uuid = _uuid(item_id)
    pokemon_uuid = _uuid(pokemon_id)
    if not personagem_uuid or not item_uuid or not pokemon_uuid:
        raise ValueError("Personagem, Pokémon ou item inválido.")
    personagem = _carregar_personagem_autorizado(personagem_uuid, campanha_id)
    item = db.session.get(Item, item_uuid)
    pokemon = db.session.execute(
        select(Pokemon)
        .where(
            Pokemon.id == pokemon_uuid,
            Pokemon.personagem_id == personagem_uuid,
            Pokemon.ativo.is_(True),
        )
        .options(selectinload(Pokemon.item_equipado))
        .with_for_update()
    ).scalar_one_or_none()
    if personagem is None or item is None or pokemon is None:
        raise ValueError("Personagem, Pokémon ou item não encontrado.")
    if not item.ativo:
        raise ValueError("Itens inativos não podem ser equipados novamente.")
    if not item.equipavel:
        raise ValueError("Este item não pode ser carregado por Pokémon.")
    if pokemon.item_equipado_id == item.id:
        raise ValueError("Este Pokémon já está carregando o item selecionado.")

    antes = {
        "pokemon_id": str(pokemon.id),
        "item_equipado_id": str(pokemon.item_equipado_id) if pokemon.item_equipado_id else None,
    }
    _retirar_sem_commit(personagem, item, 1)
    registro_novo = _registro_inventario(personagem.id, item.id)
    if registro_novo is not None and registro_novo.quantidade == 0:
        db.session.delete(registro_novo)

    if pokemon.item_equipado is not None:
        _somar_sem_commit(personagem, pokemon.item_equipado, 1)
    pokemon.item_equipado = item
    _auditar(
        usuario_id=usuario_id,
        personagem_id=personagem.id,
        acao="equipar_item",
        antes=antes,
        depois={"pokemon_id": str(pokemon.id), "item_equipado_id": str(item.id)},
    )
    db.session.commit()


def desequipar_item_pokemon(
    *,
    personagem_id: str | uuid.UUID,
    pokemon_id: str | uuid.UUID,
    usuario_id: str | uuid.UUID | None,
    campanha_id: str | uuid.UUID | None = None,
) -> None:
    personagem_uuid = _uuid(personagem_id)
    pokemon_uuid = _uuid(pokemon_id)
    if not personagem_uuid or not pokemon_uuid:
        raise ValueError("Personagem ou Pokémon inválido.")
    personagem = _carregar_personagem_autorizado(personagem_uuid, campanha_id)
    pokemon = db.session.execute(
        select(Pokemon)
        .where(
            Pokemon.id == pokemon_uuid,
            Pokemon.personagem_id == personagem_uuid,
            Pokemon.ativo.is_(True),
        )
        .options(selectinload(Pokemon.item_equipado))
        .with_for_update()
    ).scalar_one_or_none()
    if personagem is None or pokemon is None:
        raise ValueError("Personagem ou Pokémon não encontrado.")
    if pokemon.item_equipado is None:
        raise ValueError("Este Pokémon não está carregando nenhum item.")
    item = pokemon.item_equipado
    antes = {"pokemon_id": str(pokemon.id), "item_equipado_id": str(item.id)}
    _somar_sem_commit(personagem, item, 1)
    pokemon.item_equipado = None
    _auditar(
        usuario_id=usuario_id,
        personagem_id=personagem.id,
        acao="desequipar_item",
        antes=antes,
        depois={"pokemon_id": str(pokemon.id), "item_equipado_id": None},
    )
    db.session.commit()


def transferir_item(
    *,
    personagem_origem_id: str | uuid.UUID,
    personagem_destino_id: str | uuid.UUID,
    item_id: str | uuid.UUID,
    quantidade: Any,
    usuario_id: str | uuid.UUID | None,
    campanha_id: str | uuid.UUID | None = None,
) -> None:
    origem_uuid = _uuid(personagem_origem_id)
    destino_uuid = _uuid(personagem_destino_id)
    item_uuid = _uuid(item_id)
    quantidade_int = _inteiro(quantidade, padrao=0)
    if not origem_uuid or not destino_uuid or not item_uuid:
        raise ValueError("Origem, destino ou item inválido.")
    if origem_uuid == destino_uuid:
        raise ValueError("Selecione outro personagem para a transferência.")
    if quantidade_int < 1 or quantidade_int > 999999:
        raise ValueError("Informe uma quantidade válida para transferência.")
    origem = _carregar_personagem_autorizado(origem_uuid, campanha_id)
    destino = _carregar_personagem_autorizado(destino_uuid, campanha_id)
    item = db.session.get(Item, item_uuid)
    if origem is None or destino is None or item is None:
        raise ValueError("Origem, destino ou item não encontrado.")
    if origem.campanha_id != destino.campanha_id:
        raise ValueError("A transferência só pode ocorrer dentro da mesma campanha.")
    if not origem.ativo or not destino.ativo:
        raise ValueError("A origem e o destino precisam estar ativos.")

    registro_origem = _registro_inventario(origem.id, item.id, bloquear=True)
    antes_origem = _snapshot_registro(registro_origem)
    registro_origem = _retirar_sem_commit(origem, item, quantidade_int)
    if registro_origem.quantidade == 0:
        db.session.delete(registro_origem)
    registro_destino_atual = _registro_inventario(destino.id, item.id, bloquear=True)
    antes_destino = _snapshot_registro(registro_destino_atual)
    registro_destino = _somar_sem_commit(destino, item, quantidade_int)
    _auditar(
        usuario_id=usuario_id,
        personagem_id=origem.id,
        acao="transferencia_saida",
        antes=antes_origem,
        depois={
            "destino_id": str(destino.id),
            "item_id": str(item.id),
            "quantidade": quantidade_int,
        },
    )
    _auditar(
        usuario_id=usuario_id,
        personagem_id=destino.id,
        acao="transferencia_entrada",
        antes=antes_destino,
        depois=_snapshot_registro(registro_destino),
    )
    db.session.commit()
