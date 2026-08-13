from __future__ import annotations

import base64
import io
import uuid
from pathlib import Path

from sqlalchemy import select

from app.extensions import db
from app.models.db import CategoriaItem, EspeciePokemon, FormaPokemon, Item, TipoPokemon


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
)


def _login_mestre(client) -> None:
    resposta = client.post("/login", data={"login": "mestre-db", "senha": "senha-db"})
    assert resposta.status_code == 302


def _arquivo_local(app, url: str) -> Path:
    relativo = url.split("/static/uploads/", 1)[1]
    return Path(app.config["UPLOAD_IMAGENS_DIR"]) / relativo


def _dados_forma_existente(especie_id: str, tipo_id: str) -> dict[str, str]:
    return {
        "especie_id": especie_id,
        "forma_nome": "Charmander Retrato",
        "forma_codigo": "charmander-retrato",
        "categoria": "alternativa",
        "tipo_primario_id": tipo_id,
        "tipo_secundario_id": "",
        "atributo_pv": "39",
        "atributo_ataque": "5",
        "atributo_defesa": "4",
        "atributo_ataque_especial": "6",
        "atributo_defesa_especial": "5",
        "atributo_velocidade": "7",
    }


def test_upload_de_imagem_para_item_e_forma_pokemon(app_db, client_db) -> None:
    _login_mestre(client_db)
    with app_db.app_context():
        categoria = db.session.execute(
            select(CategoriaItem).where(CategoriaItem.codigo == "bagas")
        ).scalar_one()
        especie = db.session.execute(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "charmander")
        ).scalar_one()
        tipo = db.session.execute(
            select(TipoPokemon).where(TipoPokemon.codigo == "fogo")
        ).scalar_one()
        categoria_id = str(categoria.id)
        especie_id = str(especie.id)
        tipo_id = str(tipo.id)

    resposta = client_db.post(
        "/mestre/catalogo/itens/novo",
        data={
            "nome": "Pedra Ilustrada",
            "codigo": "pedra-ilustrada",
            "categoria_id": categoria_id,
            "preco": "10",
            "personalizado": "1",
            "efeitos_json": "{}",
            "imagem_arquivo": (io.BytesIO(PNG_1X1), "item.png"),
        },
    )
    assert resposta.status_code == 302

    with app_db.app_context():
        item = db.session.execute(
            select(Item).where(Item.codigo == "pedra-ilustrada")
        ).scalar_one()
        assert item.imagem_url is not None
        assert item.imagem_url.startswith("/static/uploads/itens/")
        assert _arquivo_local(app_db, item.imagem_url).is_file()

    dados_forma = _dados_forma_existente(especie_id, tipo_id)
    dados_forma.update(
        {
            "imagem_arquivo": (io.BytesIO(PNG_1X1), "normal.png"),
            "imagem_shiny_arquivo": (io.BytesIO(PNG_1X1), "shiny.png"),
        }
    )
    resposta = client_db.post("/mestre/catalogo/pokemons/novo", data=dados_forma)
    assert resposta.status_code == 302

    with app_db.app_context():
        forma = db.session.execute(
            select(FormaPokemon).where(FormaPokemon.codigo == "charmander-retrato")
        ).scalar_one()
        assert forma.imagem_url and forma.imagem_url.startswith("/static/uploads/pokemons/")
        assert forma.imagem_shiny_url and forma.imagem_shiny_url.startswith(
            "/static/uploads/pokemons/"
        )
        assert _arquivo_local(app_db, forma.imagem_url).is_file()
        assert _arquivo_local(app_db, forma.imagem_shiny_url).is_file()

    runner = app_db.test_cli_runner()
    verificacao = runner.invoke(args=["midia", "verificar"])
    assert verificacao.exit_code == 0, verificacao.output
    assert "Referências de imagens locais estão consistentes" in verificacao.output


