"""Regressão: evolução do tester e ação na ficha isolada /p/login.

A identidade continua estritamente vinculada a Personagem.usuario_id.
A correção não libera evoluções para outro jogador ou para a conta mestre.
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    EspeciePokemon, EvolucaoPokemon, FormaPokemon, FormaPokemonAtributo,
    Personagem, Pokemon, Usuario,
)
from app.services.evolucao_efetiva_service import evoluir_pokemon
from app.services.pokemon_db_service import calcular_pokemon, carregar_regras_pokemon_db


def _montar_evolucao(app):
    with app.app_context():
        ch = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        es = EspeciePokemon(codigo="charmeleon", nome="Charmeleon", ativo=True)
        nova = FormaPokemon(
            especie=es, codigo="charmeleon", nome="Charmeleon",
            categoria="normal", ativo=True,
        )
        db.session.add(nova)
        db.session.flush()
        for base in ch.atributos_base:
            db.session.add(FormaPokemonAtributo(
                forma_pokemon=nova,
                atributo=base.atributo,
                valor_base=Decimal(base.valor_base) + 8,
            ))
        r = EvolucaoPokemon(
            forma_origem_id=ch.id,
            forma_destino_id=nova.id,
            tipo_requisito="nivel",
            requisitos={"tipo_relacao": "evolucao", "nivel": 16},
            ativo=True,
        )
        personagem = db.session.get(
            Personagem, uuid.UUID(app.config["TEST_IDS"]["personagem"])
        )
        p = Pokemon(
            personagem=personagem, forma_pokemon_id=ch.id,
            apelido="Foguinho", genero="Macho",
            localizacao="equipe", posicao=1, pv_atual=1, ativo=True,
        )
        db.session.add_all([r, p])
        db.session.flush()
        regras = carregar_regras_pokemon_db(personagem.campanha_id)
        p.pv_atual = calcular_pokemon(p, personagem, regras)["totais"]["pv"]
        db.session.commit()
        return str(p.id), str(r.id), nova.id, ch.id


def _csrf_do_pokemon(client, url):
    resposta = client.get(url)
    assert resposta.status_code == 200
    with client.session_transaction() as sessao:
        token = sessao["csrf_acao_evolucao"]
    assert token
    assert "Evoluir" in resposta.get_data(as_text=True)
    assert "Charmeleon" in resposta.get_data(as_text=True)
    return token


def test_tester_pode_evoluir_o_proprio_pokemon_pelo_formulario(app_db, client_db):
    pid, rid, destino, _ = _montar_evolucao(app_db)
    with app_db.app_context():
        conta = db.session.get(Usuario, uuid.UUID(app_db.config["TEST_IDS"]["jogador"]))
        conta.perfil = "tester"
        db.session.commit()

    assert client_db.post("/login", data={
        "login": "bartz-db", "senha": "abc123",
    }).status_code == 302
    token = _csrf_do_pokemon(client_db, "/jogador/dashboard")
    resposta = client_db.post(
        f"/jogador/pokemon/{pid}/evolucoes/{rid}/evoluir",
        data={"csrf_token": token, "retorno": "boxes"},
    )
    assert resposta.status_code == 302
    assert "/jogador/pokemon/" in resposta.headers["Location"]
    with app_db.app_context():
        assert db.session.get(Pokemon, uuid.UUID(pid)).forma_pokemon_id == destino


def test_entrada_por_url_de_jogador_permite_evolucao_sem_trocar_conta_mestre(
    app_db, client_db, tmp_path,
):
    pid, rid, destino, _ = _montar_evolucao(app_db)
    config = tmp_path / "entrada_personagens.json"
    config.write_text(json.dumps({
        "habilitado": True,
        "slots": [
            {"login": "bartz-db" if i == 1 else f"outro{i}"}
            for i in range(1, 10)
        ],
    }), encoding="utf-8")
    app_db.config["LOGIN_PERSONAGENS_ARQUIVO"] = str(config)

    # Sessão principal do mestre não pode migrar para o cookie da ficha.
    assert client_db.post("/login", data={
        "login": "mestre-db", "senha": "senha-db",
    }).status_code == 302
    assert client_db.get("/mestre/dashboard").status_code == 200

    ficha = "/p/bartz-db/jogador/dashboard"
    pagina = client_db.get(ficha)
    assert pagina.status_code == 200
    assert f"/p/bartz-db/jogador/pokemon/{pid}/evolucoes/{rid}/evoluir" in pagina.get_data(as_text=True)
    # O token deve sair do formulário da ficha isolada, não do
    # cookie principal (que continua pertencendo ao mestre).
    import re
    form = pagina.get_data(as_text=True)
    token_match = re.search(r'name="csrf_token" value="([^"]+)"', form)
    assert token_match
    token = token_match.group(1)
    resposta = client_db.post(
        f"/p/bartz-db/jogador/pokemon/{pid}/evolucoes/{rid}/evoluir",
        data={"csrf_token": token, "retorno": "boxes"},
    )
    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith(f"/p/bartz-db/jogador/pokemon/{pid}")
    assert client_db.get("/mestre/dashboard").status_code == 200
    with app_db.app_context():
        assert db.session.get(Pokemon, uuid.UUID(pid)).forma_pokemon_id == destino


def test_tester_estranho_nao_pode_evoluir_pokemon_de_outro_treinador(app_db):
    pid, rid, _, origem = _montar_evolucao(app_db)
    with app_db.app_context():
        ids = app_db.config["TEST_IDS"]
        conta = db.session.get(Usuario, uuid.UUID(ids["jogador"]))
        conta.perfil = "tester"
        # Usuário mestre nunca é confundido com dono pela sessão do jogador.
        try:
            evoluir_pokemon(
                pokemon_id=pid, relacao_id=rid,
                personagem_id=ids["personagem"],
                campanha_id=ids["campanha"],
                usuario_id=ids["mestre"],
            )
        except PermissionError:
            pass
        else:
            raise AssertionError("Conta alheia evoluiu Pokémon indevidamente.")
        db.session.rollback()
        assert db.session.get(Pokemon, uuid.UUID(pid)).forma_pokemon_id == origem
