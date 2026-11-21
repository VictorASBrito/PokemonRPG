"""10E.4.1 — Interface única de evolução, formas e Mega no expandido."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    EspeciePokemon, EvolucaoPokemon, FormaPokemon, FormaPokemonAtributo,
    Personagem, Pokemon, PokemonEmCampo,
)
from app.services.pokemon_db_service import calcular_pokemon, carregar_regras_pokemon_db


def _ids(app):
    return {k: uuid.UUID(v) for k, v in app.config["TEST_IDS"].items() if k != "formas"}


def _familia(codigo: str, formas: list[tuple[str, str]]) -> dict[str, FormaPokemon]:
    especie = EspeciePokemon(codigo=codigo, nome=codigo.title(), ativo=True)
    db.session.add(especie)
    db.session.flush()
    base = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
    saida = {}
    for cod, categoria in formas:
        forma = FormaPokemon(especie=especie, codigo=cod, nome=cod.title(), categoria=categoria, ativo=True)
        db.session.add(forma)
        db.session.flush()
        for attr in base.atributos_base:
            db.session.add(FormaPokemonAtributo(
                forma_pokemon=forma,
                atributo=attr.atributo,
                valor_base=Decimal(attr.valor_base) + 8,
            ))
        saida[cod] = forma
    db.session.flush()
    return saida


def _pokemon(app, forma, *, pos=1, pv=20):
    obj = Pokemon(
        personagem_id=_ids(app)["personagem"],
        forma_pokemon_id=forma.id, apelido="Parceiro",
        genero="Macho", pv_atual=pv,
        localizacao="equipe", posicao=pos, ativo=True,
    )
    db.session.add(obj)
    db.session.flush()
    personagem = db.session.get(Personagem, _ids(app)["personagem"])
    regras = carregar_regras_pokemon_db(personagem.campanha_id)
    obj.pv_atual = calcular_pokemon(obj, personagem, regras)["totais"]["pv"]
    db.session.flush()
    return obj


def _login(client, mestre=False):
    return client.post("/login", data={
        "login": "mestre-db" if mestre else "bartz-db",
        "senha": "senha-db" if mestre else "abc123",
    })


def _csrf(client, chave):
    with client.session_transaction() as sess:
        return sess[chave]


def test_uma_alternativa_usa_sprite_e_nome_diretamente_no_expandido(app_db, client_db):
    with app_db.app_context():
        formas = _familia("morpeko", [
            ("morpeko-satisfeito", "normal"), ("morpeko-faminto", "alternativa"),
        ])
        p = _pokemon(app_db, formas["morpeko-satisfeito"])
        db.session.commit()
        pid, fid = p.id, formas["morpeko-faminto"].id
    assert _login(client_db).status_code == 302
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert 'class="pokemon-dashboard-acao-direta"' in html
    assert "Morpeko-Faminto" in html
    assert "Mudar de forma</summary>" not in html
    assert 'img/mudanca-forma.svg' in html
    assert "Mega Evoluir" not in html
    token = _csrf(client_db, "csrf_acao_evolucao")
    resposta = client_db.post(f"/jogador/pokemon/{pid}/transformar", data={
        "csrf_token": token, "origem": "painel",
        "tipo": "alternativa", "destino_id": str(fid),
    })
    assert resposta.status_code == 302
    assert f"foco={pid}" in resposta.headers["Location"]
    with app_db.app_context():
        p = db.session.get(Pokemon, pid)
        assert p.forma_temporaria_id == fid
        assert p.forma_pokemon_id != fid
    assert "Reverter forma" in client_db.get("/jogador/dashboard").get_data(as_text=True)


def test_varias_alternativas_abrem_menu_com_sprites_e_nomes(app_db, client_db):
    with app_db.app_context():
        formas = _familia("rotom", [
            ("rotom", "normal"), ("rotom-microondas", "alternativa"),
            ("rotom-geladeira", "alternativa"),
        ])
        _pokemon(app_db, formas["rotom"])
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert "Mudar de forma</summary>" in html
    assert "Rotom-Microondas" in html and "Rotom-Geladeira" in html
    assert html.count('name="tipo" value="alternativa"') == 2
    assert 'data-pokemon-abrir="formas"' in html


def test_evolucao_vermelha_so_quando_pode_evoluir_e_retorna_ao_painel(app_db, client_db):
    with app_db.app_context():
        formas = _familia("charmander-family-ui", [
            ("charmeleon", "normal"),
        ])
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        destino = formas["charmeleon"]
        rel = EvolucaoPokemon(
            forma_origem_id=origem.id, forma_destino_id=destino.id,
            tipo_requisito="nivel",
            requisitos={"tipo_relacao": "evolucao", "nivel": 16},
            ativo=True,
        )
        db.session.add(rel)
        p = _pokemon(app_db, origem)
        db.session.commit()
        pid, rid, dest = p.id, rel.id, destino.id
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert "evolucao-disponivel.svg" in html
    assert 'data-pokemon-abrir="evolucoes"' in html
    assert "Charmeleon" in html
    csrf = _csrf(client_db, "csrf_acao_evolucao")
    resposta = client_db.post(f"/jogador/pokemon/{pid}/evolucoes/{rid}/evoluir", data={
        "csrf_token": csrf, "origem": "painel",
    })
    assert resposta.status_code == 302
    assert f"foco={pid}" in resposta.headers["Location"]
    with app_db.app_context():
        assert db.session.get(Pokemon, pid).forma_pokemon_id == dest
    assert 'data-pokemon-abrir="evolucoes"' not in client_db.get("/jogador/dashboard").get_data(as_text=True)


def test_em_campo_oculta_evolucao_vermelha_ate_pokemon_sair(app_db, client_db):
    with app_db.app_context():
        formas = _familia("linha-pokemon", [("evoluido", "normal")])
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        rel = EvolucaoPokemon(
            forma_origem_id=origem.id, forma_destino_id=formas["evoluido"].id,
            tipo_requisito="nivel", requisitos={"tipo_relacao": "evolucao", "nivel": 16},
            ativo=True,
        )
        db.session.add(rel)
        p = _pokemon(app_db, origem)
        db.session.add(PokemonEmCampo(
            campanha_id=_ids(app_db)["campanha"], pokemon_id=p.id, time_numero=1,
        ))
        db.session.commit()
    _login(client_db)
    assert 'data-pokemon-abrir="evolucoes"' not in client_db.get("/jogador/dashboard").get_data(as_text=True)


def test_mega_trainer_menu_tres_pontos_sem_pedra_e_fluxo_expandido(app_db, client_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal"),
            ("charizard-mega-x", "mega"),
            ("charizard-mega-y", "mega"),
        ])
        p = _pokemon(app_db, formas["charizard"])
        db.session.add(PokemonEmCampo(
            campanha_id=_ids(app_db)["campanha"], pokemon_id=p.id, time_numero=1,
        ))
        db.session.commit()
        pid, fid, dono_id, origem_id = p.id, formas["charizard-mega-x"].id, p.personagem_id, formas["charizard"].id
    _login(client_db, mestre=True)
    mestre_html = client_db.get("/mestre/dashboard").get_data(as_text=True)
    assert 'data-menu-opcoes' in mestre_html
    assert "Permitir Mega Evolução" in mestre_html
    assert "mega-pedra-ankar.svg" in mestre_html
    assert 'role="switch"' in mestre_html
    assert "mega_habilitada" not in mestre_html  # campo interno não vaza no HTML
    token = _csrf(client_db, "perfil_csrf")
    negar = client_db.post(f"/mestre/painel/jogadores/{dono_id}/mega", data={
        "csrf_token": "incorreto", "habilitar": "1",
    })
    assert negar.status_code == 403
    resposta = client_db.post(f"/mestre/painel/jogadores/{dono_id}/mega", data={
        "csrf_token": token, "habilitar": "1",
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.get(Personagem, dono_id).mega_habilitada is True
    client_db.post("/logout")
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert "Mega Evoluir" in html and "mega-pedra-ankar.svg" in html
    assert "Charizard-Mega-X" in html and "Charizard-Mega-Y" in html
    csrf = _csrf(client_db, "csrf_acao_evolucao")
    r = client_db.post(f"/jogador/pokemon/{pid}/transformar", data={
        "csrf_token": csrf, "origem": "painel",
        "tipo": "mega", "destino_id": str(fid),
    })
    assert r.status_code == 302
    assert f"foco={pid}" in r.headers["Location"]
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, pid)
        assert pokemon.forma_temporaria_id == fid
        assert pokemon.forma_pokemon_id == origem_id


def test_preview_mestre_nao_recebe_botoes_de_evolucao_do_jogador(app_db, client_db):
    with app_db.app_context():
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        destino = _familia("ui-preview", [("charmeleon", "normal")])["charmeleon"]
        db.session.add(EvolucaoPokemon(
            forma_origem_id=origem.id, forma_destino_id=destino.id,
            tipo_requisito="nivel", requisitos={"tipo_relacao": "evolucao", "nivel": 16},
            ativo=True,
        ))
        _pokemon(app_db, origem)
        db.session.commit()
        personagem_id = _ids(app_db)["personagem"]
    _login(client_db, mestre=True)
    html = client_db.get(f"/mestre/jogadores/{personagem_id}/preview").get_data(as_text=True)
    assert "Visualização como jogador" in html
    assert 'data-pokemon-abrir="evolucoes"' not in html
    assert "Evoluir" not in html
