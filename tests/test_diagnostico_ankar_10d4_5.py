"""Etapa 10D.4.5 — apresentação de diagnósticos d100 em toda Ankar."""
from __future__ import annotations

import random

from app.services.gerador_npcs_ankar import sortear_encontros_regionais
import app.services.gerador_npcs_ankar as regional


def _tabelas():
    return [
        {"local_id": "a", "local_nome": "Rota A",
         "zona_index": 0, "zona_nome": "Zona A", "tabela_index": 0,
         "terreno": "GRAMA", "tabela": {"encontros": [
             {"pokemon": "Bulbasaur", "d100": "1-50", "faixa_valida": True},
             {"pokemon": "Charmander", "d100": "51-100", "faixa_valida": True},
         ]}},
        {"local_id": "b", "local_nome": "Rota B",
         "zona_index": 0, "zona_nome": "Zona B", "tabela_index": 0,
         "terreno": "CIDADE", "tabela": {"encontros": [
             {"pokemon": "Bulbasaur", "d100": "1-60", "faixa_valida": True},
         ]}},
        {"local_id": "c", "local_nome": "Rota C",
         "zona_index": 0, "zona_nome": "Zona C", "tabela_index": 0,
         "terreno": "PESCA", "tabela": {"encontros": [
             {"pokemon": "Espécie sem forma", "d100": "1-100", "faixa_valida": True},
         ]}},
    ]


def _atlas():
    locais = []
    for t in _tabelas():
        locais.append({
            "id": t["local_id"], "nome": t["local_nome"], "tipo": "rota",
            "zonas": [{"nome": t["zona_nome"], "tabelas": [t["tabela"]]}],
        })
    return {"locais": locais}


def test_diagnostico_regional_distingue_tabelas_e_faces():
    escolhas, avisos = sortear_encontros_regionais(
        _tabelas(), 2, nomes_habilitados={"Bulbasaur", "Charmander"},
        permitir_repetidos=False, rng=random.Random(4),
    )
    assert len(escolhas) == 2
    assert {i["pokemon"] for i in escolhas} == {"Bulbasaur", "Charmander"}
    assert avisos["tabelas_consultadas"] == 3
    assert avisos["tabelas_aptas"] == 2
    assert avisos["tabelas_sem_encontros_validos"] == 1
    assert avisos["rolagens_sem_faixa"] == 140
    assert avisos["rolagens_sem_forma"] == 100


def test_preview_sucesso_com_diagnostico_recolhido(app_db, client_db, monkeypatch):
    monkeypatch.setattr(regional, "carregar_catalogo_ankar", _atlas)
    assert client_db.post("/login", data={
        "login": "mestre-db", "senha": "senha-db"
    }).status_code == 302
    client_db.get("/mestre/npcs")
    with client_db.session_transaction() as sess:
        token = sess["npc_catalogo_csrf"]
    resp = client_db.post("/mestre/npcs/gerar", data={
        "csrf_token": token, "nome": "Horda teste", "tipo": "temporario",
        "modo": "aleatorio", "quantidade": "2", "nivel": "20",
    }, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Prévia gerada com sucesso." in html
    assert '<details class="npcs-diagnostico-atlas">' in html
    assert "3 tabela(s) consultada(s)" in html
    assert "2 tabela(s) possuem encontros aproveitáveis" in html
    assert "Dados do Atlas, não erros desta equipe" in html
    assert "Tabela original:" not in html
    assert "Bulbasaur" in html and "Charmander" in html


def test_modo_manual_nao_mostra_relatorio_de_tabelas(app_db, client_db):
    assert client_db.post("/login", data={
        "login": "mestre-db", "senha": "senha-db"
    }).status_code == 302
    client_db.get("/mestre/npcs")
    with client_db.session_transaction() as sess:
        token = sess["npc_catalogo_csrf"]
    resp = client_db.post("/mestre/npcs/gerar", data={
        "csrf_token": token, "nome": "Treinador manual", "tipo": "fixo",
        "modo": "manual", "quantidade": "1", "nivel": "18",
        "forma_id_manual": [app_db.config["TEST_IDS"]["formas"]["bulbasaur"]],
    }, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Prévia gerada com sucesso." in html
    assert "Espécies escolhidas manualmente." in html
    assert "npcs-diagnostico-atlas" not in html
