"""O importador nunca utiliza o banco de produção: fixture SQLite do projeto."""
import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import Item, Personagem, PersonagemItem, Pokemon, StatusCondicao
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
