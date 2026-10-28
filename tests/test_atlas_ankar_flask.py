"""Executar em ambiente com Flask/SQLAlchemy. Reutiliza fixture app_db existente."""
from __future__ import annotations


def test_atlas_exige_login(app_db):
    resp = app_db.test_client().get('/regiao/ankar')
    assert resp.status_code in (302, 303)
    assert '/login' in resp.headers['Location']


def test_mestre_abre_atlas_e_rota(app_db):
    with app_db.test_client() as c:
        login = c.post('/login', data={'login':'mestre-db','senha':'senha-db'})
        assert login.status_code in (302, 303)
        resposta = c.get('/regiao/ankar')
        assert resposta.status_code == 200
        assert b'Explore a regi' in resposta.data
        detalhe = c.get('/regiao/ankar/rota-1')
        assert detalhe.status_code == 200
        assert b'Tentacool' in detalhe.data
        assert b'60-75' in detalhe.data
        assert c.get('/regiao/ankar/rota-9999').status_code == 404
