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
    assert 'data-pokemon-painel="formas"' in html
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


def test_campo_nao_oculta_evolucao_vermelha(app_db, client_db):
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
    assert 'data-pokemon-abrir="evolucoes"' in client_db.get("/jogador/dashboard").get_data(as_text=True)


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
    assert "img/inventory/itens/keystone.png" in mestre_html
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
    assert "Mega Evoluir" in html and "img/inventory/itens/keystone.png" in html
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


def test_keystone_local_e_css_protege_icone_do_retrato():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    assert (raiz / "static/img/inventory/itens/keystone.png").is_file()
    css = (raiz / "static/css/dashboard.css").read_text(encoding="utf-8")
    assert ".retrato-pokemon-dashboard img" not in css
    assert ".retrato-pokemon-dashboard > img" in css
    assert ".pokemon-dashboard-indicador > img" in css


def test_mega_liberada_pode_ser_acionada_sem_campo(app_db, client_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal"), ("charizard-mega-x", "mega"),
        ])
        _pokemon(app_db, formas["charizard"])
        treinador = db.session.get(Personagem, _ids(app_db)["personagem"])
        treinador.mega_habilitada = True
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert "Coloque este Pokémon no Campo" not in html
    assert 'data-pokemon-abrir="formas"' in html
    assert "img/inventory/itens/keystone.png" in html


def test_mega_exibe_motivo_quando_mestre_nao_liberou(app_db, client_db):
    with app_db.app_context():
        formas = _familia("charizard", [
            ("charizard", "normal"), ("charizard-mega-x", "mega"),
        ])
        _pokemon(app_db, formas["charizard"])
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert "Mega Evolução não liberada. Peça ao mestre" in html
    assert "img/inventory/itens/keystone.png" in html


def test_retrato_e_unico_lugar_das_acoes_no_dashboard(app_db, client_db):
    with app_db.app_context():
        formas = _familia("morpeko", [
            ("morpeko-satisfeito", "normal"), ("morpeko-faminto", "alternativa"),
        ])
        _pokemon(app_db, formas["morpeko-satisfeito"])
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert 'class="pokemon-dashboard-indicadores"' in html
    assert 'class="pokemon-dashboard-acao-direta"' in html
    assert 'class="pokemon-dashboard-transformacoes"' not in html
    assert 'data-pokemon-abrir="formas"' in html


def test_evolucao_disponivel_sem_dependencia_de_campo_ou_menu_inferior(app_db, client_db):
    with app_db.app_context():
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        destino = _familia("familia-esquerda", [("charmeleon", "normal")])["charmeleon"]
        db.session.add(EvolucaoPokemon(
            forma_origem_id=origem.id, forma_destino_id=destino.id,
            tipo_requisito="nivel", requisitos={"tipo_relacao": "evolucao", "nivel": 16},
            ativo=True,
        ))
        pokemon = _pokemon(app_db, origem)
        db.session.add(PokemonEmCampo(
            campanha_id=_ids(app_db)["campanha"], pokemon_id=pokemon.id, time_numero=1,
        ))
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert 'class="pokemon-dashboard-acao-posicao indicador-esquerda"' in html
    assert 'class="pokemon-dashboard-indicador indicador-evolucao"' in html
    assert 'class="pokemon-dashboard-transformacoes"' not in html


def test_10e4_3_morpeko_forma_unica_exibe_nome_e_imagem_no_botao(app_db, client_db):
    with app_db.app_context():
        formas = _familia("morpeko-retrato", [
            ("morpeko-satisfeito", "normal"),
            ("morpeko-faminto", "alternativa"),
        ])
        formas["morpeko-faminto"].imagem_url = "https://example.test/morpeko-faminto.png"
        _pokemon(app_db, formas["morpeko-satisfeito"])
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert 'data-pokemon-acao="alternativa"' in html
    assert '<span class="pokemon-dashboard-acao-rotulo">Morpeko-Faminto</span>' in html
    assert 'src="https://example.test/morpeko-faminto.png"' in html
    assert 'class="pokemon-dashboard-transformacoes"' not in html


def test_10e4_3_castform_varias_formas_exibem_menu_com_miniaturas(app_db, client_db):
    with app_db.app_context():
        formas = _familia("castform-retrato", [
            ("castform", "normal"),
            ("castform-ensolarado", "alternativa"),
            ("castform-chuvoso", "alternativa"),
            ("castform-nevado", "alternativa"),
        ])
        for codigo in ("castform-ensolarado", "castform-chuvoso", "castform-nevado"):
            formas[codigo].imagem_url = f"https://example.test/{codigo}.png"
        _pokemon(app_db, formas["castform"])
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert 'data-pokemon-acao="menu-formas"' in html
    assert '<span class="pokemon-dashboard-acao-rotulo">Trocar de forma</span>' in html
    for codigo, nome in (
        ("castform-ensolarado", "Castform-Ensolarado"),
        ("castform-chuvoso", "Castform-Chuvoso"),
        ("castform-nevado", "Castform-Nevado"),
    ):
        assert f'src="https://example.test/{codigo}.png"' in html
        assert f"<strong>{nome}</strong>" in html
    assert html.count('name="tipo" value="alternativa"') == 3


def test_10e4_3_blaziken_mega_unica_mostra_keystone_e_texto(app_db, client_db):
    with app_db.app_context():
        formas = _familia("blaziken", [
            ("blaziken", "normal"),
            ("blaziken-mega", "mega"),
        ])
        _pokemon(app_db, formas["blaziken"])
        personagem = db.session.get(Personagem, _ids(app_db)["personagem"])
        personagem.mega_habilitada = True
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert 'data-pokemon-acao="mega"' in html
    assert '<span class="pokemon-dashboard-acao-rotulo">Mega Evoluir</span>' in html
    assert 'src="/static/img/inventory/itens/keystone.png"' in html
    assert 'class="pokemon-dashboard-acao-posicao indicador-direita"' in html


