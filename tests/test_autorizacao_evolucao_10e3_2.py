"""10E.3.2 — Regressões da liberação narrativa por Pokémon individual."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    AutorizacaoEvolucaoPokemon, Campanha, CampanhaMembro, EspeciePokemon,
    EvolucaoPokemon, FormaPokemon, HistoricoAlteracao, Personagem, Pokemon, Usuario,
)
from app.services.autorizacao_evolucao_service import (
    autorizar_evolucao_individual, revogar_evolucao_individual,
)
from app.services.consulta_evolucao_service import consultar_evolucoes_pokemon


def _login(client, login="mestre-db", senha="senha-db"):
    assert client.post("/login", data={"login": login, "senha": senha}).status_code == 302


def _forma(codigo):
    existente = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == codigo))
    if existente:
        return existente
    especie = EspeciePokemon(codigo=codigo, nome=codigo.capitalize(), ativo=True)
    forma = FormaPokemon(
        especie=especie, codigo=codigo, nome=codigo.capitalize(),
        ativo=True, categoria="normal",
    )
    db.session.add(forma)
    db.session.flush()
    return forma


def _montar(app):
    with app.app_context():
        ids = app.config["TEST_IDS"]
        personagem = db.session.get(Personagem, uuid.UUID(ids["personagem"]))
        eevee, umbreon, espeon, vaporeon = map(
            _forma, ("eevee", "umbreon", "espeon", "vaporeon")
        )
        r1 = EvolucaoPokemon(
            forma_origem_id=eevee.id, forma_destino_id=umbreon.id,
            tipo_requisito="especial",
            requisitos={"tipo_relacao": "evolucao", "requer_liberacao_mestre": True,
                        "condicao": "Decisão narrativa"},
            ativo=True,
        )
        r2 = EvolucaoPokemon(
            forma_origem_id=eevee.id, forma_destino_id=espeon.id,
            tipo_requisito="especial",
            requisitos={"tipo_relacao": "evolucao", "requer_liberacao_mestre": True,
                        "condicao": "Decisão do mestre"},
            ativo=True,
        )
        rsimples = EvolucaoPokemon(
            forma_origem_id=eevee.id, forma_destino_id=vaporeon.id,
            tipo_requisito="item",
            requisitos={"tipo_relacao": "evolucao", "item_nome": "Pedra da Água"},
            ativo=True,
        )
        p1 = Pokemon(
            personagem_id=personagem.id, forma_pokemon_id=eevee.id,
            apelido="Lua", genero="Ø", pv_atual=18, shiny=True,
            localizacao="box", posicao=1, ativo=True,
        )
        p2 = Pokemon(
            personagem_id=personagem.id, forma_pokemon_id=eevee.id,
            apelido="Sol", genero="Ø", pv_atual=17,
            localizacao="box", posicao=2, ativo=True,
        )
        db.session.add_all([r1, r2, rsimples, p1, p2])
        db.session.commit()
        return {
            "personagem": personagem.id, "campanha": personagem.campanha_id,
            "mestre": uuid.UUID(ids["mestre"]), "jogador": uuid.UUID(ids["jogador"]),
            "eevee": eevee.id, "p1": p1.id, "p2": p2.id,
            "umbreon": r1.id, "espeon": r2.id, "vaporeon": rsimples.id,
        }


def _dados(x, **changes):
    return dict(
        pokemon_id=x["p1"], relacao_id=x["umbreon"],
        usuario_id=x["mestre"], campanha_id=x["campanha"],
        motivo="Ritual narrativo na floresta de Ankar",
        **changes,
    )


def _status(x, pokemon="p1"):
    personagem = db.session.get(Personagem, x["personagem"])
    p = db.session.get(Pokemon, x[pokemon])
    return {o.destino_codigo: o.estado for o in consultar_evolucoes_pokemon(p, personagem).opcoes}


def test_concessao_isolada_por_pokemon_e_por_destino_sem_mutacoes(app_db):
    x = _montar(app_db)
    with app_db.app_context():
        p = db.session.get(Pokemon, x["p1"])
        antes = (p.forma_pokemon_id, p.shiny, p.pv_atual, p.apelido, p.posicao)
        a, mudou = autorizar_evolucao_individual(**_dados(x))
        assert mudou is True
        db.session.commit()
        assert a.ativo is True and a.autorizado_por_id == x["mestre"]
        assert _status(x) == {
            "umbreon": "liberada_mestre",
            "espeon": "requer_mestre",
            "vaporeon": "pedra_ausente",
        }
        assert _status(x, "p2")["umbreon"] == "requer_mestre"
        assert db.session.scalar(select(func.count(AutorizacaoEvolucaoPokemon.id))) == 1
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 1
        assert (p.forma_pokemon_id, p.shiny, p.pv_atual, p.apelido, p.posicao) == antes


def test_repetir_concessao_revogar_e_reliberar_preserva_historico(app_db):
    x = _montar(app_db)
    with app_db.app_context():
        a, mudou = autorizar_evolucao_individual(**_dados(x))
        db.session.commit()
        pk = a.id
        b, mudou = autorizar_evolucao_individual(**_dados(x))
        db.session.commit()
        assert not mudou and b.id == pk
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 1

        assert revogar_evolucao_individual(**_dados(x)) is True
        db.session.commit()
        assert _status(x)["umbreon"] == "requer_mestre"
        assert revogar_evolucao_individual(**_dados(x)) is False
        db.session.commit()
        novo, mudou = autorizar_evolucao_individual(**_dados(x))
        db.session.commit()
        assert mudou and novo.id == pk
        assert novo.revogado_em is None
        assert novo.revogado_por_id is None
        assert novo.motivo_revogacao is None
        assert _status(x)["umbreon"] == "liberada_mestre"
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 3


def test_bloqueia_falsificacao_de_usuario_campanha_relacao_e_nivel_simples(app_db):
    x = _montar(app_db)
    with app_db.app_context():
        with pytest.raises(PermissionError):
            autorizar_evolucao_individual(**{
                **_dados(x), "usuario_id": x["jogador"],
            })
        with pytest.raises(ValueError, match="Evolução simples"):
            autorizar_evolucao_individual(**{
                **_dados(x), "relacao_id": x["vaporeon"],
            })
        outra_campanha = Campanha(codigo="outra-campanha", nome="Outra campanha", ativo=True)
        db.session.add(outra_campanha)
        db.session.commit()
        with pytest.raises(PermissionError):
            autorizar_evolucao_individual(**{
                **_dados(x), "campanha_id": outra_campanha.id,
            })
        outsider = Pokemon(
            personagem_id=x["personagem"],
            forma_pokemon_id=db.session.get(EvolucaoPokemon, x["umbreon"]).forma_destino_id,
            localizacao="box", posicao=3, pv_atual=5, ativo=True,
        )
        db.session.add(outsider)
        db.session.commit()
        with pytest.raises(ValueError, match="forma atual"):
            autorizar_evolucao_individual(**{
                **_dados(x), "pokemon_id": outsider.id,
            })
        assert db.session.scalar(select(func.count(AutorizacaoEvolucaoPokemon.id))) == 0


def test_relacoes_inativas_mega_e_destino_inativo_nao_sao_autorizaveis(app_db):
    x = _montar(app_db)
    with app_db.app_context():
        rel = db.session.get(EvolucaoPokemon, x["umbreon"])
        rel.ativo = False
        db.session.commit()
        with pytest.raises(ValueError, match="inativa"):
            autorizar_evolucao_individual(**_dados(x))
        rel.ativo = True
        rel.requisitos = {"tipo_relacao": "mega", "condicao": "Mega"}
        db.session.commit()
        with pytest.raises(ValueError, match="não corresponde"):
            autorizar_evolucao_individual(**_dados(x))
        rel.requisitos = {"tipo_relacao": "evolucao", "requer_liberacao_mestre": True}
        rel.forma_destino.ativo = False
        db.session.commit()
        with pytest.raises(ValueError, match="Destino"):
            autorizar_evolucao_individual(**_dados(x))


def test_falha_na_justificativa_nao_cria_autorizacao(app_db):
    x = _montar(app_db)
    with app_db.app_context():
        for motivo in ("", "x", "a" * 501):
            with pytest.raises(ValueError, match="motivo"):
                autorizar_evolucao_individual(**{**_dados(x), "motivo": motivo})
        assert db.session.scalar(select(func.count(AutorizacaoEvolucaoPokemon.id))) == 0


def test_mudanca_manual_de_forma_revoga_em_transacao(app_db, client_db):
    x = _montar(app_db)
    with app_db.app_context():
        autorizar_evolucao_individual(**_dados(x))
        db.session.commit()
    _login(client_db)
    url = f"/mestre/jogadores/{x['personagem']}/pokemon/{x['p1']}"
    form = {
        "especie_nome": "Charmander", "genero": "Ø",
        "natureza": "Dócil", "status": "Nenhum",
        "pv_atual": "18", "golpe_nome": ["", "", "", ""],
    }
    assert client_db.post(url, data=form).status_code == 302
    with app_db.app_context():
        a = db.session.scalar(select(AutorizacaoEvolucaoPokemon))
        assert a.ativo is False and a.revogado_em is not None
        assert a.motivo_revogacao.startswith("Mudança manual")
    # Mesmo se uma manutenção externa devolver a forma antiga,
    # uma concessão previamente revogada NÃO volta a valer.
    with app_db.app_context():
        db.session.get(Pokemon, x["p1"]).forma_pokemon_id = x["eevee"]
        db.session.commit()
        assert _status(x)["umbreon"] == "requer_mestre"


def test_rotas_mestre_csrf_escopo_e_restricao_jogador(app_db, client_db):
    x = _montar(app_db)
    base = f"/mestre/jogadores/{x['personagem']}/pokemon/{x['p1']}/evolucoes/{x['umbreon']}"
    assert client_db.post(base + "/autorizar").status_code == 302
    _login(client_db, "bartz-db", "abc123")
    assert client_db.post(base + "/autorizar", data={"motivo": "Só jogador"}).status_code == 302
    # A proteção encerra a sessão em tentativas de acesso à área errada.
    _login(client_db, "bartz-db", "abc123")
    assert client_db.get(f"/jogador/pokemon/{x['p1']}").status_code == 200
    assert "Liberar para este Pokémon" not in client_db.get(
        f"/jogador/pokemon/{x['p1']}"
    ).get_data(as_text=True)
    client_db.post("/logout")
    _login(client_db)
    page = client_db.get(
        f"/mestre/jogadores/{x['personagem']}/pokemon/{x['p1']}"
    )
    assert page.status_code == 200
    assert "Liberar para este Pokémon" in page.get_data(as_text=True)
    with client_db.session_transaction() as sess:
        token = sess["csrf_autorizacao_evolucao"]
    assert client_db.post(base + "/autorizar", data={
        "motivo": "Evento narrativo",
    }).status_code == 403
    with app_db.app_context():
        assert db.session.scalar(select(func.count(AutorizacaoEvolucaoPokemon.id))) == 0
    grant = client_db.post(base + "/autorizar", data={
        "csrf_token": token, "motivo": "Eevee recebeu a bênção do mestre",
    })
    assert grant.status_code == 302
    page = client_db.get(
        f"/mestre/jogadores/{x['personagem']}/pokemon/{x['p1']}"
    ).get_data(as_text=True)
    assert "Liberada pelo mestre" in page
    assert "Revogar liberação" in page
    assert "Liberar para este Pokémon" in page  # opção Espeon separada
    revoke = client_db.post(base + "/revogar", data={
        "csrf_token": token, "motivo": "Ritual foi interrompido",
    })
    assert revoke.status_code == 302
    with app_db.app_context():
        assert _status(x)["umbreon"] == "requer_mestre"
        assert _status(x, "p2")["umbreon"] == "requer_mestre"
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 2


def test_nao_aceita_forjar_outro_personagem_na_url(app_db, client_db):
    x = _montar(app_db)
    with app_db.app_context():
        jogador = db.session.get(Personagem, x["personagem"])
        # Um usuário só pode ter um personagem por campanha. Criar outra
        # conta preserva essa restrição ao testar a tentativa de falsificação.
        outra_conta = Usuario(
            login="outro-jogador-teste", nome="Outro jogador",
            senha_hash="hash-nao-utilizado", perfil="jogador", ativo=True,
        )
        fake = Personagem(
            usuario=outra_conta, campanha_id=jogador.campanha_id,
            nome="Outro personagem", nivel=8, ativo=True,
        )
        db.session.add_all([outra_conta, fake])
        db.session.commit()
        fake_id = fake.id
    _login(client_db)
    # Criar CSRF na ficha verdadeira, depois tentar utilizar outra URL.
    client_db.get(f"/mestre/jogadores/{x['personagem']}/pokemon/{x['p1']}")
    with client_db.session_transaction() as sess:
        token = sess["csrf_autorizacao_evolucao"]
    wrong = f"/mestre/jogadores/{fake_id}/pokemon/{x['p1']}/evolucoes/{x['umbreon']}/autorizar"
    assert client_db.post(wrong, data={
        "csrf_token": token, "motivo": "Tentativa inválida",
    }).status_code == 404
    with app_db.app_context():
        assert db.session.scalar(select(func.count(AutorizacaoEvolucaoPokemon.id))) == 0
