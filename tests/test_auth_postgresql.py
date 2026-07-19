from __future__ import annotations

import json
import shutil
from pathlib import Path

from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models.db import (
    Atributo,
    Campanha,
    CampanhaMembro,
    ConjuntoRegras,
    Personagem,
    PersonagemAtributo,
    Regra,
    RegraValor,
    Usuario,
)
from app.services.senha_service import gerar_hash_senha


def _app_banco(monkeypatch, tmp_path: Path):
    banco = tmp_path / "auth.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{banco}")
    app = create_app()

    origem = Path(__file__).resolve().parent.parent / "data"
    data_dir = tmp_path / "data"
    shutil.copytree(origem, data_dir)
    app.config.update(TESTING=True, SECRET_KEY="teste", DATA_DIR=data_dir)

    tabelas = [
        Usuario.__table__,
        Campanha.__table__,
        CampanhaMembro.__table__,
        Atributo.__table__,
        Personagem.__table__,
        PersonagemAtributo.__table__,
        Regra.__table__,
        ConjuntoRegras.__table__,
        RegraValor.__table__,
    ]
    with app.app_context():
        db.metadata.create_all(db.engine, tables=tabelas)
        campanha = Campanha(codigo="ankar", nome="Ankar", ativo=True)
        mestre = Usuario(
            login="mestre-db",
            nome="Mestre do Banco",
            senha_hash=gerar_hash_senha("senha-db"),
            perfil="mestre",
            ativo=True,
        )
        db.session.add_all([campanha, mestre])
        db.session.commit()
    return app, data_dir


def test_login_usa_postgresql_em_vez_do_json(monkeypatch, tmp_path: Path) -> None:
    app, _ = _app_banco(monkeypatch, tmp_path)
    client = app.test_client()

    resposta_errada = client.post(
        "/login",
        data={"login": "mestre-db", "senha": "mestre123"},
    )
    assert resposta_errada.status_code == 401

    resposta = client.post(
        "/login",
        data={"login": "mestre-db", "senha": "senha-db"},
    )
    assert resposta.status_code == 302
    with client.session_transaction() as sessao:
        assert sessao["nome"] == "Mestre do Banco"
        assert sessao["perfil"] == "mestre"


def test_cadastro_cria_usuario_personagem_e_compatibilidade_json(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app, data_dir = _app_banco(monkeypatch, tmp_path)
    client = app.test_client()
    assert client.post(
        "/login",
        data={"login": "mestre-db", "senha": "senha-db"},
    ).status_code == 302

    resposta = client.post(
        "/mestre/jogadores/novo",
        data={
            "nome": "Victor",
            "login": "victor-db",
            "senha": "abc123",
            "confirmar_senha": "abc123",
        },
    )
    assert resposta.status_code == 302

    with app.app_context():
        usuario = db.session.execute(
            select(Usuario).where(Usuario.login == "victor-db")
        ).scalar_one()
        personagem = db.session.execute(
            select(Personagem).where(Personagem.usuario_id == usuario.id)
        ).scalar_one()
        membro = db.session.execute(
            select(CampanhaMembro).where(CampanhaMembro.usuario_id == usuario.id)
        ).scalar_one()

        assert usuario.perfil == "jogador"
        assert personagem.nome == "Victor"
        assert membro.papel == "jogador"

    usuarios_json = json.loads(
        (data_dir / "usuarios.json").read_text(encoding="utf-8")
    )
    legado = next(
        item for item in usuarios_json["usuarios"] if item["login"] == "victor-db"
    )
    arquivo_ficha = (
        data_dir
        / "campanhas"
        / "ankar"
        / "jogadores"
        / f"{legado['jogador_id']}.json"
    )
    assert arquivo_ficha.exists()
