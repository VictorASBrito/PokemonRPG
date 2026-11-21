"""10D.4.5 — Painel do NPC com controle da equipe e acesso exclusivo do mestre."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import NPCModelo, Pokemon
from app.services.npc_ficha_service import opcoes_edicao_npc


def login(client, usuario="mestre-db", senha="senha-db"):
    assert client.post("/login", data={"login": usuario, "senha": senha}).status_code == 302


def criar_npc(app, client):
    assert client.get("/mestre/catalogo/npcs/novo").status_code == 200
    with client.session_transaction() as sess:
        csrf = sess["npc_catalogo_csrf"]
    dados = {
        "csrf_token": csrf, "nome": "Comandante Íris",
        "nivel": "35", "classe": "Comandante",
        "anotacoes": "Informação reservada à narrativa.",
    }
    with app.app_context():
        from app.services.npc_ficha_service import dados_ficha_npc
        regras = dados_ficha_npc(campanha_codigo="ankar")["regras"]
        for atributo in regras["atributos"]:
            dados[f'atributo_{atributo["id"]}'] = str(atributo["valor_inicial"])
    r = client.post("/mestre/catalogo/npcs/novo", data=dados)
    assert r.status_code == 302
    with app.app_context():
        modelo = db.session.scalar(select(NPCModelo))
        return str(modelo.id), csrf


def test_painel_npc_exibe_resumo_e_equipe_sem_login_de_jogador(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    resposta = client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    })
    assert resposta.status_code == 302
    pagina = client_db.get(f"/mestre/catalogo/npcs/{modelo_id}/painel")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    for trecho in (
        "Comandante Íris", "Treinador NPC", "Atributos atuais",
        "Golpes equipados", "Gerenciar integrante", "Salvar Pokémon",
        "Ações rápidas", 'data-dashboard-pokemon-grid',
        'data-dashboard-pokemon-card', 'data-pokemon-id="0"',
        "Natureza", "Gênero", "Shiny", "Recolher",
        "Anotações do mestre",
    ):
        assert trecho in html
    assert f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar" in html
    assert "/static/js/dashboard-pokemon.js" in html
    assert "/static/js/npc-painel.js" in html
    catalogo = client_db.get("/mestre/catalogo/npcs").get_data(as_text=True)
    assert f"/mestre/catalogo/npcs/{modelo_id}/painel" in catalogo
    assert "Painel NPC" in catalogo
    with app_db.app_context():
        assert db.session.scalar(select(func.count()).select_from(Pokemon)) == 0


def test_editar_nome_natureza_genero_shiny_e_dados_persistem_no_modelo(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    assert client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    }).status_code == 302
    with app_db.app_context():
        generos = opcoes_edicao_npc(campanha_codigo="ankar")["generos"]
        genero = generos[-1]
    url = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar"
    resposta = client_db.post(url, data={
        "csrf_token": csrf, "foco": "0", "origem": "painel",
        "nome": "Verde", "forma_id": forma, "natureza_id": "",
        "genero": genero, "shiny": "1", "golpe_nome": ["", "", "", ""],
    })
    assert resposta.status_code == 302
    assert "/painel?foco=0" in resposta.headers["Location"]
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        assert len(modelo.equipe) == 1
        item = modelo.equipe[0]
        assert item["nome"] == "Verde" and item["shiny"] is True
        assert item["genero"] == genero
        assert item["forma_id"] == forma
        assert item["golpes"] == []
    assert "Verde" in client_db.get(resposta.headers["Location"]).get_data(as_text=True)


def test_reordenar_equipe_e_pv_no_painel(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    for codigo in ("bulbasaur", "charmander"):
        assert client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
            "csrf_token": csrf, "forma_id": app_db.config["TEST_IDS"]["formas"][codigo],
            "origem": "painel",
        }).status_code == 302
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        ids_antes = [m["forma_id"] for m in modelo.equipe]
        pv_antes = int(modelo.equipe[0]["pv_atual"])
    pv = client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/pv", data={
        "csrf_token": csrf, "origem": "painel", "foco": "0",
        "quantidade": "4", "operacao": "menos",
    })
    assert pv.status_code == 302 and "/painel" in pv.headers["Location"]
    mover = client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/mover", data={
        "csrf_token": csrf, "origem": "painel", "foco": "1",
        "direcao": "baixo",
    })
    assert mover.status_code == 302
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        assert [m["forma_id"] for m in modelo.equipe] == ids_antes[::-1]
        assert modelo.equipe[1]["pv_atual"] == pv_antes - 4


def test_painel_somente_mestre_valida_csrf_e_campanha(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    url = f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar"
    assert client_db.post(url, data={"csrf_token": "errado", "forma_id": forma}).status_code == 400
    assert client_db.post(url, data={"csrf_token": csrf, "forma_id": forma}).status_code == 302
    editar = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar"
    assert client_db.post(editar, data={
        "csrf_token": "errado", "nome": "Invasor",
    }).status_code == 400
    with app_db.app_context():
        assert db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe[0]["nome"] != "Invasor"
    client_db.post("/logout")
    login(client_db, "bartz-db", "abc123")
    assert client_db.get(f"/mestre/catalogo/npcs/{modelo_id}/painel").status_code in (302, 403)
    assert client_db.post(editar, data={"csrf_token": csrf, "nome": "Invasor"}).status_code in (302, 403)


def test_painel_rejeita_edicao_invalida_e_indice_fora_da_equipe(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    })
    url = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar"
    assert client_db.post(url, data={
        "csrf_token": csrf, "origem": "painel",
        "forma_id": forma, "natureza_id": "uuid-invalido", "genero": "Ø",
    }).status_code == 302
    assert client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/5/mover", data={
        "csrf_token": csrf, "origem": "painel", "direcao": "cima",
    }).status_code == 302
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        assert len(modelo.equipe) == 1
        assert modelo.equipe[0]["forma_id"] == forma


def test_catalogo_de_golpes_e_natureza_atualiza_painel_npc(app_db, client_db):
    from app.models.db import Golpe, Natureza
    from app.services.npc_ficha_service import ficha_card_npc

    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    })
    with app_db.app_context():
        natureza = db.session.scalar(select(Natureza).where(Natureza.codigo == "valente"))
        arranhao = db.session.scalar(select(Golpe).where(Golpe.codigo == "arranhao"))
        chamas = db.session.scalar(select(Golpe).where(Golpe.codigo == "ataque-de-chamas"))
        inicial = ficha_card_npc(campanha_codigo="ankar", modelo_id=modelo_id)["equipe"][0]
        atk_inicial = inicial["totais"]["ataque"]
    edicao = client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar", data={
        "csrf_token": csrf, "origem": "painel", "foco": "0",
        "nome": "Tropa Verde", "forma_id": forma, "natureza_id": str(natureza.id),
        "genero": "Ø", "golpe_nome": ["Arranhão", "Ataque de Chamas", "", ""],
    })
    assert edicao.status_code == 302
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        assert modelo.equipe[0]["golpes"] == [str(arranhao.id), str(chamas.id)]
        card = ficha_card_npc(campanha_codigo="ankar", modelo_id=modelo_id)["equipe"][0]
        assert card["totais"]["ataque"] > atk_inicial
        assert [g["nome"] for g in card["golpes"]] == ["Arranhão", "Ataque de Chamas"]
        assert card["natureza"] == "Valente"
    html = client_db.get(f"/mestre/catalogo/npcs/{modelo_id}/painel?foco=0").get_data(as_text=True)
    assert "Tropa Verde" in html
    assert "Arranhão" in html and "Ataque de Chamas" in html
    assert "Valente" in html
    assert 'data-seletor-inicial="Bulbasaur"' in html


def test_mudar_especie_preserva_dano_e_rejeita_golpes_repetidos(app_db, client_db):
    from app.models.db import Golpe
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    bulbasaur = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    charmander = app_db.config["TEST_IDS"]["formas"]["charmander"]
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": bulbasaur,
    })
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        inicial = modelo.equipe[0]["pv_atual"]
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/pv", data={
        "csrf_token": csrf, "quantidade": "3", "operacao": "menos",
    })
    response = client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar", data={
        "csrf_token": csrf, "origem": "painel", "nome": "Meu Charmander",
        "forma_id": charmander, "natureza_id": "", "genero": "Ø",
        "golpe_nome": ["", "", "", ""],
    })
    assert response.status_code == 302
    with app_db.app_context():
        from app.services.campo_npc_service import _pv_maximo
        from app.services.pokemon_db_service import carregar_regras_pokemon_db
        from app.services.npc_ficha_service import _nivel
        from app.models.db import FormaPokemon
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        item = modelo.equipe[0]
        forma = db.session.get(FormaPokemon, uuid.UUID(charmander))
        regras = carregar_regras_pokemon_db(modelo.campanha_id)
        assert item["pv_atual"] == _pv_maximo(forma, _nivel(modelo), regras) - 3
        assert item["forma_id"] == charmander
        golpe = db.session.scalar(select(Golpe).where(Golpe.codigo == "arranhao"))
        nome_golpe = golpe.nome
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/editar", data={
        "csrf_token": csrf, "origem": "painel", "nome": "Tentativa",
        "forma_id": charmander, "genero": "Ø",
        "golpe_nome": [nome_golpe, nome_golpe, "", ""],
    })
    with app_db.app_context():
        item = db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe[0]
        assert item["nome"] == "Meu Charmander"
        assert item.get("golpes") == []


def test_painel_npc_mantem_mesmo_layout_de_combate_sem_formularios_dentro_da_grade(app_db, client_db):
    """Blocos expandidos espelham os do jogador; gerenciamento fica fora da grade."""
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    forma = app_db.config["TEST_IDS"]["formas"]["bulbasaur"]
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": forma,
    })
    html = client_db.get(f"/mestre/catalogo/npcs/{modelo_id}/painel?foco=0").get_data(as_text=True)
    assert 'data-dashboard-pokemon-grid' in html
    assert 'class="dashboard-jogador npc-painel"' in html
    assert 'class="npc-painel-cabecalho"' not in html
    grade = html.split('data-dashboard-pokemon-grid', 1)[1].split('</section>', 1)[0]
    # Ações e campos nunca devem disputar a altura da área de golpes.
    cartao = html.split('data-dashboard-pokemon-card', 1)[1].split('</article>', 1)[0]
    assert '<form' not in cartao
    assert 'pokemon-dashboard-atributos-totais' in cartao
    assert 'pokemon-dashboard-lista-golpes-detalhados' in cartao
    assert 'pokemon-dashboard-golpes-detalhados' in cartao
    assert 'pokemon-dashboard-acoes-expandidas' in cartao
    assert 'data-npc-dialog-open="npc-editar-0"' in cartao
    assert 'data-npc-dialog-open="npc-acoes-0"' in cartao
    for legenda in ('Natureza', 'Gênero', 'Status', 'Item', 'Variação', 'Nível'):
        assert f'<span>{legenda}</span>' in cartao
    assert 'id="npc-editar-0"' in html
    assert 'id="npc-acoes-0"' in html
    assert 'id="npc-pv-treinador"' in html
    assert 'id="npc-adicionar-pokemon"' in html
    assert 'data-npc-dialog-open="npc-adicionar-pokemon"' in html
    assert 'data-npc-confirm-dialog' in html
    assert 'name="golpe_nome"' in html


def test_modais_npc_respeitam_grade_compartilhada_e_escape():
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    js = (raiz / "static/js/npc-painel.js").read_text(encoding="utf-8")
    css = (raiz / "static/css/npc-painel.css").read_text(encoding="utf-8")
    template = (raiz / "templates/mestre/catalogo/npc_painel.html").read_text(encoding="utf-8")
    assert 'dialogo.showModal()' in js
    assert 'evento.stopPropagation()' in js
    assert "document.querySelector('dialog[open]')" in js
    assert 'form.requestSubmit()' in js
    assert 'window.confirm(' not in js
    assert 'npc-painel-dialog-editar' in css
    assert 'max-height: min(85dvh, 760px)' in css
    assert 'npc-painel-cabecalho' not in template
    assert '<section class="pokemon-dashboard-painel-detalhe npc-painel-edicao">' not in template
    assert '<section class="pokemon-dashboard-painel-detalhe npc-painel-controles">' not in template
    assert 'data-npc-dialog-close' in template


# 10D.4.7 — relações personalizadas e modos do NPC (sem criar Pokemon/Personagem).
def _familia_de_teste(codigo, definicoes):
    from decimal import Decimal
    from app.models.db import EspeciePokemon, FormaPokemon, FormaPokemonAtributo
    especie = EspeciePokemon(codigo=codigo, nome=codigo.title(), ativo=True)
    db.session.add(especie)
    db.session.flush()
    referencia = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
    formas = {}
    for nome, categoria in definicoes:
        f = FormaPokemon(
            especie=especie, codigo=nome, nome=nome.title(), categoria=categoria,
            ativo=True, imagem_url=f"https://example.test/{nome}.png",
        )
        db.session.add(f)
        db.session.flush()
        for atributo in referencia.atributos_base:
            db.session.add(FormaPokemonAtributo(
                forma_pokemon=f, atributo=atributo.atributo,
                valor_base=Decimal(atributo.valor_base) + (30 if categoria == "mega" else 5),
            ))
        formas[nome] = f
    db.session.flush()
    return formas


def test_npc_mega_por_relacao_e_reversao_sem_perder_original(app_db, client_db):
    from app.models.db import EvolucaoPokemon
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    with app_db.app_context():
        formas = _familia_de_teste("scolipede-npc", [
            ("scolipede-npc", "normal"), ("scolipede-npc-mega", "mega"),
        ])
        original, mega = formas["scolipede-npc"], formas["scolipede-npc-mega"]
        db.session.add(EvolucaoPokemon(
            forma_origem_id=original.id, forma_destino_id=mega.id,
            tipo_requisito="especial", requisitos={"tipo_relacao": "mega"}, ativo=True,
        ))
        db.session.commit()
        base_id, mega_id = str(original.id), str(mega.id)
    url_painel = f"/mestre/catalogo/npcs/{modelo_id}/painel"
    url_acao = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/transformar"
    assert client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": base_id,
    }).status_code == 302
    html = client_db.get(url_painel).get_data(as_text=True)
    assert 'class="pokemon-dashboard-indicadores"' in html
    assert "Mega Evoluir" in html
    assert "img/inventory/itens/keystone.png" in html
    assert f'name="destino_id" value="{mega_id}"' in html
    assert 'aria-label="Seções do catálogo"' not in html

    resposta = client_db.post(url_acao, data={
        "csrf_token": csrf, "tipo": "mega", "destino_id": mega_id, "foco": "0",
    })
    assert resposta.status_code == 302 and "/painel?foco=0" in resposta.headers["Location"]
    with app_db.app_context():
        modelo = db.session.get(NPCModelo, uuid.UUID(modelo_id))
        item = modelo.equipe[0]
        assert item["forma_id"] == base_id
        assert item["forma_temporaria_id"] == mega_id
        assert item["tipo_transformacao"] == "mega"
        pv_mega = item["pv_atual"]
    html = client_db.get(url_painel).get_data(as_text=True)
    assert "Scolipede-Npc-Mega" in html
    assert "Reverter forma" in html
    assert str(pv_mega) in html
    resposta = client_db.post(url_acao, data={"csrf_token": csrf, "tipo": "reverter", "foco": "0"})
    assert resposta.status_code == 302
    with app_db.app_context():
        membro = db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe[0]
        assert membro["forma_id"] == base_id
        assert membro["forma_temporaria_id"] is None
        assert membro["tipo_transformacao"] is None


def test_npc_castform_multiplas_formas_troca_sem_alterar_permanente(app_db, client_db):
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    with app_db.app_context():
        formas = _familia_de_teste("castform-npc", [
            ("castform-npc", "normal"),
            ("castform-npc-sol", "alternativa"), ("castform-npc-chuva", "alternativa"),
            ("castform-npc-neve", "alternativa"),
        ])
        db.session.commit()
        base = str(formas["castform-npc"].id)
        chuva = str(formas["castform-npc-chuva"].id)
        sol = str(formas["castform-npc-sol"].id)
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
        "csrf_token": csrf, "forma_id": base,
    })
    html = client_db.get(f"/mestre/catalogo/npcs/{modelo_id}/painel").get_data(as_text=True)
    assert "Trocar de forma" in html
    for nome in ("Castform-Npc-Sol", "Castform-Npc-Chuva", "Castform-Npc-Neve"):
        assert nome in html
    for codigo in ("castform-npc-sol", "castform-npc-chuva", "castform-npc-neve"):
        assert f"https://example.test/{codigo}.png" in html
    url = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/transformar"
    for destino in (chuva, sol):
        assert client_db.post(url, data={
            "csrf_token": csrf, "tipo": "alternativa", "destino_id": destino, "foco": "0",
        }).status_code == 302
    with app_db.app_context():
        membro = db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe[0]
        assert membro["forma_id"] == base
        assert membro["forma_temporaria_id"] == sol
        assert membro["tipo_transformacao"] == "alternativa"
    assert 'aria-label="Seções do catálogo"' not in html
    catalogo = client_db.get("/mestre/catalogo/npcs").get_data(as_text=True)
    assert 'aria-label="Seções do catálogo"' in catalogo


def test_npc_mega_exclusiva_por_treinador_e_rejeita_destino_invalido(app_db, client_db):
    from app.models.db import EvolucaoPokemon
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    with app_db.app_context():
        formas = _familia_de_teste("mega-dupla-npc", [
            ("mega-dupla-npc", "normal"), ("mega-dupla-npc-x", "mega"),
        ])
        base_id, mega_id = str(formas["mega-dupla-npc"].id), str(formas["mega-dupla-npc-x"].id)
        db.session.add(EvolucaoPokemon(
            forma_origem_id=formas["mega-dupla-npc"].id,
            forma_destino_id=formas["mega-dupla-npc-x"].id,
            tipo_requisito="especial", requisitos={"tipo_relacao": "mega"}, ativo=True,
        ))
        db.session.commit()
    for _ in range(2):
        assert client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={
            "csrf_token": csrf, "forma_id": base_id,
        }).status_code == 302
    url0 = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/transformar"
    url1 = f"/mestre/catalogo/npcs/{modelo_id}/equipe/1/transformar"
    assert client_db.post(url0, data={"csrf_token": csrf, "tipo": "mega", "destino_id": mega_id}).status_code == 302
    assert client_db.post(url1, data={"csrf_token": csrf, "tipo": "mega", "destino_id": mega_id}).status_code == 302
    assert client_db.post(url1, data={"csrf_token": csrf, "tipo": "mega", "destino_id": base_id}).status_code == 302
    with app_db.app_context():
        membros = db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe
        assert membros[0]["tipo_transformacao"] == "mega"
        assert not membros[1].get("forma_temporaria_id")
        assert membros[1]["forma_id"] == base_id
    # CSRF obrigatório; jogadores não podem acionar rotas do mestre.
    assert client_db.post(url0, data={"csrf_token": "invalido", "tipo": "reverter"}).status_code == 400
    client_db.post("/logout")
    login(client_db, "bartz-db", "abc123")
    assert client_db.post(url0, data={"csrf_token": csrf, "tipo": "reverter"}).status_code in (302, 403)
    with app_db.app_context():
        membro = db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe[0]
        assert membro["tipo_transformacao"] == "mega"


def test_npc_mega_reverte_ao_desmaiar_e_editando_forma_base(app_db, client_db):
    from app.models.db import EvolucaoPokemon
    login(client_db)
    modelo_id, csrf = criar_npc(app_db, client_db)
    with app_db.app_context():
        formas = _familia_de_teste("mega-ko-npc", [
            ("mega-ko-npc", "normal"), ("mega-ko-npc-x", "mega"),
        ])
        base, mega = str(formas["mega-ko-npc"].id), str(formas["mega-ko-npc-x"].id)
        db.session.add(EvolucaoPokemon(
            forma_origem_id=formas["mega-ko-npc"].id,
            forma_destino_id=formas["mega-ko-npc-x"].id,
            tipo_requisito="especial", requisitos={"tipo_relacao": "mega"}, ativo=True,
        ))
        db.session.commit()
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/adicionar", data={"csrf_token": csrf, "forma_id": base})
    transform_url = f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/transformar"
    client_db.post(transform_url, data={"csrf_token": csrf, "tipo": "mega", "destino_id": mega})
    client_db.post(f"/mestre/catalogo/npcs/{modelo_id}/equipe/0/pv", data={
        "csrf_token": csrf, "operacao": "menos", "quantidade": "9999",
    })
    with app_db.app_context():
        membro = db.session.get(NPCModelo, uuid.UUID(modelo_id)).equipe[0]
        assert membro["pv_atual"] <= 0
        assert membro["forma_temporaria_id"] is None
        assert membro["tipo_transformacao"] is None
