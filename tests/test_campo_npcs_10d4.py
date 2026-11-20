"""Regressões integradas da Etapa 10D.4 — NPCs e hordas."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    Campanha, FormaPokemon, GrupoNPCEmCampo, HistoricoAlteracao,
    Pokemon, PokemonCapturavel, PokemonEmCampo, PokemonNPCEmCampo,
)
from app.services.campo_npc_service import mover_grupo_npc


def _entrar(client, login="mestre-db", senha="senha-db"):
    assert client.post("/login", data={"login": login, "senha": senha}).status_code == 302


def _token(client):
    assert client.get("/campo").status_code == 200
    with client.session_transaction() as sessao:
        return sessao["campo_csrf"]


def _forma(app):
    with app.app_context():
        forma = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.nome == "Bulbasaur")
        )
        assert forma is not None
        return str(forma.id)


def _criar(client, token, forma, *, nome="Horda de teste", tipo="horda", qtd=3, time=2):
    return client.post("/campo/npcs/criar", data={
        "csrf_token": token,
        "nome": nome,
        "tipo": tipo,
        "forma_id": forma,
        "nivel": "12",
        "quantidade": str(qtd),
        "time_numero": str(time),
    })


def test_mestre_cria_horda_compartilhada_e_jogador_so_visualiza(app_db, client_db):
    forma = _forma(app_db)
    _entrar(client_db)
    token = _token(client_db)
    assert _criar(client_db, token, forma).status_code == 302

    with app_db.app_context():
        grupo = db.session.scalar(select(GrupoNPCEmCampo))
        assert grupo is not None and grupo.tipo == "horda" and grupo.time_numero == 2
        grupo_id = str(grupo.id)
        membros = db.session.scalars(select(PokemonNPCEmCampo)).all()
        assert len(membros) == 3
        assert all(m.pv_atual == m.pv_maximo and m.pv_maximo > 0 for m in membros)
        # NPCs não ocupam equipe/Box nem se tornam capturáveis automaticamente.
        assert db.session.scalar(select(func.count()).select_from(Pokemon)) == 0
        assert db.session.scalar(select(func.count()).select_from(PokemonCapturavel)) == 0

    pagina = client_db.get("/campo").get_data(as_text=True)
    assert "Horda de teste" in pagina and "Bulbasaur" in pagina
    assert 'aria-label="Time 2"' in pagina
    assert "Gerador regional e catálogo de NPCs" in pagina

    assert client_db.post("/logout").status_code == 302
    _entrar(client_db, "bartz-db", "abc123")
    jogador = client_db.get("/campo/estado")
    texto = jogador.get_data(as_text=True)
    assert jogador.status_code == 200 and "Horda de teste" in texto
    assert "Bulbasaur" in texto
    assert "/campo/npcs/" + grupo_id + "/mover" not in texto
    token_jogador = _token(client_db)
    assert _criar(client_db, token_jogador, forma, nome="Invasão").status_code == 403


def test_mestre_move_ajusta_pv_retira_e_limpa_horda(app_db, client_db):
    forma = _forma(app_db)
    _entrar(client_db)
    token = _token(client_db)
    assert _criar(client_db, token, forma, qtd=2).status_code == 302
    with app_db.app_context():
        grupo = db.session.scalar(select(GrupoNPCEmCampo))
        grupo_id = str(grupo.id)
        membro = db.session.scalar(select(PokemonNPCEmCampo))
        membro_id = str(membro.id)
        pv_original = membro.pv_atual

    assert client_db.post(f"/campo/npcs/{grupo_id}/mover", data={
        "csrf_token": token, "time_numero": "16",
    }).status_code == 302

    assert client_db.post(f"/campo/npcs/pokemons/{membro_id}/pv", data={
        "csrf_token": token, "quantidade": "9", "operacao": "menos",
    }).status_code == 302

    with app_db.app_context():
        grupo = db.session.get(GrupoNPCEmCampo, uuid.UUID(grupo_id))
        membro = db.session.get(PokemonNPCEmCampo, uuid.UUID(membro_id))
        assert grupo.time_numero == 16
        assert membro.pv_atual == max(0, pv_original - 9)

    assert client_db.post(f"/campo/npcs/pokemons/{membro_id}/retirar", data={
        "csrf_token": token,
    }).status_code == 302
    with app_db.app_context():
        assert db.session.get(PokemonNPCEmCampo, uuid.UUID(membro_id)) is None
        assert db.session.get(GrupoNPCEmCampo, uuid.UUID(grupo_id)) is not None

    assert client_db.post("/campo/limpar", data={"csrf_token": token}).status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(PokemonNPCEmCampo)) == 0
        assert db.session.scalar(select(func.count()).select_from(GrupoNPCEmCampo)) == 0
        assert db.session.scalar(select(func.count()).select_from(PokemonEmCampo)) == 0
        eventos = db.session.scalars(
            select(HistoricoAlteracao).where(HistoricoAlteracao.entidade == "campo_npc")
        ).all()
        assert {"criar", "mover", "ajustar_pv", "retirar", "limpar"}.issubset({e.acao for e in eventos})


def test_adicionar_ao_grupo_e_remover_ultimo_integrante(app_db, client_db):
    forma = _forma(app_db)
    _entrar(client_db)
    token = _token(client_db)
    assert _criar(client_db, token, forma, tipo="npc", nome="Treinador Rival", qtd=1).status_code == 302

    with app_db.app_context():
        grupo_id = str(db.session.scalar(select(GrupoNPCEmCampo)).id)
    rejeicao = client_db.post("/campo/npcs/adicionar", data={
        "csrf_token": token, "grupo_id": grupo_id, "forma_id": forma,
        "nivel": "15", "quantidade": "2",
    }, follow_redirects=True)
    assert "manter o nível 12" in rejeicao.get_data(as_text=True)
    with app_db.app_context():
        assert len(db.session.scalars(select(PokemonNPCEmCampo)).all()) == 1
    assert client_db.post("/campo/npcs/adicionar", data={
        "csrf_token": token, "grupo_id": grupo_id, "forma_id": forma,
        "nivel": "12", "quantidade": "2",
    }).status_code == 302
    with app_db.app_context():
        membros = db.session.scalars(select(PokemonNPCEmCampo)).all()
        ids = [str(x.id) for x in membros]
        assert len(ids) == 3
        assert {x.nivel for x in membros} == {12}

    for membro_id in ids:
        assert client_db.post(f"/campo/npcs/pokemons/{membro_id}/retirar", data={
            "csrf_token": token,
        }).status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(GrupoNPCEmCampo)) is None


def test_bloqueia_csrf_quantidade_e_time_invalidos(app_db, client_db):
    forma = _forma(app_db)
    _entrar(client_db)
    token = _token(client_db)
    assert _criar(client_db, "", forma).status_code == 400
    assert _criar(client_db, token, forma, qtd=13).status_code == 302
    assert _criar(client_db, token, forma, time=17).status_code == 302
    assert _criar(client_db, token, "inválido").status_code == 302

    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(GrupoNPCEmCampo)) == 0


def test_isolamento_entre_campanhas(app_db, client_db):
    forma = _forma(app_db)
    _entrar(client_db)
    token = _token(client_db)
    assert _criar(client_db, token, forma).status_code == 302
    with app_db.app_context():
        grupo_id = str(db.session.scalar(select(GrupoNPCEmCampo)).id)
        db.session.add(Campanha(codigo="outra-campanha", nome="Outra", ativo=True))
        db.session.commit()
        with pytest.raises(ValueError, match="não encontrado nesta campanha"):
            mover_grupo_npc(
                campanha_codigo="outra-campanha", grupo_id=grupo_id,
                time_numero="4", usuario_id=app_db.config["TEST_IDS"]["mestre"],
            )
        db.session.rollback()
        assert db.session.get(GrupoNPCEmCampo, uuid.UUID(grupo_id)).time_numero == 2
