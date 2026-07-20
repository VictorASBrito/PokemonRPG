from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    Atributo,
    CategoriaGolpe,
    FormaPokemon,
    FormaPokemonGolpe,
    Golpe,
    HistoricoAlteracao,
    StatusCondicao,
    TipoPokemon,
)
from app.services.golpe_admin_service import efeitos_para_editor


def _login_mestre(client_db) -> None:
    resposta = client_db.post("/login", data={"login": "mestre-db", "senha": "senha-db"})
    assert resposta.status_code == 302


def _opcoes(app_db):
    with app_db.app_context():
        tipo = db.session.execute(select(TipoPokemon).where(TipoPokemon.codigo == "fogo")).scalar_one()
        categoria = db.session.execute(
            select(CategoriaGolpe).where(CategoriaGolpe.codigo == "especial")
        ).scalar_one()
        status = db.session.execute(
            select(StatusCondicao).where(StatusCondicao.codigo == "queimando")
        ).scalar_one()
        atributo = db.session.execute(
            select(Atributo).where(Atributo.codigo == "defesa_especial")
        ).scalar_one()
        return str(tipo.id), str(categoria.id), str(status.id), atributo.codigo


def _dados_golpe(app_db) -> dict[str, str]:
    tipo_id, categoria_id, status_id, atributo_codigo = _opcoes(app_db)
    efeitos = {
        "versao": 1,
        "efeitos": [
            {
                "tipo": "aplicar_status",
                "alvo": "oponente",
                "chance": 30,
                "status_id": status_id,
                "duracao": "3 turnos",
            },
            {
                "tipo": "alterar_atributo",
                "alvo": "oponente",
                "chance": 100,
                "atributo": atributo_codigo,
                "operacao": "percentual",
                "valor": -0.1,
            },
            {
                "tipo": "texto",
                "alvo": "oponente",
                "chance": 100,
                "texto": "As chamas iluminam o campo durante a cena.",
            },
        ],
    }
    return {
        "nome": "Explosão de Ankar",
        "codigo": "explosao-de-ankar",
        "tipo_id": tipo_id,
        "categoria_id": categoria_id,
        "expressao_dano": "6d6",
        "precisao": "90",
        "prioridade": "1",
        "descricao": "Uma técnica criada para a campanha.",
        "personalizado": "1",
        "efeitos_json": json.dumps(efeitos),
    }


def test_mestre_lista_cria_e_edita_golpe_com_efeitos(app_db, client_db) -> None:
    _login_mestre(client_db)
    pagina = client_db.get("/mestre/catalogo/golpes")
    assert pagina.status_code == 200
    assert "Ataque de Chamas" in pagina.get_data(as_text=True)

    pagina_nova = client_db.get("/mestre/catalogo/golpes/novo")
    assert pagina_nova.status_code == 200
    assert "Editor visual de efeitos" in pagina_nova.get_data(as_text=True)

    resposta = client_db.post("/mestre/catalogo/golpes/novo", data=_dados_golpe(app_db))
    assert resposta.status_code == 302
    assert "/mestre/catalogo/golpes/" in resposta.headers["Location"]

    with app_db.app_context():
        golpe = db.session.execute(
            select(Golpe).where(Golpe.codigo == "explosao-de-ankar")
        ).scalar_one()
        golpe_id = str(golpe.id)
        assert golpe.personalizado is True
        assert golpe.expressao_dano == "6d6"
        assert golpe.precisao == Decimal("90")
        assert len(golpe.efeitos["efeitos"]) == 3
        assert golpe.efeitos["efeitos"][1]["atributo"] == "defesa_especial"
        assert db.session.execute(
            select(HistoricoAlteracao).where(
                HistoricoAlteracao.entidade == "golpe",
                HistoricoAlteracao.registro_id == golpe.id,
            )
        ).scalar_one_or_none() is not None

    pagina_edicao = client_db.get(f"/mestre/catalogo/golpes/{golpe_id}/editar")
    corpo = pagina_edicao.get_data(as_text=True)
    assert pagina_edicao.status_code == 200
    assert "Explosão de Ankar" in corpo
    assert "As chamas iluminam" in corpo

    dados = _dados_golpe(app_db)
    dados.update(nome="Explosão Rubra de Ankar", precisao="95")
    resposta = client_db.post(f"/mestre/catalogo/golpes/{golpe_id}/editar", data=dados)
    assert resposta.status_code == 302
    with app_db.app_context():
        golpe = db.session.get(Golpe, golpe.id)
        assert golpe is not None
        assert golpe.nome == "Explosão Rubra de Ankar"
        assert golpe.precisao == Decimal("95")


