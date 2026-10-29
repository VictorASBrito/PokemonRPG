"""Integração: requer Flask, PostgreSQL/SQLite fixture app_db do PokemonRPG."""
from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models.db import Campanha, CampanhaMembro, Personagem, Usuario
from app.services.senha_service import gerar_hash_senha


def test_slot_mestre_abre_form_e_envia_post_para_login(app_db):
    cliente = app_db.test_client()
    resposta = cliente.get('/login/coringa')
    assert resposta.status_code == 200
    pagina = resposta.get_data(as_text=True)
    assert 'action="/login"' in pagina
    resposta = cliente.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'})
    assert resposta.status_code in (302, 303)
    with cliente.session_transaction() as sessao:
        assert sessao.get('perfil') == 'mestre'


def test_mestre_pode_trocar_para_teste_mesmo_com_sessao_ativa(app_db):
    with app_db.app_context():
        campanha = db.session.execute(select(Campanha).where(Campanha.codigo == 'ankar')).scalar_one()
        usuario = Usuario(login='teste-db', nome='Conta Teste', perfil='tester',
                          senha_hash=gerar_hash_senha('senha-db-teste'), ativo=True)
        personagem = Personagem(usuario=usuario, campanha=campanha, nome='Treinador Teste', ativo=True)
        db.session.add_all([usuario, personagem,
                            CampanhaMembro(usuario=usuario, campanha=campanha, papel='jogador')])
        db.session.commit()
        id_teste = str(usuario.id)
    cliente = app_db.test_client()
    assert cliente.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'}).status_code in (302, 303)
    assert cliente.get('/login/coringa').status_code == 200
    resposta = cliente.post('/login', data={'login': 'teste-db', 'senha': 'senha-db-teste'})
    assert resposta.status_code in (302, 303)
    with cliente.session_transaction() as sessao:
        assert sessao.get('usuario_id') == id_teste
        assert sessao.get('perfil') == 'jogador'
    assert cliente.get('/jogador/dashboard').status_code == 200


def test_senha_invalida_nao_troca_conta_atual(app_db):
    cliente = app_db.test_client()
    assert cliente.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'}).status_code in (302, 303)
    with cliente.session_transaction() as sessao:
        id_original = sessao.get('usuario_id')
    resposta = cliente.post('/login', data={'login': 'mestre-db', 'senha': 'errada'})
    assert resposta.status_code == 401
    with cliente.session_transaction() as sessao:
        assert sessao.get('usuario_id') == id_original
