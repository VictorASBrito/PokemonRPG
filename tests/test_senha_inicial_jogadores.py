"""Proteção dos novos acessos externos com senha provisória 12345."""

from sqlalchemy import select

from app.extensions import db
from app.models.db import Usuario
from app.services.senha_service import gerar_hash_senha, verificar_senha


def test_senha_temporaria_exige_troca_antes_da_ficha(app_db, client_db):
    with app_db.app_context():
        usuario = db.session.execute(select(Usuario).where(Usuario.login == "bartz-db")).scalar_one()
        usuario.senha_hash = gerar_hash_senha("12345")
        db.session.commit()

    login = client_db.post("/login", data={"login": "bartz-db", "senha": "12345"})
    assert login.status_code == 302
    assert "/conta/senha" in login.headers["Location"]
    assert client_db.get("/jogador/dashboard").status_code == 302

    pagina = client_db.get("/conta/senha")
    assert pagina.status_code == 200
    with client_db.session_transaction() as sessao:
        token = sessao["troca_senha_token"]

    resposta = client_db.post("/conta/senha", data={
        "csrf_token": token,
        "senha_atual": "12345",
        "senha_nova": "MinhaNovaSenhaSegura987",
        "confirmar_senha": "MinhaNovaSenhaSegura987",
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        usuario = db.session.execute(select(Usuario).where(Usuario.login == "bartz-db")).scalar_one()
        assert verificar_senha("MinhaNovaSenhaSegura987", usuario.senha_hash)
