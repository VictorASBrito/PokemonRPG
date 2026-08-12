from __future__ import annotations

import json
import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    Campanha,
    CampanhaMembro,
    CategoriaItem,
    FormaPokemon,
    HistoricoAlteracao,
    Item,
    Personagem,
    PersonagemItem,
    Pokemon,
    Usuario,
)
from app.services.senha_service import gerar_hash_senha


def _login_mestre(client) -> None:
    resposta = client.post("/login", data={"login": "mestre-db", "senha": "senha-db"})
    assert resposta.status_code == 302


def test_catalogo_cria_edita_duplica_e_desativa_item(app_db, client_db) -> None:
    _login_mestre(client_db)
    pagina = client_db.get("/mestre/catalogo/itens")
    assert pagina.status_code == 200
    assert "Baga Laranja" in pagina.get_data(as_text=True)

    efeitos = {
        "versao": 1,
        "efeitos": [
            {
                "tipo": "recuperar_pv",
                "alvo": "pokemon",
                "operacao": "fixo",
                "valor": 50,
            },
            {
                "tipo": "texto",
                "alvo": "pokemon",
                "texto": "Só pode ser usada uma vez por cena.",
            },
        ],
    }
    resposta = client_db.post(
        "/mestre/catalogo/itens/novo",
        data={
            "nome": "Super Poção de Ankar",
            "codigo": "super-pocao-ankar",
            "nova_categoria": "Cura especial",
            "preco": "700",
            "descricao": "Recupera energia de um Pokémon.",
            "imagem_url": "https://img/super-pocao.png",
            "consumivel": "1",
            "uso_em_batalha": "1",
            "personalizado": "1",
            "efeitos_json": json.dumps(efeitos),
        },
    )
    assert resposta.status_code == 302
    assert "/mestre/catalogo/itens/" in resposta.headers["Location"]

    with app_db.app_context():
        item = db.session.execute(
            select(Item).where(Item.codigo == "super-pocao-ankar")
        ).scalar_one()
        item_id = str(item.id)
        assert item.preco == 700
        assert item.consumivel is True
        assert item.equipavel is False
        assert item.uso_em_batalha is True
        assert item.categoria.nome == "Cura especial"
        assert len(item.efeitos["efeitos"]) == 2
        assert db.session.execute(
            select(HistoricoAlteracao).where(
                HistoricoAlteracao.entidade == "item",
                HistoricoAlteracao.registro_id == item.id,
            )
        ).scalar_one_or_none() is not None

    edicao = client_db.get(f"/mestre/catalogo/itens/{item_id}/editar")
    texto = edicao.get_data(as_text=True)
    assert edicao.status_code == 200
    assert "Editor visual de efeitos" in texto
    assert "recuperar_pv" in texto
    assert "efeitos-item-iniciais" in texto

    resposta = client_db.post(f"/mestre/catalogo/itens/{item_id}/duplicar")
    assert resposta.status_code == 302
    with app_db.app_context():
        copia = db.session.execute(
            select(Item).where(Item.codigo == "super-pocao-ankar-copia")
        ).scalar_one()
        assert copia.ativo is False
        assert copia.personalizado is True
        copia_id = str(copia.id)

    resposta = client_db.post(
        f"/mestre/catalogo/itens/{copia_id}/atividade",
        data={"ativo": "1"},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        copia = db.session.get(Item, copia.id)
        assert copia is not None and copia.ativo is True


def test_fluxo_inventario_adiciona_equipa_usa_desequipa_e_transfere(app_db, client_db) -> None:
    with app_db.app_context():
        campanha = db.session.execute(select(Campanha).where(Campanha.codigo == "ankar")).scalar_one()
        usuario_destino = Usuario(
            login="destino-db",
            nome="Priscilla",
            senha_hash=gerar_hash_senha("abc123"),
            perfil="jogador",
            ativo=True,
        )
        destino = Personagem(
            usuario=usuario_destino,
            campanha=campanha,
            nome="Priscilla",
            nivel=48,
            pv_atual=10,
            ativo=True,
        )
        db.session.add_all(
            [
                usuario_destino,
                destino,
                CampanhaMembro(campanha=campanha, usuario=usuario_destino, papel="jogador"),
            ]
        )
        forma = db.session.execute(
            select(FormaPokemon).where(FormaPokemon.codigo == "charmander")
        ).scalar_one()
        personagem = db.session.get(Personagem, uuid.UUID(app_db.config["TEST_IDS"]["personagem"]))
        pokemon = Pokemon(
            personagem=personagem,
            forma_pokemon=forma,
            apelido="Brasinha",
            localizacao="box",
            posicao=1,
            pv_atual=20,
            ativo=True,
        )
        db.session.add(pokemon)
        db.session.commit()
        personagem_id = str(personagem.id)
        destino_id = str(destino.id)
        pokemon_id = str(pokemon.id)
        item = db.session.execute(select(Item).where(Item.codigo == "baga-laranja")).scalar_one()
        item_id = str(item.id)

    _login_mestre(client_db)

    resposta = client_db.post(
        f"/mestre/jogadores/{personagem_id}/inventario/adicionar",
        data={"item_id": item_id, "quantidade": "3"},
    )
    assert resposta.status_code == 302
    pagina = client_db.get(f"/mestre/jogadores/{personagem_id}/inventario")
    texto = pagina.get_data(as_text=True)
    assert pagina.status_code == 200
    assert "Baga Laranja" in texto
    assert "Itens, quantidades, transferências" in texto

    resposta = client_db.post(
        f"/mestre/jogadores/{personagem_id}/inventario/equipar",
        data={"item_id": item_id, "pokemon_id": pokemon_id},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, pokemon.id)
        registro = db.session.execute(
            select(PersonagemItem).where(
                PersonagemItem.personagem_id == personagem.id,
                PersonagemItem.item_id == item.id,
            )
        ).scalar_one()
        assert pokemon.item_equipado_id == item.id
        assert registro.quantidade == 2

    resposta = client_db.post(
        f"/mestre/jogadores/{personagem_id}/inventario/usar",
        data={"item_id": item_id, "quantidade": "1"},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        registro = db.session.execute(
            select(PersonagemItem).where(
                PersonagemItem.personagem_id == personagem.id,
                PersonagemItem.item_id == item.id,
            )
        ).scalar_one()
        assert registro.quantidade == 1

    resposta = client_db.post(
        f"/mestre/jogadores/{personagem_id}/inventario/desequipar",
        data={"pokemon_id": pokemon_id},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, pokemon.id)
        registro = db.session.execute(
            select(PersonagemItem).where(
                PersonagemItem.personagem_id == personagem.id,
                PersonagemItem.item_id == item.id,
            )
        ).scalar_one()
        assert pokemon.item_equipado_id is None
        assert registro.quantidade == 2

    resposta = client_db.post(
        f"/mestre/jogadores/{personagem_id}/inventario/transferir",
        data={
            "item_id": item_id,
            "personagem_destino_id": destino_id,
            "quantidade": "1",
        },
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        quantidades = {
            str(registro.personagem_id): registro.quantidade
            for registro in db.session.execute(
                select(PersonagemItem).where(PersonagemItem.item_id == item.id)
            ).scalars()
        }
        assert quantidades[personagem_id] == 1
        assert quantidades[destino_id] == 1

    runner = app_db.test_cli_runner()
    verificacao = runner.invoke(args=["inventario", "verificar"])
    assert verificacao.exit_code == 0, verificacao.output
    assert "Itens, inventários e equipamentos estão consistentes" in verificacao.output


def test_jogador_nao_pode_adicionar_quantidade_livremente(app_db, client_db) -> None:
    resposta = client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"})
    assert resposta.status_code == 302
    personagem_id = app_db.config["TEST_IDS"]["personagem"]
    with app_db.app_context():
        item = db.session.execute(select(Item).where(Item.codigo == "baga-laranja")).scalar_one()
        item_id = str(item.id)

    resposta = client_db.post(
        f"/mestre/jogadores/{personagem_id}/inventario/adicionar",
        data={"item_id": item_id, "quantidade": "99"},
    )
    assert resposta.status_code == 302
    assert resposta.headers["Location"] in {"/", "/login", "/jogador/dashboard"}
    with app_db.app_context():
        total = db.session.scalar(
            select(PersonagemItem.quantidade).where(
                PersonagemItem.personagem_id == uuid.UUID(personagem_id),
                PersonagemItem.item_id == item.id,
            )
        )
        assert total is None


def test_mestre_nao_acessa_inventario_de_outra_campanha(app_db, client_db) -> None:
    with app_db.app_context():
        outra_campanha = Campanha(
            codigo="outra-campanha",
            nome="Outra campanha",
            ativo=True,
        )
        outro_usuario = Usuario(
            login="outro-jogador-db",
            nome="Outro jogador",
            senha_hash=gerar_hash_senha("abc123"),
            perfil="jogador",
            ativo=True,
        )
        outro_personagem = Personagem(
            usuario=outro_usuario,
            campanha=outra_campanha,
            nome="Visitante",
            nivel=10,
            pv_atual=10,
            ativo=True,
        )
        db.session.add_all(
            [
                outra_campanha,
                outro_usuario,
                outro_personagem,
                CampanhaMembro(
                    campanha=outra_campanha,
                    usuario=outro_usuario,
                    papel="jogador",
                ),
            ]
        )
        db.session.commit()
        personagem_id = str(outro_personagem.id)
        item = db.session.execute(
            select(Item).where(Item.codigo == "baga-laranja")
        ).scalar_one()
        item_id = str(item.id)

    _login_mestre(client_db)

    pagina = client_db.get(f"/mestre/jogadores/{personagem_id}/inventario")
    assert pagina.status_code == 302
    assert pagina.headers["Location"].endswith("/mestre/jogadores")

    resposta = client_db.post(
        f"/mestre/jogadores/{personagem_id}/inventario/adicionar",
        data={"item_id": item_id, "quantidade": "5"},
    )
    assert resposta.status_code == 302

    with app_db.app_context():
        registro = db.session.execute(
            select(PersonagemItem).where(
                PersonagemItem.personagem_id == uuid.UUID(personagem_id),
                PersonagemItem.item_id == uuid.UUID(item_id),
            )
        ).scalar_one_or_none()
        assert registro is None
