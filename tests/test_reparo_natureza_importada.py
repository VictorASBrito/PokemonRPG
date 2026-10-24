"""Testes das condições de segurança do reparo de itens fantasma."""

from app.services.reparo_natureza_importada import (
    campo_item_repetido_da_natureza,
    elegivel_para_desvincular,
)


def registro_seguro(**alteracoes):
    dados = {
        "codigo_item": "importado-ficha-timido",
        "nome_item": "Tímido",
        "nome_natureza": "Tímido",
        "personalizado": True,
        "equipavel": True,
        "categoria_id": None,
        "preco": 0,
        "consumivel": False,
        "uso_em_batalha": False,
        "efeitos": None,
        "aparece_em_inventario": False,
    }
    dados.update(alteracoes)
    return dados


def test_aceita_apenas_item_importado_idêntico_a_natureza():
    assert campo_item_repetido_da_natureza("Tímido", "Timido")
    assert elegivel_para_desvincular(**registro_seguro())
    assert not elegivel_para_desvincular(**registro_seguro(nome_item="Baga"))
    assert not elegivel_para_desvincular(**registro_seguro(codigo_item="item-editor-timido"))


def test_nao_altera_itens_modificados_ou_que_possam_ter_uso_legitimo():
    for variacao in (
        {"personalizado": False},
        {"equipavel": False},
        {"categoria_id": "categoria"},
        {"preco": 25},
        {"consumivel": True},
        {"uso_em_batalha": True},
        {"efeitos": {"versao": 1, "efeitos": [{"tipo": "texto", "texto": "teste"}]}},
        {"aparece_em_inventario": True},
    ):
        assert not elegivel_para_desvincular(**registro_seguro(**variacao))


def test_elegibilidade_ignora_acento_e_case_sem_confundir_valores():
    assert elegivel_para_desvincular(**registro_seguro(nome_item="Timido"))
    assert not elegivel_para_desvincular(**registro_seguro(nome_natureza="Modesto"))


def test_comando_simula_e_somente_aplica_sob_confirmacao(app_db):
    from sqlalchemy import select
    from app.extensions import db
    from app.models.db import FormaPokemon, HistoricoAlteracao, Item, Natureza, Personagem, Pokemon

    with app_db.app_context():
        item = Item(
            codigo="importado-ficha-docil", nome="Dócil", personalizado=True,
            equipavel=True, consumivel=False, uso_em_batalha=False, preco=0, ativo=True,
        )
        pokemon = Pokemon(
            personagem=db.session.scalar(select(Personagem)),
            forma_pokemon=db.session.scalar(select(FormaPokemon)),
            natureza=db.session.scalar(select(Natureza).where(Natureza.codigo == "docil")),
            item_equipado=item, pv_atual=10, localizacao="equipe", posicao=1, ativo=True,
        )
        db.session.add(pokemon)
        db.session.commit()
        pokemon_id, item_id = pokemon.id, item.id

    runner = app_db.test_cli_runner()
    simulacao = runner.invoke(args=["catalogo", "revisar-naturezas-importadas"])
    assert simulacao.exit_code == 0, simulacao.output
    assert "SIMULAÇÃO" in simulacao.output
    assert "elegíveis à correção: 1" in simulacao.output
    with app_db.app_context():
        assert db.session.get(Pokemon, pokemon_id).item_equipado_id == item_id

    aplicar = runner.invoke(args=["catalogo", "revisar-naturezas-importadas", "--aplicar"])
    assert aplicar.exit_code == 0, aplicar.output
    assert "Corrigidos 1 vínculo(s)" in aplicar.output
    with app_db.app_context():
        assert db.session.get(Pokemon, pokemon_id).item_equipado_id is None
        assert db.session.get(Item, item_id) is not None
        eventos = db.session.scalars(select(HistoricoAlteracao).where(
            HistoricoAlteracao.entidade == "pokemon", HistoricoAlteracao.registro_id == pokemon_id
        )).all()
        assert len(eventos) == 1

    novamente = runner.invoke(args=["catalogo", "revisar-naturezas-importadas", "--aplicar"])
    assert novamente.exit_code == 0, novamente.output
    assert "Nenhuma mudança necessária" in novamente.output


def test_comando_preserva_item_de_natureza_com_preco_ou_inventario(app_db):
    from sqlalchemy import select
    from app.extensions import db
    from app.models.db import FormaPokemon, Item, Natureza, Personagem, PersonagemItem, Pokemon

    with app_db.app_context():
        pessoa = db.session.scalar(select(Personagem))
        item = Item(
            codigo="importado-ficha-docil", nome="Dócil", personalizado=True,
            equipavel=True, consumivel=False, uso_em_batalha=False, preco=0, ativo=True,
        )
        pokemon = Pokemon(
            personagem=pessoa,
            forma_pokemon=db.session.scalar(select(FormaPokemon)),
            natureza=db.session.scalar(select(Natureza).where(Natureza.codigo == "docil")),
            item_equipado=item, pv_atual=10, localizacao="equipe", posicao=1, ativo=True,
        )
        db.session.add_all([pokemon, PersonagemItem(personagem=pessoa, item=item, quantidade=1)])
        db.session.commit()
        pokemon_id, item_id = pokemon.id, item.id

    resultado = app_db.test_cli_runner().invoke(
        args=["catalogo", "revisar-naturezas-importadas", "--aplicar"]
    )
    assert resultado.exit_code == 0, resultado.output
    assert "Coincidências não elegíveis, mantidas para revisão: 1" in resultado.output
    with app_db.app_context():
        assert db.session.get(Pokemon, pokemon_id).item_equipado_id == item_id
