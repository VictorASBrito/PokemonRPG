from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.models.db import HistoricoAlteracao, PokemonCapturavel


def _login_mestre(client_db) -> None:
    resposta = client_db.post("/login", data={"login": "mestre-db", "senha": "senha-db"})
    assert resposta.status_code == 302


def _login_jogador(client_db) -> None:
    resposta = client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"})
    assert resposta.status_code == 302


def test_mestre_adiciona_capturavel_e_jogador_visualiza_no_campo(app_db, client_db) -> None:
    _login_mestre(client_db)
    personagem_id = app_db.config["TEST_IDS"]["personagem"]
    forma_id = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]

    # Simula o contrato real do autocomplete usado pela tela do mestre.
    opcoes = client_db.get("/api/catalogo/formas?q=bulba").get_json()["itens"]
    opcao = next(item for item in opcoes if item["valor"] == "Bulbasaur")
    assert opcao["id"] == forma_id
    assert str(uuid.UUID(opcao["id"])) == forma_id
    formulario = client_db.get("/mestre/capturaveis").get_data(as_text=True)
    assert 'data-seletor-alvo="forma_id"' in formulario
    assert 'capturaveis-052' in formulario

    resposta = client_db.post(
        "/mestre/capturaveis",
        data={
            "forma_id": opcao["id"],
            "forma_nome": opcao["valor"],
            "encontrado_por_personagem_id": personagem_id,
        },
    )
    assert resposta.status_code == 302

    with app_db.app_context():
        capturavel = db.session.execute(select(PokemonCapturavel)).scalar_one()
        assert capturavel.ordem == 1
        assert str(capturavel.forma_pokemon_id) == forma_id
        historico = db.session.execute(
            select(HistoricoAlteracao).where(
                HistoricoAlteracao.entidade == "pokemon_capturavel",
                HistoricoAlteracao.registro_id == capturavel.id,
            )
        ).scalar_one()
        assert historico.acao == "criar"
        assert historico.dados_anteriores is None
        assert historico.dados_novos["forma"] == "Bulbasaur"
        assert historico.dados_novos["encontrado_por"] == "Bartz"

    client_db.post("/logout")
    _login_jogador(client_db)
    pagina = client_db.get("/jogador/capturaveis")
    texto = pagina.get_data(as_text=True)
    assert pagina.status_code == 200
    assert "Pokémon capturáveis em campo" in texto
    assert "Bulbasaur" in texto
    assert "Grama" in texto
    assert "Encontrado por Bartz" in texto


def test_limite_de_quinze_capturaveis_e_respeitado(app_db, client_db) -> None:
    _login_mestre(client_db)
    personagem_id = app_db.config["TEST_IDS"]["personagem"]
    forma_ids = list(app_db.config["TEST_IDS"]["formas"].values())

    with app_db.app_context():
        for indice in range(15):
            db.session.add(
                PokemonCapturavel(
                    campanha_id=uuid.UUID(app_db.config["TEST_IDS"]["campanha"]),
                    forma_pokemon_id=uuid.UUID(forma_ids[indice % len(forma_ids)]),
                    encontrado_por_personagem_id=uuid.UUID(personagem_id),
                    ordem=indice + 1,
                    genero="♂",
                    ativo=True,
                )
            )
        db.session.commit()

    resposta = client_db.post(
        "/mestre/capturaveis",
        data={
            "forma_id": forma_ids[0],
            "forma_nome": "Bulbasaur",
            "encontrado_por_personagem_id": personagem_id,
        },
        follow_redirects=True,
    )
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "atingiu o limite de 15" in texto



def test_mestre_remove_capturavel_do_campo(app_db, client_db) -> None:
    _login_mestre(client_db)
    personagem_id = app_db.config["TEST_IDS"]["personagem"]
    forma_id = app_db.config["TEST_IDS"]["formas"]["charmander"]

    client_db.post(
        "/mestre/capturaveis",
        data={
            "forma_id": forma_id,
            "forma_nome": "Charmander",
            "encontrado_por_personagem_id": personagem_id,
        },
    )

    with app_db.app_context():
        capturavel = db.session.execute(select(PokemonCapturavel)).scalar_one()
        capturavel_id = str(capturavel.id)

    resposta = client_db.post(f"/mestre/capturaveis/{capturavel_id}/remover", follow_redirects=True)
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "removido do campo" in texto

    with app_db.app_context():
        capturavel = db.session.get(PokemonCapturavel, uuid.UUID(capturavel_id))
        assert capturavel is not None
        assert capturavel.ativo is False
        assert capturavel.ordem is None
        eventos = list(
            db.session.execute(
                select(HistoricoAlteracao)
                .where(
                    HistoricoAlteracao.entidade == "pokemon_capturavel",
                    HistoricoAlteracao.registro_id == capturavel.id,
                )
                .order_by(HistoricoAlteracao.criado_em)
            ).scalars()
        )
        assert {item.acao for item in eventos} == {"criar", "remover"}
        remocao = next(item for item in eventos if item.acao == "remover")
        assert remocao.dados_anteriores["forma"] == "Charmander"
        assert remocao.dados_anteriores["ordem_anterior"] == 1
        assert remocao.dados_novos is None

    client_db.post("/logout")
    _login_jogador(client_db)
    pagina = client_db.get("/jogador/capturaveis").get_data(as_text=True)
    assert "Nenhum Pokémon capturável no momento" in pagina