def test_10e4_3_css_icone_nao_herda_tamanho_do_sprite_principal():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    sistema = (raiz / "static/css/sistema-ui.css").read_text(encoding="utf-8")
    dashboard = (raiz / "static/css/dashboard.css").read_text(encoding="utf-8")
    assert "body.app-shell .retrato-pokemon-dashboard img {" not in sistema
    assert "body.app-shell .retrato-pokemon-dashboard > img {" in sistema
    assert ".pokemon-dashboard-indicador > img" in dashboard
    assert ".retrato-pokemon-dashboard .pokemon-dashboard-lista-opcoes .dashboard-acao-opcao > img" in dashboard
    assert "max-width: 34px;" in dashboard and "max-height: 34px;" in dashboard
    assert "overflow-x: hidden;" in dashboard


def test_10e4_4_relacao_mega_personalizada_alimenta_painel_e_transformacao(app_db, client_db):
    """Scolipede Mega cadastrada no catálogo, não no JSON fixo."""
    from app.services.evolucoes_admin_service import salvar_relacao, desativar_relacao
    from app.services.transformacoes_service import listar_formas_temporarias, transformar_pokemon

    with app_db.app_context():
        formas = _familia("scolipede", [
            ("scolipede", "normal"), ("scolipede-mega", "mega"),
        ])
        base, destino = formas["scolipede"], formas["scolipede-mega"]
        p = _pokemon(app_db, base)
        personagem = db.session.get(Personagem, _ids(app_db)["personagem"])
        personagem.mega_habilitada = True
        db.session.commit()
        assert not listar_formas_temporarias(p)["mega"]

        relacao, erros = salvar_relacao(base, {
            "destino_id": str(destino.id),
            "tipo_relacao": "mega",
            "tipo_requisito": "especial",
            "fonte": "mestre",
            "condicao": "",
            "item_nome": "",
        }, usuario_id=None)
        assert not erros and relacao is not None
        relacao_id = str(relacao.id)
        assert [f.id for f in listar_formas_temporarias(p)["mega"]] == [destino.id]
        pid = p.id
        destino_id = destino.id
        original_id = base.id

    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert 'data-pokemon-acao="mega"' in html
    assert "Mega Evoluir" in html
    assert "img/inventory/itens/keystone.png" in html

    with app_db.app_context():
        ids = _ids(app_db)
        msg = transformar_pokemon(
            pokemon_id=pid, destino_id=destino_id, tipo="mega",
            usuario_id=ids["jogador"], personagem_id=ids["personagem"],
            campanha_id=ids["campanha"],
        )
        db.session.commit()
        p = db.session.get(Pokemon, pid)
        assert "Mega" in msg
        assert p.forma_pokemon_id == original_id
        assert p.forma_temporaria_id == destino_id
        assert p.tipo_transformacao == "mega"

        # Desativar a ligação bloqueia futuras escolhas sem apagar Pokémon.
        assert desativar_relacao(base, relacao_id, usuario_id=None)
        assert listar_formas_temporarias(p)["mega"] == []


def test_10e4_4_catalogo_reconhece_mega_na_pesquisa_e_exige_mesma_especie(app_db, client_db):
    from app.services.evolucoes_admin_service import salvar_relacao
    with app_db.app_context():
        formas = _familia("scolipede", [
            ("scolipede", "normal"), ("scolipede-mega", "mega"),
        ])
        base, destino = formas["scolipede"], formas["scolipede-mega"]
        base_id, destino_id = base.id, destino.id
        outra = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        _, erros = salvar_relacao(base, {
            "destino_id": str(outra.id),
            "tipo_relacao": "mega",
            "tipo_requisito": "especial",
            "fonte": "mestre",
        }, usuario_id=None)
        assert any("mesma espécie" in erro for erro in erros)
        db.session.rollback()
        db.session.commit()
    _login(client_db, mestre=True)
    html = client_db.get(
        f"/mestre/catalogo/pokemons/{base_id}/relacoes?q=Scoli"
    ).get_data(as_text=True)
    assert f'data-categoria="mega"' in html
    assert str(destino_id) in html
    assert 'data-relacao-nova' in html
    assert "relacoes-pokemon.js" in html
    assert "Não é necessário cadastrar pedra ou item" in html


def test_10e4_4_confirmacao_e_modal_local_sem_window_confirm(app_db, client_db):
    from pathlib import Path
    with app_db.app_context():
        formas = _familia("morpeko-modal", [
            ("morpeko-satisfeito", "normal"),
            ("morpeko-faminto", "alternativa"),
        ])
        _pokemon(app_db, formas["morpeko-satisfeito"])
        db.session.commit()
    _login(client_db)
    html = client_db.get("/jogador/dashboard").get_data(as_text=True)
    assert "<dialog" in html
    assert "data-pokemon-confirmacao-modal" in html
    assert 'data-pokemon-confirmacao-aceitar' in html
    assert 'data-confirmacao="Mudar para Morpeko-Faminto?"' in html
    js = (Path(__file__).resolve().parents[1] / "static/js/dashboard-pokemon.js").read_text(encoding="utf-8")
    assert "window.confirm(" not in js
    assert "modal.showModal()" in js
    assert "formulario.requestSubmit" in js