def test_upload_invalido_nao_cria_item_nem_arquivo(app_db, client_db) -> None:
    _login_mestre(client_db)
    with app_db.app_context():
        categoria = db.session.execute(
            select(CategoriaItem).where(CategoriaItem.codigo == "bagas")
        ).scalar_one()
        categoria_id = str(categoria.id)

    resposta = client_db.post(
        "/mestre/catalogo/itens/novo",
        data={
            "nome": "Arquivo falso",
            "codigo": "arquivo-falso",
            "categoria_id": categoria_id,
            "preco": "0",
            "efeitos_json": "{}",
            "imagem_arquivo": (io.BytesIO(b"isto nao e uma imagem"), "falso.png"),
        },
    )
    assert resposta.status_code == 200
    assert "Formato não suportado" in resposta.get_data(as_text=True)
    with app_db.app_context():
        assert db.session.execute(
            select(Item).where(Item.codigo == "arquivo-falso")
        ).scalar_one_or_none() is None
    pasta = Path(app_db.config["UPLOAD_IMAGENS_DIR"])
    assert not list(pasta.rglob("*.png"))


def test_substituicao_preserva_upload_compartilhado_por_duplicacao(app_db, client_db) -> None:
    _login_mestre(client_db)
    with app_db.app_context():
        categoria = db.session.execute(
            select(CategoriaItem).where(CategoriaItem.codigo == "bagas")
        ).scalar_one()
        categoria_id = str(categoria.id)

    resposta = client_db.post(
        "/mestre/catalogo/itens/novo",
        data={
            "nome": "Item com retrato",
            "codigo": "item-com-retrato",
            "categoria_id": categoria_id,
            "preco": "1",
            "personalizado": "1",
            "efeitos_json": "{}",
            "imagem_arquivo": (io.BytesIO(PNG_1X1), "primeira.png"),
        },
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        item = db.session.execute(
            select(Item).where(Item.codigo == "item-com-retrato")
        ).scalar_one()
        item_id = str(item.id)
        url_original = item.imagem_url
        assert url_original
        arquivo_original = _arquivo_local(app_db, url_original)
        assert arquivo_original.is_file()

    assert client_db.post(f"/mestre/catalogo/itens/{item_id}/duplicar").status_code == 302

    resposta = client_db.post(
        f"/mestre/catalogo/itens/{item_id}/editar",
        data={
            "nome": "Item com retrato",
            "codigo": "item-com-retrato",
            "categoria_id": categoria_id,
            "preco": "1",
            "personalizado": "1",
            "efeitos_json": "{}",
            "imagem_url": url_original,
            "imagem_arquivo": (io.BytesIO(PNG_1X1), "segunda.png"),
        },
    )
    assert resposta.status_code == 302

    with app_db.app_context():
        item = db.session.get(Item, item.id)
        copia = db.session.execute(
            select(Item).where(Item.codigo == "item-com-retrato-copia")
        ).scalar_one()
        assert item and item.imagem_url != url_original
        assert copia.imagem_url == url_original
        assert arquivo_original.is_file(), "A cópia ainda referencia a imagem original."
        assert _arquivo_local(app_db, item.imagem_url).is_file()


def test_jogador_pode_enviar_foto_do_perfil(app_db, client_db) -> None:
    resposta = client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"})
    assert resposta.status_code == 302

    resposta = client_db.post(
        "/jogador/ficha",
        data={
            "nome": "Bartz",
            "foto_url": "",
            "foto_arquivo": (io.BytesIO(PNG_1X1), "perfil.png"),
            "nivel": "48",
            "idade": "24",
            "genero": "Masculino",
            "origem": "Atleta",
            "classe": "Treinador(a)",
            "estilo_combate": "Agressivo",
            "numeros_shiny": "7",
            "pokedolares": "300",
            "pv_atual": "30",
            "atributo_fisico": "1",
            "atributo_destreza": "1",
            "atributo_saude": "3",
            "atributo_conhecimento": "1",
            "atributo_comunicacao": "1",
            "atributo_espirito": "1",
            "beneficios_habilidades": "",
            "anotacoes": "",
        },
    )
    assert resposta.status_code == 302

    from app.models.db import Personagem
    with app_db.app_context():
        personagem = db.session.get(Personagem, uuid.UUID(app_db.config["TEST_IDS"]["personagem"]))
        assert personagem is not None
        assert personagem.foto_url is not None
        assert personagem.foto_url.startswith("/static/uploads/perfis/")
        assert _arquivo_local(app_db, personagem.foto_url).is_file()

    dashboard = client_db.get("/jogador/dashboard")
    assert dashboard.status_code == 200
    assert "/static/uploads/perfis/" in dashboard.get_data(as_text=True)
