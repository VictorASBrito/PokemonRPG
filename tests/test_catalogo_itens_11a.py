"""O importador nunca utiliza o banco de produção: fixture SQLite do projeto."""
import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import Item, Personagem, PersonagemItem, Pokemon, PokemonStatus, StatusCondicao
from app.services.inventario_service import usar_item_consumivel
from app.services.materiais_evolucao_service import material_por_identificador
from scripts.ampliar_catalogo_itens_11a import aplicar, carregar_lote, preparar
from scripts.acervo_icones_itens_11a import carregar_indice, baixar


ROOT = Path(__file__).resolve().parents[1]


def test_manifesto_imagens_e_regras_coerentes():
    lote = carregar_lote()
    indice = carregar_indice()
    assert len(lote) == len({i["codigo"] for i in lote}) == 16
    assert len(indice["arquivos"]) == len(set(indice["arquivos"])) == 2258
    for i in lote:
        if i["origem_icone"] == "local":
            assert (ROOT / "static/img/inventory/itens" / i["icone"]).is_file()
        else:
            assert i["icone"] in indice["arquivos"]
        if i["funcionalidade"] == "evolucao":
            assert material_por_identificador(i["codigo"])
    assert {"super-pocao", "hiper-pocao", "max-pocao"} <= {i["codigo"] for i in lote}


def test_acervo_rejeita_caminho_arbitrario(tmp_path):
    with pytest.raises(ValueError):
        baixar("../pocao.png", carregar_indice(), destino=tmp_path)
    assert not list(tmp_path.iterdir())


def test_importacao_local_preserva_registros_e_nao_duplica(app_db):
    with app_db.app_context():
        antes = db.session.scalar(select(func.count(Item.id)))
        existentes = list(db.session.scalars(select(Item)).all())
        ids = {i.id for i in existentes}
        lote = [i for i in carregar_lote() if i["origem_icone"] == "local"]
        assert len(lote) == 11
        plano = preparar(lote)
        assert all(p["acao"] == "criar" for p in plano)
        assert db.session.scalar(select(func.count(Item.id))) == antes
        aplicar(lote)
        assert db.session.scalar(select(func.count(Item.id))) == antes + 11
        assert ids <= {i.id for i in db.session.scalars(select(Item))}
        assert all(p["acao"] == "preservar" for p in aplicar(lote))
        assert db.session.scalar(select(func.count(Item.id))) == antes + 11


def test_icone_ausente_bloqueia_lote(app_db, tmp_path):
    with app_db.app_context():
        antes = db.session.scalar(select(func.count(Item.id)))
        with pytest.raises(ValueError, match="Lote bloqueado"):
            aplicar(raiz=tmp_path)
        assert db.session.scalar(select(func.count(Item.id))) == antes


def test_pocao_importada_tem_efeito_e_pedra_nao_e_gasta_pela_bag(app_db):
    with app_db.app_context():
        aplicar([m for m in carregar_lote()
                 if m["codigo"] in {"super-pocao", "water-stone"}])
        cura = db.session.scalar(select(Item).where(Item.codigo == "super-pocao"))
        pedra = db.session.scalar(select(Item).where(Item.codigo == "water-stone"))
        assert cura.efeitos["efeitos"][0]["valor"] == 60
        personagem = db.session.get(Personagem, UUID(app_db.config["TEST_IDS"]["personagem"]))
        db.session.add(PersonagemItem(personagem_id=personagem.id,
                                     item_id=pedra.id, quantidade=2))
        db.session.commit()
        with pytest.raises(ValueError, match="evolução autorizada"):
            usar_item_consumivel(personagem_id=personagem.id, item_id=pedra.id,
                                 usuario_id=None, campanha_id=personagem.campanha_id)
        assert db.session.scalar(select(PersonagemItem.quantidade)
                                 .where(PersonagemItem.item_id == pedra.id)) == 2


def test_lote_completo_e_cura_total_resolvem_status(app_db, tmp_path):
    from shutil import copyfile
    with app_db.app_context():
        lote = carregar_lote()
        # O teste não depende da rede. Os 5 ícones externos são substituídos
        # por um PNG de fixture, usado apenas na pasta temporária.
        for m in lote:
            pasta = "itens" if m["origem_icone"] == "local" else "acervo-pokeapi"
            arquivo = tmp_path / "static/img/inventory" / pasta / m["icone"]
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            origem = ROOT / "static/img/inventory/itens" / (
                m["icone"] if pasta == "itens" else "pocao.png")
            copyfile(origem, arquivo)
        totais = next(m for m in lote if m["codigo"] == "cura-total")
        atuais = set(db.session.scalars(select(StatusCondicao.codigo)))
        for codigo in totais["status"]:
            if codigo not in atuais:
                db.session.add(StatusCondicao(codigo=codigo, nome=codigo, ativo=True))
        db.session.commit()
        assert sum(p["acao"] == "criar" for p in aplicar(lote, raiz=tmp_path)) == 16
        item = db.session.scalar(select(Item).where(Item.codigo == "cura-total"))
        assert len(item.efeitos["efeitos"]) == 7
        pessoa = db.session.get(Personagem, UUID(app_db.config["TEST_IDS"]["personagem"]))
        pokemon = Pokemon(personagem_id=pessoa.id,
                          forma_pokemon_id=UUID(app_db.config["TEST_IDS"]["formas"]["bulbasaur"]),
                          pv_atual=5, localizacao="equipe", posicao=1, ativo=True)
        db.session.add(pokemon)
        db.session.flush()
        paralisado = db.session.scalar(select(StatusCondicao).where(
            StatusCondicao.codigo == "paralisado"))
        db.session.add(PokemonStatus(pokemon_id=pokemon.id, status_id=paralisado.id))
        db.session.add(PersonagemItem(personagem_id=pessoa.id,
                                     item_id=item.id, quantidade=2))
        pocao = db.session.scalar(select(Item).where(Item.codigo == "super-pocao"))
        db.session.add(PersonagemItem(personagem_id=pessoa.id,
                                     item_id=pocao.id, quantidade=2))
        db.session.commit()
        usar_item_consumivel(personagem_id=pessoa.id, item_id=item.id,
                             pokemon_id=pokemon.id, usuario_id=None,
                             campanha_id=pessoa.campanha_id)
        assert db.session.scalar(select(func.count(PokemonStatus.id)).where(
            PokemonStatus.pokemon_id == pokemon.id)) == 0
        assert db.session.scalar(select(PersonagemItem.quantidade).where(
            PersonagemItem.item_id == item.id)) == 1
        usar_item_consumivel(personagem_id=pessoa.id, item_id=pocao.id,
                             pokemon_id=pokemon.id, usuario_id=None,
                             campanha_id=pessoa.campanha_id)
        assert pokemon.pv_atual > 5
        assert db.session.scalar(select(PersonagemItem.quantidade).where(
            PersonagemItem.item_id == pocao.id)) == 1


def test_alias_preserva_item_existente(app_db):
    with app_db.app_context():
        item = Item(codigo="pedra-de-agua", nome="Pedra da Água", preco=17,
                    consumivel=False, ativo=True)
        db.session.add(item)
        db.session.commit()
        id_original = item.id
        lote = [m for m in carregar_lote() if m["codigo"] == "water-stone"]
        p = aplicar(lote)[0]
        assert p["acao"] == "preservar"
        assert p["existente"] == "pedra-de-agua"
        assert db.session.get(Item, id_original).preco == 17
        assert db.session.scalar(select(Item).where(Item.codigo == "water-stone")) is None
