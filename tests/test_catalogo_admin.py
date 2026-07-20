from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    EspeciePokemon,
    FormaPokemon,
    HistoricoAlteracao,
    TipoPokemon,
)


def _login_mestre(client_db) -> None:
    resposta = client_db.post(
        "/login",
        data={"login": "mestre-db", "senha": "senha-db"},
    )
    assert resposta.status_code == 302


def _dados_forma(tipo_id: str) -> dict[str, str]:
    return {
        "nova_especie": "1",
        "especie_nome": "Dracolar",
        "especie_codigo": "dracolar",
        "numero": "1001",
        "geracao": "9",
        "especie_personalizada": "1",
        "especie_descricao": "Pokémon criado para Ankar.",
        "forma_nome": "Dracolar",
        "forma_codigo": "dracolar",
        "categoria": "personalizada",
        "tipo_primario_id": tipo_id,
        "tipo_secundario_id": "",
        "imagem_url": "https://img/dracolar.png",
        "imagem_shiny_url": "https://img/dracolar-shiny.png",
        "atributo_pv": "60",
        "atributo_ataque": "9",
        "atributo_defesa": "8",
        "atributo_ataque_especial": "10",
        "atributo_defesa_especial": "8",
        "atributo_velocidade": "7",
    }


def test_catalogo_exige_perfil_mestre(client_db) -> None:
    assert client_db.get("/mestre/catalogo").status_code == 302
    assert client_db.post(
        "/login", data={"login": "bartz-db", "senha": "abc123"}
    ).status_code == 302
    resposta = client_db.get("/mestre/catalogo")
    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/")


def test_mestre_cria_edita_duplica_e_desativa_forma(app_db, client_db) -> None:
    _login_mestre(client_db)
    pagina_nova = client_db.get("/mestre/catalogo/pokemons/novo")
    assert pagina_nova.status_code == 200
    assert "Nova espécie ou forma" in pagina_nova.get_data(as_text=True)
    with app_db.app_context():
        tipo = db.session.execute(
            select(TipoPokemon).where(TipoPokemon.codigo == "fogo")
        ).scalar_one()
        tipo_id = str(tipo.id)

    resposta = client_db.post(
        "/mestre/catalogo/pokemons/novo",
        data=_dados_forma(tipo_id),
    )
    assert resposta.status_code == 302
    assert "/mestre/catalogo/pokemons/" in resposta.headers["Location"]

    with app_db.app_context():
        forma = db.session.execute(
            select(FormaPokemon).where(FormaPokemon.codigo == "dracolar")
        ).scalar_one()
        assert forma.especie.codigo == "dracolar"
        assert forma.especie.personalizada is True
        assert forma.categoria == "personalizada"
        assert forma.tipos[0].tipo.codigo == "fogo"
        assert {
            item.atributo.codigo: int(item.valor_base)
            for item in forma.atributos_base
        }["ataque_especial"] == 10
        forma_id = str(forma.id)
        assert db.session.execute(
            select(HistoricoAlteracao).where(
                HistoricoAlteracao.entidade == "forma_pokemon",
                HistoricoAlteracao.registro_id == forma.id,
            )
        ).scalar_one_or_none() is not None

    pagina_edicao = client_db.get(f"/mestre/catalogo/pokemons/{forma_id}/editar")
    assert pagina_edicao.status_code == 200
    assert "Dracolar" in pagina_edicao.get_data(as_text=True)

    dados_edicao = _dados_forma(tipo_id)
    dados_edicao.pop("nova_especie")
    dados_edicao.update(
        {
            "especie_nome": "Dracolar",
            "especie_codigo": "dracolar",
            "especie_ativa": "1",
            "forma_nome": "Dracolar Ankar",
            "forma_codigo": "dracolar-ankar",
            "atributo_ataque": "11",
        }
    )
    resposta = client_db.post(
        f"/mestre/catalogo/pokemons/{forma_id}/editar",
        data=dados_edicao,
    )
    assert resposta.status_code == 302

    resposta = client_db.post(f"/mestre/catalogo/pokemons/{forma_id}/duplicar")
    assert resposta.status_code == 302

    with app_db.app_context():
        forma = db.session.get(FormaPokemon, forma.id)
        assert forma is not None
        assert forma.nome == "Dracolar Ankar"
        copia = db.session.execute(
            select(FormaPokemon).where(FormaPokemon.codigo == "dracolar-ankar-copia")
        ).scalar_one()
        assert copia.ativo is False
        assert copia.especie_id == forma.especie_id
        assert len(copia.atributos_base) == len(forma.atributos_base)

    resposta = client_db.post(
        f"/mestre/catalogo/pokemons/{forma_id}/atividade",
        data={"ativo": "0"},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        forma = db.session.get(FormaPokemon, forma.id)
        assert forma is not None and forma.ativo is False


def test_pesquisa_e_simulacao_do_catalogo(app_db, client_db) -> None:
    _login_mestre(client_db)
    resposta = client_db.get("/mestre/catalogo/pokemons?q=Charmander")
    assert resposta.status_code == 200
    assert "Charmander" in resposta.get_data(as_text=True)

    resposta = client_db.post(
        "/mestre/catalogo/pokemons/simular",
        json={
            "nivel": 10,
            "shiny": True,
            "atributos": {
                "pv": 39,
                "ataque": 5,
                "defesa": 4,
                "ataque_especial": 6,
                "defesa_especial": 5,
                "velocidade": 7,
            },
        },
    )
    assert resposta.status_code == 200
    atributos = resposta.get_json()["atributos"]
    assert atributos["ataque_especial"] > atributos["defesa_especial"]
    assert atributos["pv"] > 39


def test_comando_catalogo_verificar(app_db) -> None:
    runner = app_db.test_cli_runner()
    resposta = runner.invoke(args=["catalogo", "verificar"])
    assert resposta.exit_code == 0, resposta.output
    assert "Catálogo de espécies e formas está consistente" in resposta.output
