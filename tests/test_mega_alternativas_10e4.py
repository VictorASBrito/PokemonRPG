"""10E.4 — Mega por permissão do treinador e alternativas livres (Morpeko)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    Atributo, EspeciePokemon, FormaPokemon, FormaPokemonAtributo,
    HistoricoAlteracao, Item, Personagem, PersonagemItem, Pokemon,
    PokemonEmCampo,
)
from app.services.campo_service import carregar_campo, retirar_pokemon, limpar_campo
from app.services.evolucao_efetiva_service import evoluir_pokemon
from app.services.pokemon_db_service import calcular_pokemon, carregar_regras_pokemon_db
from app.services.transformacoes_service import (
    listar_formas_temporarias, permitir_mega_treinador,
    transformar_pokemon, encerrar_mega_desmaio,
)


def _ids(app):
    return {chave: uuid.UUID(valor) for chave, valor in app.config["TEST_IDS"].items()
            if chave != "formas"}


def _familia(codigo: str, membros: list[tuple[str, str, int]]):
    especie = EspeciePokemon(codigo=codigo, nome=codigo.capitalize(), ativo=True)
    db.session.add(especie)
    db.session.flush()
    atributos = list(db.session.scalars(select(Atributo).where(Atributo.escopo == "pokemon")))
    formas = {}
    for i, (cod, categoria, aumento) in enumerate(membros):
        forma = FormaPokemon(
            especie=especie, codigo=cod, nome=cod.capitalize(),
            categoria=categoria, ativo=True,
        )
        db.session.add(forma)
        db.session.flush()
        for att in atributos:
            db.session.add(FormaPokemonAtributo(
                forma_pokemon=forma, atributo=att,
                valor_base=Decimal(20 + aumento),
            ))
        formas[cod] = forma
    db.session.flush()
    return formas


def _pokemon(app, forma, *, pos=1, dano=7):
    ids = _ids(app)
    p = Pokemon(
        personagem_id=ids["personagem"],
        forma_pokemon_id=forma.id,
        apelido="Companheiro", genero="Macho", shiny=True,
        localizacao="equipe", posicao=pos, pv_atual=1, ativo=True,
    )
    db.session.add(p)
    db.session.flush()
    personagem = db.session.get(Personagem, ids["personagem"])
    regras = carregar_regras_pokemon_db(personagem.campanha_id)
    p.pv_atual = calcular_pokemon(p, personagem, regras)["totais"]["pv"] - dano
    db.session.flush()
    return p


def _campo(app, pokemon, time=1):
    ids = _ids(app)
    db.session.add(PokemonEmCampo(
        campanha_id=ids["campanha"], pokemon_id=pokemon.id, time_numero=time,
    ))
    db.session.flush()


def _mudar(app, p, *, tipo, destino_id=None, usuario="jogador", personagem="personagem"):
    ids = _ids(app)
    return transformar_pokemon(
        pokemon_id=p.id, destino_id=destino_id, tipo=tipo,
        usuario_id=ids[usuario], personagem_id=ids[personagem],
        campanha_id=ids["campanha"],
    )


def _permissao(app, habilitar):
    ids = _ids(app)
    return permitir_mega_treinador(
        personagem_id=ids["personagem"], campanha_id=ids["campanha"],
        usuario_id=ids["mestre"], habilitar=habilitar,
    )


def test_morpeko_pode_trocar_livremente_sem_permissao_mestre(app_db):
    with app_db.app_context():
        formas = _familia("morpeko", [
            ("morpeko-satisfeito", "normal", 0),
            ("morpeko-faminto", "alternativa", 8),
        ])
        p = _pokemon(app_db, formas["morpeko-satisfeito"])
        db.session.commit()
        origem = p.forma_pokemon_id
        anterior = p.pv_atual
        opts = listar_formas_temporarias(p)
        assert [f.codigo for f in opts["alternativas"]] == ["morpeko-faminto"]
        assert not p.personagem.mega_habilitada
        msg = _mudar(app_db, p, tipo="alternativa", destino_id=formas["morpeko-faminto"].id)
        db.session.commit()
        assert "Morpeko-faminto" in msg
        assert p.forma_pokemon_id == origem
        assert p.forma_temporaria_id == formas["morpeko-faminto"].id
        assert p.tipo_transformacao == "alternativa"
        assert p.pv_atual > anterior
        opts = listar_formas_temporarias(p)
        assert opts["atual"].id == formas["morpeko-faminto"].id
        _mudar(app_db, p, tipo="reverter")
        db.session.commit()
        assert p.forma_temporaria_id is None and p.tipo_transformacao is None
        assert p.pv_atual == anterior


def test_morpeko_original_faminto_tambem_pode_virar_satisfeito(app_db):
    with app_db.app_context():
        formas = _familia("morpeko", [
            ("morpeko-satisfeito", "normal", 0),
            ("morpeko-faminto", "alternativa", 8),
        ])
        p = _pokemon(app_db, formas["morpeko-faminto"])
        db.session.commit()
        opts = listar_formas_temporarias(p)
        assert "morpeko-satisfeito" in [f.codigo for f in opts["alternativas"]]
        _mudar(app_db, p, tipo="alternativa", destino_id=formas["morpeko-satisfeito"].id)
        db.session.commit()
        assert p.forma_pokemon_id == formas["morpeko-faminto"].id
        assert p.forma_temporaria_id == formas["morpeko-satisfeito"].id


def test_mega_exige_permissao_por_treinador_sem_pedras_nem_campo(app_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal", 0),
            ("charizard-mega-x", "mega", 18),
            ("charizard-mega-y", "mega", 21),
        ])
        p = _pokemon(app_db, formas["charizard"])
        _campo(app_db, p)
        db.session.commit()
        original = p.forma_pokemon_id
        old_pv = p.pv_atual
        assert len(listar_formas_temporarias(p)["mega"]) == 2
        with pytest.raises(PermissionError, match="não habilitou"):
            _mudar(app_db, p, tipo="mega", destino_id=formas["charizard-mega-x"].id)
        db.session.rollback()
        assert p.forma_temporaria_id is None
        assert _permissao(app_db, True).startswith("Mega Evolução habilitada")
        db.session.commit()
        msg = _mudar(app_db, p, tipo="mega", destino_id=formas["charizard-mega-x"].id)
        db.session.commit()
        assert "Charizard-mega-x" in msg
        assert p.forma_pokemon_id == original
        assert p.forma_temporaria_id == formas["charizard-mega-x"].id
        assert p.pv_atual > old_pv
        # Nenhuma Pedra Chave, Charizardite ou registro na mochila
        assert db.session.scalar(select(func.count(PersonagemItem.id))) == 0
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) >= 2


def test_so_uma_mega_ativa_por_treinador_e_revogacao_reverte(app_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal", 0),
            ("charizard-mega-x", "mega", 18),
            ("charizard-mega-y", "mega", 20),
        ])
        p1 = _pokemon(app_db, formas["charizard"], pos=1)
        p2 = _pokemon(app_db, formas["charizard"], pos=2)
        _campo(app_db, p1, 1)
        _campo(app_db, p2, 2)
        _permissao(app_db, True)
        db.session.commit()
        _mudar(app_db, p1, tipo="mega", destino_id=formas["charizard-mega-x"].id)
        db.session.commit()
        with pytest.raises(ValueError, match="já possui"):
            _mudar(app_db, p2, tipo="mega", destino_id=formas["charizard-mega-y"].id)
        db.session.rollback()
        assert p2.forma_temporaria_id is None
        _permissao(app_db, False)
        db.session.commit()
        assert p1.forma_temporaria_id is None
        assert p1.forma_pokemon_id == formas["charizard"].id
        assert not p1.personagem.mega_habilitada


def test_mega_pode_ser_ativada_fora_do_campo_mas_nao_por_usuario_alheio(app_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal", 0), ("charizard-mega-x", "mega", 18),
        ])
        p = _pokemon(app_db, formas["charizard"])
        _permissao(app_db, True)
        db.session.commit()
        with pytest.raises(PermissionError, match="Somente"):
            _mudar(app_db, p, tipo="mega", destino_id=formas["charizard-mega-x"].id,
                   usuario="mestre")
        db.session.rollback()
        _mudar(app_db, p, tipo="mega", destino_id=formas["charizard-mega-x"].id)
        db.session.commit()
        assert p.forma_temporaria_id == formas["charizard-mega-x"].id


def test_rotas_campo_legadas_e_retirada_nao_revertem_mega(app_db, client_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal", 0), ("charizard-mega-x", "mega", 18),
        ])
        p = _pokemon(app_db, formas["charizard"])
        _campo(app_db, p)
        db.session.commit()
        pid, destino_id, dono_id = p.id, formas["charizard-mega-x"].id, p.personagem_id
    assert client_db.post("/login", data={"login": "mestre-db", "senha": "senha-db"}).status_code == 302
    pagina = client_db.get("/mestre/dashboard")
    assert pagina.status_code == 200
    assert "Permitir Mega Evolução" in pagina.get_data(as_text=True)
    with client_db.session_transaction() as sess:
        csrf = sess["perfil_csrf"]
    url = f"/mestre/painel/jogadores/{dono_id}/mega"
    assert client_db.post(url, data={"csrf_token": csrf, "habilitar": "1"}).status_code == 302
    client_db.post("/logout")
    assert client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"}).status_code == 302
    pagina = client_db.get("/jogador/dashboard")
    assert pagina.status_code == 200
    assert "Mega Evoluir" in pagina.get_data(as_text=True)
    # O POST antigo do Campo segue aceito; seu token é criado ao visitar o Campo.
    assert client_db.get("/campo").status_code == 200
    with client_db.session_transaction() as sess:
        csrf = sess["campo_csrf"]
    action = f"/campo/pokemons/{pid}/transformar"
    assert client_db.post(action, data={
        "csrf_token": "errado", "tipo": "mega", "destino_id": str(destino_id)
    }).status_code == 400
    resposta = client_db.post(action, data={
        "csrf_token": csrf, "tipo": "mega", "destino_id": str(destino_id),
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.get(Pokemon, pid).forma_temporaria_id == destino_id
    assert "Mega Evolução" in client_db.get("/campo").get_data(as_text=True)
    assert client_db.post(f"/campo/pokemons/{pid}/retirar", data={
        "csrf_token": csrf,
    }).status_code == 302
    with app_db.app_context():
        p = db.session.get(Pokemon, pid)
        assert p.forma_temporaria_id == destino_id and p.tipo_transformacao == "mega"
        assert db.session.scalar(select(func.count(PokemonEmCampo.id))) == 0


def test_limpar_campo_nao_altera_a_mega(app_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal", 0), ("charizard-mega-y", "mega", 18),
        ])
        p = _pokemon(app_db, formas["charizard"])
        _campo(app_db, p)
        _permissao(app_db, True)
        db.session.commit()
        _mudar(app_db, p, tipo="mega", destino_id=formas["charizard-mega-y"].id)
        db.session.commit()
        limpar_campo(campanha_codigo="ankar", usuario_id=str(_ids(app_db)["mestre"]))
        assert p.forma_temporaria_id == formas["charizard-mega-y"].id
        assert db.session.scalar(select(func.count(PokemonEmCampo.id))) == 0


def test_alternativa_persiste_ao_sair_do_campo_mas_e_reversivel(app_db):
    with app_db.app_context():
        formas = _familia("morpeko", [
            ("morpeko-satisfeito", "normal", 0),
            ("morpeko-faminto", "alternativa", 5),
        ])
        p = _pokemon(app_db, formas["morpeko-satisfeito"])
        _campo(app_db, p)
        db.session.commit()
        _mudar(app_db, p, tipo="alternativa", destino_id=formas["morpeko-faminto"].id)
        db.session.commit()
        retirar_pokemon(campanha_codigo="ankar", pokemon_id=str(p.id),
                       mestre=False, personagem_id=str(p.personagem_id),
                       usuario_id=str(_ids(app_db)["jogador"]))
        assert p.forma_temporaria_id == formas["morpeko-faminto"].id
        _mudar(app_db, p, tipo="reverter")
        db.session.commit()
        assert p.forma_temporaria_id is None


def test_desmaio_encerra_mega_sem_curar_pokemon(app_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal", 0), ("charizard-mega-x", "mega", 15),
        ])
        p = _pokemon(app_db, formas["charizard"])
        _campo(app_db, p)
        _permissao(app_db, True)
        db.session.commit()
        _mudar(app_db, p, tipo="mega", destino_id=formas["charizard-mega-x"].id)
        p.pv_atual = 0
        encerrar_mega_desmaio(p, str(_ids(app_db)["jogador"]))
        db.session.commit()
        assert p.forma_temporaria_id is None
        assert p.pv_atual == 0


def test_destino_de_outro_pokemon_ou_megaregional_nao_e_permitido(app_db):
    with app_db.app_context():
        formas = _familia("morpeko", [
            ("morpeko-satisfeito", "normal", 0), ("morpeko-faminto", "alternativa", 6),
        ])
        outras = _familia("charizard", [
            ("charizard", "normal", 0), ("charizard-mega-x", "mega", 18),
        ])
        p = _pokemon(app_db, formas["morpeko-satisfeito"])
        db.session.commit()
        with pytest.raises(ValueError, match="não habilitada"):
            _mudar(app_db, p, tipo="alternativa", destino_id=outras["charizard-mega-x"].id)
        db.session.rollback()
        with pytest.raises(ValueError, match="não habilitada"):
            _mudar(app_db, p, tipo="mega", destino_id=outras["charizard-mega-x"].id)
        db.session.rollback()
        assert p.forma_temporaria_id is None


def test_mega_deve_estar_revertida_antes_de_evolucao_permanente(app_db):
    with app_db.app_context():
        from app.models.db import EvolucaoPokemon
        formas = _familia("charizard", [
            ("charizard", "normal", 0), ("charizard-mega-x", "mega", 18),
        ])
        evo = _familia("outro-mon", [("outro-mon", "normal", 30)])
        p = _pokemon(app_db, formas["charizard"])
        rel = EvolucaoPokemon(
            forma_origem_id=formas["charizard"].id,
            forma_destino_id=evo["outro-mon"].id, tipo_requisito="nivel",
            requisitos={"tipo_relacao": "evolucao", "nivel": 16}, ativo=True,
        )
        db.session.add(rel)
        _campo(app_db, p)
        _permissao(app_db, True)
        db.session.commit()
        _mudar(app_db, p, tipo="mega", destino_id=formas["charizard-mega-x"].id)
        db.session.commit()
        ids = _ids(app_db)
        with pytest.raises(ValueError, match="Reverta"):
            evoluir_pokemon(
                pokemon_id=p.id, relacao_id=rel.id, personagem_id=ids["personagem"],
                campanha_id=ids["campanha"], usuario_id=ids["jogador"],
            )
        db.session.rollback()
        assert p.forma_pokemon_id == formas["charizard"].id


def test_alternativa_na_ficha_jogador_com_requisicao_e_csrf(app_db, client_db):
    with app_db.app_context():
        formas = _familia("morpeko", [
            ("morpeko-satisfeito", "normal", 0), ("morpeko-faminto", "alternativa", 6),
        ])
        p = _pokemon(app_db, formas["morpeko-satisfeito"])
        db.session.commit()
        pid, destino_id = p.id, formas["morpeko-faminto"].id
    assert client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"}).status_code == 302
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert "Morpeko-faminto" in html and "pokemon-dashboard-acao-direta" in html
    with client_db.session_transaction() as sess:
        csrf = sess["csrf_acao_evolucao"]
    url = f"/jogador/pokemon/{pid}/transformar"
    assert client_db.post(url, data={
        "csrf_token": "errado", "tipo": "alternativa", "destino_id": str(destino_id),
    }).status_code == 403
    resposta = client_db.post(url, data={
        "csrf_token": csrf, "tipo": "alternativa", "destino_id": str(destino_id),
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        p = db.session.get(Pokemon, pid)
        assert p.forma_temporaria_id == destino_id
        assert p.forma_pokemon_id != destino_id