def test_duplica_desativa_e_normaliza_efeito_textual(app_db, client_db) -> None:
    _login_mestre(client_db)
    with app_db.app_context():
        golpe = db.session.execute(select(Golpe).where(Golpe.codigo == "arranhao")).scalar_one()
        golpe.efeitos = {"texto": "Causa dano e assusta o alvo."}
        db.session.commit()
        golpe_id = str(golpe.id)
        assert efeitos_para_editor(golpe.efeitos) == [
            {"tipo": "texto", "texto": "Causa dano e assusta o alvo."}
        ]

    resposta = client_db.post(f"/mestre/catalogo/golpes/{golpe_id}/duplicar")
    assert resposta.status_code == 302
    with app_db.app_context():
        copia = db.session.execute(
            select(Golpe).where(Golpe.codigo == "arranhao-copia")
        ).scalar_one()
        assert copia.ativo is False
        assert copia.personalizado is True
        assert copia.efeitos == {"texto": "Causa dano e assusta o alvo."}
        copia_id = str(copia.id)

    resposta = client_db.post(
        f"/mestre/catalogo/golpes/{copia_id}/atividade",
        data={"ativo": "1"},
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        copia = db.session.get(Golpe, copia.id)
        assert copia is not None and copia.ativo is True


def test_vincula_atualiza_e_remove_golpe_de_forma(app_db, client_db) -> None:
    _login_mestre(client_db)
    with app_db.app_context():
        golpe = db.session.execute(
            select(Golpe).where(Golpe.codigo == "ataque-de-chamas")
        ).scalar_one()
        forma = db.session.execute(
            select(FormaPokemon).where(FormaPokemon.codigo == "charmander")
        ).scalar_one()
        golpe_id = str(golpe.id)
        forma_id = str(forma.id)

    resposta = client_db.post(
        f"/mestre/catalogo/golpes/{golpe_id}/vinculos",
        data={
            "forma_pokemon_id": forma_id,
            "metodo": "nivel",
            "nivel_requerido": "7",
            "observacoes": "Aprendido após treinamento.",
        },
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        vinculo = db.session.execute(
            select(FormaPokemonGolpe).where(
                FormaPokemonGolpe.forma_pokemon_id == forma.id,
                FormaPokemonGolpe.golpe_id == golpe.id,
                FormaPokemonGolpe.metodo == "nivel",
            )
        ).scalar_one()
        vinculo_id = str(vinculo.id)
        assert vinculo.nivel_requerido == 7

    resposta = client_db.post(
        f"/mestre/catalogo/golpes/{golpe_id}/vinculos",
        data={
            "vinculo_id": vinculo_id,
            "forma_pokemon_id": forma_id,
            "metodo": "nivel",
            "nivel_requerido": "12",
            "observacoes": "Rebalanceado.",
        },
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        vinculo = db.session.get(FormaPokemonGolpe, vinculo.id)
        assert vinculo is not None
        assert vinculo.nivel_requerido == 12
        assert vinculo.observacoes == "Rebalanceado."

    resposta = client_db.post(
        f"/mestre/catalogo/golpes/{golpe_id}/vinculos/{vinculo_id}/remover"
    )
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.get(FormaPokemonGolpe, vinculo.id) is None


def test_comando_catalogo_tambem_verifica_golpes(app_db) -> None:
    runner = app_db.test_cli_runner()
    resposta = runner.invoke(args=["catalogo", "verificar"])
    assert resposta.exit_code == 0, resposta.output
    assert "Catálogo de golpes está consistente" in resposta.output
