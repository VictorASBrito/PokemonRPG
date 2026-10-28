"""Regressões da etapa 10A.4 (rodar na instalação local do PokémonRPG)."""
from __future__ import annotations

import re
from pathlib import Path

from app.services.regiao_ankar_service import (
    encontro_por_indices, formas_presentes_no_atlas, localizar_ankar,
    paragrafos_da_descricao,
)
from app.extensions import db
from app.models.db import FormaPokemon, PokemonCapturavel
from sqlalchemy import func, select

RAIZ = Path(__file__).resolve().parents[1]


def _rota1():
    rota = localizar_ankar("rota-1")
    assert rota
    return rota


def test_x_nao_pode_virar_pokemon():
    local = {"zonas": [{"tabelas": [{"encontros": [
        {"pokemon": "x", "marcador": True}, {"pokemon": "Tentacool", "marcador": False},
        {"pokemon": "Random", "marcador": False}, {"pokemon": "", "marcador": False},
    ]}]}]}
    assert encontro_por_indices(local, 0, 0, 0) is None
    assert encontro_por_indices(local, 0, 0, 1)["pokemon"] == "Tentacool"
    assert encontro_por_indices(local, 0, 0, 2) is None
    assert encontro_por_indices(local, 0, 0, 3) is None
    assert encontro_por_indices(local, -1, 0, 0) is None
    assert encontro_por_indices(local, 20, 0, 0) is None


def test_faixas_da_rota_um_sao_preservadas():
    tabela = _rota1()["zonas"][0]["tabelas"][0]
    assert [e["d100"] for e in tabela["encontros"]] == [
        "1-30", "31-45", "46-55", "56-60", "60-75", "76-90", "91-97", "98-100"
    ]


def test_descricao_preserva_o_conteudo():
    original = "Primeira frase. Segunda frase. Terceira frase, com detalhes."
    assert " ".join(paragrafos_da_descricao(original)) == original
    assert paragrafos_da_descricao("-") == []


def test_estilos_e_scripts_sao_isolados():
    css = (RAIZ / "static/css/atlas-ankar.css").read_text(encoding="utf-8")
    js = (RAIZ / "static/js/atlas-ankar.js").read_text(encoding="utf-8")
    assert "ankar-mapa-base" in css and "anker-nunca" not in css
    assert "Math.max(820" not in js  # não forçar mapa maior que a tela
    assert "data-ankar-gerar" in js
    assert "[data-ankar-etapa=\"jogador\"]" in js


def test_ficha_mestre_exibe_cards_modal_e_x(app_db):
    # Catálogo de teste normalmente só contém algumas espécies; ambos devem
    # aparecer: card gerável quando houver correspondência, e placeholders.
    with app_db.app_context():
        formas = formas_presentes_no_atlas(_rota1())
        assert isinstance(formas, dict)
        assert all("id" in info and "imagem" in info for info in formas.values())
    with app_db.test_client() as client:
        client.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'})
        resp = client.get('/regiao/ankar/rota-1')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'ankar-grade-pokemon' in html
        assert 'Deseja gerar este Pokémon na tela de capturáveis?' in html
        assert 'encontrado_por_personagem_id' in html
        assert '1-30' in html and '60-75' in html


def test_post_sem_csrf_nao_cria_encontro(app_db):
    with app_db.test_client() as client:
        client.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'})
        resp = client.post('/regiao/ankar/rota-1/gerar-encontro', data={
            'zona': 0, 'tabela': 0, 'indice': 0,
        })
        assert resp.status_code in (302, 303)
        with app_db.app_context():
            assert db.session.scalar(select(func.count(PokemonCapturavel.id))) == 0


def test_post_indices_invalidos_nao_cria_encontro(app_db):
    with app_db.test_client() as client:
        client.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'})
        with client.session_transaction() as sess:
            sess['atlas_ankar_gerar_csrf'] = 'token-teste'
        for indice in ('-1', 'x', '99999'):
            resp = client.post('/regiao/ankar/rota-1/gerar-encontro', data={
                'csrf_token': 'token-teste', 'zona': '0', 'tabela': '0', 'indice': indice,
            })
            assert resp.status_code in (302, 303)
        with app_db.app_context():
            assert db.session.scalar(select(func.count(PokemonCapturavel.id))) == 0


def test_mestre_gera_especie_do_atlas_pelo_servico_existente(app_db):
    # A fixture oficial contém Rattata; a Rota 8 apresenta Rattata na 1ª tabela.
    local = localizar_ankar('rota-8')
    assert local['zonas'][0]['tabelas'][0]['encontros'][0]['pokemon'] == 'Rattata'
    with app_db.test_client() as client:
        client.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'})
        with client.session_transaction() as sess:
            sess['atlas_ankar_gerar_csrf'] = 'token-teste'
        resp = client.post('/regiao/ankar/rota-8/gerar-encontro', data={
            'csrf_token': 'token-teste', 'zona': 0, 'tabela': 0, 'indice': 0,
            'encontrado_por_personagem_id': app_db.config['TEST_IDS']['personagem'],
        })
        assert resp.status_code in (302, 303)
        assert '/mestre/capturaveis' in resp.headers['Location']
        with app_db.app_context():
            assert db.session.scalar(select(func.count(PokemonCapturavel.id))) == 1


def test_marcador_x_nao_pode_ser_gerado_por_post(app_db):
    local = localizar_ankar('gym-05-fai')
    assert local is not None
    x = next((zi, ti, ei) for zi, z in enumerate(local['zonas'])
        for ti, t in enumerate(z['tabelas']) for ei, e in enumerate(t['encontros'])
        if e.get('marcador'))
    with app_db.test_client() as client:
        client.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'})
        with client.session_transaction() as sess:
            sess['atlas_ankar_gerar_csrf'] = 'token-teste'
        resp = client.post('/regiao/ankar/gym-05-fai/gerar-encontro', data={
            'csrf_token': 'token-teste', 'zona': x[0], 'tabela': x[1], 'indice': x[2],
            'encontrado_por_personagem_id': app_db.config['TEST_IDS']['personagem'],
        })
        assert resp.status_code in (302, 303)
        assert '/mestre/capturaveis' not in resp.headers['Location']
        with app_db.app_context():
            assert db.session.scalar(select(func.count(PokemonCapturavel.id))) == 0
