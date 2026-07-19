from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models.db import CampanhaMembro, Personagem, Usuario


def test_login_usa_postgresql(client_db) -> None:
    resposta_errada = client_db.post(
        "/login",
        data={"login": "mestre-db", "senha": "mestre123"},
    )
    assert resposta_errada.status_code == 401

    resposta = client_db.post(
        "/login",
        data={"login": "mestre-db", "senha": "senha-db"},
    )
    assert resposta.status_code == 302
    with client_db.session_transaction() as sessao:
        assert sessao["nome"] == "Mestre do Banco"
        assert sessao["perfil"] == "mestre"
        assert "jogador_id" not in sessao


def test_cadastro_cria_usuario_e_personagem_somente_no_banco(app_db, client_db) -> None:
    assert client_db.post(
        "/login",
        data={"login": "mestre-db", "senha": "senha-db"},
    ).status_code == 302

    resposta = client_db.post(
        "/mestre/jogadores/novo",
        data={
            "nome": "Claire",
            "login": "claire-db",
            "senha": "abc123",
            "confirmar_senha": "abc123",
        },
    )
    assert resposta.status_code == 302

    with app_db.app_context():
        usuario = db.session.execute(
            select(Usuario).where(Usuario.login == "claire-db")
        ).scalar_one()
        personagem = db.session.execute(
            select(Personagem).where(Personagem.usuario_id == usuario.id)
        ).scalar_one()
        membro = db.session.execute(
            select(CampanhaMembro).where(CampanhaMembro.usuario_id == usuario.id)
        ).scalar_one()

        assert usuario.perfil == "jogador"
        assert personagem.nome == "Claire"
        assert membro.papel == "jogador"
        assert str(personagem.id) in resposta.headers["Location"]