def test_capturavel_aceita_formato_antigo_do_autocomplete(app_db, client_db) -> None:
    _login_mestre(client_db)
    personagem_id = app_db.config["TEST_IDS"]["personagem"]
    # A versão anterior enviava "Bulbasaur" no campo que deveria ser UUID.
    resposta = client_db.post(
        "/mestre/capturaveis",
        data={
            "forma_id": "Bulbasaur",
            "forma_nome": "Bulbasaur",
            "encontrado_por_personagem_id": personagem_id,
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "Pokémon capturável adicionado ao campo." in resposta.get_data(as_text=True)
    with app_db.app_context():
        capturavel = db.session.execute(select(PokemonCapturavel)).scalar_one()
        assert str(capturavel.forma_pokemon_id) == app_db.config["TEST_IDS"]["formas"]["bulbasaur"]


def test_capturavel_rejeita_forma_id_incorreto(app_db, client_db) -> None:
    _login_mestre(client_db)
    resposta = client_db.post(
        "/mestre/capturaveis",
        data={
            "forma_id": "outra-forma",
            "forma_nome": "Bulbasaur",
            "encontrado_por_personagem_id": app_db.config["TEST_IDS"]["personagem"],
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "Selecione uma espécie válida no catálogo." in resposta.get_data(as_text=True)
    with app_db.app_context():
        assert db.session.execute(select(PokemonCapturavel)).scalars().first() is None


def test_remover_com_dez_capturaveis_reordena_sem_violacao_unique(app_db, client_db) -> None:
    """Regressão: UPDATE em lote não pode ocupar posições ainda em uso."""
    _login_mestre(client_db)
    ids = app_db.config["TEST_IDS"]
    forma_ids = list(ids["formas"].values())
    with app_db.app_context():
        capturaveis = [
            PokemonCapturavel(
                campanha_id=uuid.UUID(ids["campanha"]),
                forma_pokemon_id=uuid.UUID(forma_ids[indice % len(forma_ids)]),
                encontrado_por_personagem_id=uuid.UUID(ids["personagem"]),
                ordem=indice + 1,
                genero="♀",
                ativo=True,
            )
            for indice in range(10)
        ]
        db.session.add_all(capturaveis)
        db.session.commit()
        id_removido = str(capturaveis[4].id)  # Remove o 5º de 10.
        ids_restantes = [str(item.id) for item in capturaveis if str(item.id) != id_removido]

    resposta = client_db.post(
        f"/mestre/capturaveis/{id_removido}/remover", follow_redirects=True
    )
    assert resposta.status_code == 200
    assert "Pokémon capturável removido do campo." in resposta.get_data(as_text=True)

    with app_db.app_context():
        todos = list(db.session.execute(select(PokemonCapturavel)).scalars())
        ativo = sorted((item for item in todos if item.ativo), key=lambda item: item.ordem)
        assert len(ativo) == 9
        assert [item.ordem for item in ativo] == list(range(1, 10))
        assert [str(item.id) for item in ativo] == ids_restantes
        removido = db.session.get(PokemonCapturavel, uuid.UUID(id_removido))
        assert removido is not None
        assert not removido.ativo
        assert removido.ordem is None
        historico = db.session.execute(
            select(HistoricoAlteracao).where(
                HistoricoAlteracao.entidade == "pokemon_capturavel",
                HistoricoAlteracao.registro_id == removido.id,
            )
        ).scalar_one()
        assert historico.acao == "remover"
        assert historico.dados_anteriores["ordem_anterior"] == 5

    # Uma nova adição deve ocupar a vaga 10, mantendo o teto de 15.
    resposta = client_db.post(
        "/mestre/capturaveis",
        data={
            "forma_id": forma_ids[0],
            "forma_nome": "Bulbasaur",
            "encontrado_por_personagem_id": ids["personagem"],
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "Pokémon capturável adicionado ao campo." in resposta.get_data(as_text=True)
    with app_db.app_context():
        ordens = sorted(
            item.ordem
            for item in db.session.execute(select(PokemonCapturavel)).scalars()
            if item.ativo
        )
        assert ordens == list(range(1, 11))


def test_remover_primeiro_e_ultimo_capturavel_preserva_ordem(app_db, client_db) -> None:
    _login_mestre(client_db)
    ids = app_db.config["TEST_IDS"]
    forma_id = ids["formas"]["caterpie"]
    with app_db.app_context():
        itens = [
            PokemonCapturavel(
                campanha_id=uuid.UUID(ids["campanha"]),
                forma_pokemon_id=uuid.UUID(forma_id),
                encontrado_por_personagem_id=uuid.UUID(ids["personagem"]),
                ordem=indice + 1,
                ativo=True,
            )
            for indice in range(4)
        ]
        db.session.add_all(itens)
        db.session.commit()
        primeiro_id = str(itens[0].id)
        ultimo_id = str(itens[-1].id)

    for alvo, esperadas in ((primeiro_id, [1, 2, 3]), (ultimo_id, [1, 2])):
        resposta = client_db.post(f"/mestre/capturaveis/{alvo}/remover", follow_redirects=True)
        assert resposta.status_code == 200
        assert "Pokémon capturável removido do campo." in resposta.get_data(as_text=True)
        with app_db.app_context():
            ordens = sorted(
                item.ordem
                for item in db.session.execute(select(PokemonCapturavel)).scalars()
                if item.ativo
            )
            assert ordens == esperadas
