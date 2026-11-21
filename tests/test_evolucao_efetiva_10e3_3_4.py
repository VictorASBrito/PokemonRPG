"""10E.3.3/4 — Evolução opcional e transacional de Pokémon de Ankar."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    Atributo, AutorizacaoEvolucaoPokemon, EspeciePokemon, EvolucaoPokemon,
    FormaPokemon, FormaPokemonAtributo, HistoricoAlteracao, Item,
    Personagem, PersonagemItem, Pokemon, PokemonEmCampo,
)
from app.services.autorizacao_evolucao_service import autorizar_evolucao_individual
from app.services.consulta_evolucao_service import consultar_evolucoes_pokemon
from app.services.evolucao_efetiva_service import evoluir_pokemon
from app.services.pokemon_db_service import calcular_pokemon, carregar_regras_pokemon_db


def _ids(app):
    return {k: uuid.UUID(v) for k, v in app.config["TEST_IDS"].items() if k != "formas"}


def _form(codigo, aumento=0):
    forma = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == codigo))
    if forma is not None:
        return forma
    base = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
    especie = EspeciePokemon(codigo=codigo, nome=codigo.capitalize(), ativo=True)
    forma = FormaPokemon(
        especie=especie, codigo=codigo, nome=codigo.capitalize(),
        categoria="normal", ativo=True,
    )
    db.session.add(forma)
    db.session.flush()
    for item in base.atributos_base:
        db.session.add(FormaPokemonAtributo(
            forma_pokemon=forma, atributo=item.atributo,
            valor_base=Decimal(item.valor_base) + Decimal(aumento),
        ))
    db.session.flush()
    return forma


def _relacao(origem, destino, *, tipo="nivel", req=None):
    r = EvolucaoPokemon(
        forma_origem_id=origem.id, forma_destino_id=destino.id,
        tipo_requisito=tipo,
        requisitos=req if req is not None else {"tipo_relacao": "evolucao", "nivel": 16},
        ativo=True,
    )
    db.session.add(r)
    db.session.flush()
    return r


def _pokemon(app, forma, *, posicao=1, shiny=False):
    ids = _ids(app)
    p = Pokemon(
        personagem_id=ids["personagem"], forma_pokemon_id=forma.id,
        apelido="Parceiro", genero="Macho", shiny=shiny,
        pv_atual=1, localizacao="box", posicao=posicao, ativo=True,
    )
    db.session.add(p)
    db.session.flush()
    char = db.session.get(Personagem, ids["personagem"])
    regras = carregar_regras_pokemon_db(char.campanha_id)
    p.pv_atual = max(1, calcular_pokemon(p, char, regras)["totais"]["pv"] - 10)
    db.session.flush()
    return p


def _material(app, codigo, nome, qtd, *, consumivel=True, ativo=True):
    item = Item(
        codigo=codigo, nome=nome, preco=200, consumivel=consumivel, ativo=ativo,
    )
    db.session.add(item)
    db.session.flush()
    registro = PersonagemItem(
        personagem_id=_ids(app)["personagem"], item_id=item.id, quantidade=qtd,
    )
    db.session.add(registro)
    db.session.flush()
    return registro


def _evoluir(app, pokemon, relacao, **kwargs):
    ids = _ids(app)
    return evoluir_pokemon(
        pokemon_id=pokemon.id, relacao_id=relacao.id,
        personagem_id=ids["personagem"], campanha_id=ids["campanha"],
        usuario_id=ids["jogador"], **kwargs,
    )


def _autorizar(app, pokemon, relacao):
    ids = _ids(app)
    autorizar_evolucao_individual(
        pokemon_id=pokemon.id, relacao_id=relacao.id,
        usuario_id=ids["mestre"], campanha_id=ids["campanha"],
        motivo="Missão de evolução especial autorizada pelo mestre",
    )


def _login(client, login, senha):
    return client.post("/login", data={"login": login, "senha": senha})


def test_evolucao_por_nivel_preserva_identidade_dano_e_historico(app_db):
    with app_db.app_context():
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        destino = _form("charmeleon", aumento=12)
        rel = _relacao(origem, destino)
        pokemon = _pokemon(app_db, origem, shiny=True)
        char = db.session.get(Personagem, _ids(app_db)["personagem"])
        regras = carregar_regras_pokemon_db(char.campanha_id)
        pv_antes = pokemon.pv_atual
        forma_antes = pokemon.forma_pokemon_id
        id_pokemon = pokemon.id
        db.session.commit()

        resultado = _evoluir(app_db, pokemon, rel)
        db.session.commit()
        assert resultado.pv_novo == resultado.pv_maximo_novo - 10
        assert resultado.pv_anterior == pv_antes
        assert resultado.pv_maximo_novo > resultado.pv_maximo_anterior
        assert resultado.item_consumido is None
        salvo = db.session.get(Pokemon, id_pokemon)
        assert salvo.forma_pokemon_id == destino.id != forma_antes
        assert (salvo.id, salvo.apelido, salvo.shiny, salvo.localizacao, salvo.posicao) == (
            id_pokemon, "Parceiro", True, "box", 1,
        )
        assert salvo.pv_atual == resultado.pv_novo
        assert calcular_pokemon(salvo, char, regras)["totais"]["pv"] == resultado.pv_maximo_novo
        hist = list(db.session.scalars(select(HistoricoAlteracao)).all())
        assert len(hist) == 1
        assert hist[0].acao == "evolucao"
        assert hist[0].dados_novos["relacao_id"] == str(rel.id)
        with pytest.raises(ValueError, match="não é mais válida"):
            _evoluir(app_db, pokemon, rel)


def test_nivel_insuficiente_bloqueia_mesmo_que_request_forjado(app_db):
    with app_db.app_context():
        char = db.session.get(Personagem, _ids(app_db)["personagem"])
        char.nivel = 12
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        destino = _form("charmeleon", 10)
        rel = _relacao(origem, destino)
        pokemon = _pokemon(app_db, origem)
        db.session.commit()
        with pytest.raises(ValueError, match="nível 16"):
            _evoluir(app_db, pokemon, rel)
        db.session.rollback()
        assert db.session.get(Pokemon, pokemon.id).forma_pokemon_id == origem.id


def test_pedra_consumida_uma_vez_da_mochila_na_mesma_transacao(app_db):
    with app_db.app_context():
        eevee = _form("eevee")
        vaporeon = _form("vaporeon", aumento=10)
        rel = _relacao(eevee, vaporeon, tipo="item", req={
            "tipo_relacao": "evolucao", "item_nome": "Pedra da Água",
            "item_codigo_pokeapi": "water-stone",
        })
        pokemon = _pokemon(app_db, eevee)
        registro = _material(app_db, "pedra-agua", "Pedra da Água", 2)
        db.session.commit()
        assert consultar_evolucoes_pokemon(
            pokemon, db.session.get(Personagem, _ids(app_db)["personagem"])
        ).opcoes[0].pode_evoluir
        resultado = _evoluir(app_db, pokemon, rel)
        db.session.commit()
        assert resultado.item_consumido == "Pedra da Água"
        assert registro.quantidade == 1
        assert pokemon.forma_pokemon_id == vaporeon.id
        hist = list(db.session.scalars(select(HistoricoAlteracao)).all())
        assert sorted(h.acao for h in hist) == ["consumo_evolucao", "evolucao"]


def test_pedra_sem_estoque_e_item_nao_consumivel_nao_modificam_ficha(app_db):
    with app_db.app_context():
        eevee, jolteon = _form("eevee"), _form("jolteon", aumento=8)
        rel = _relacao(eevee, jolteon, tipo="item", req={
            "tipo_relacao": "evolucao", "item_nome": "Pedra do Trovão",
            "item_codigo_pokeapi": "thunder-stone",
        })
        p = _pokemon(app_db, eevee)
        db.session.commit()
        with pytest.raises(ValueError, match="ausente"):
            _evoluir(app_db, p, rel)
        db.session.rollback()
        estoque = _material(app_db, "thunder-stone", "Pedra do Trovão", 1, consumivel=False)
        db.session.commit()
        with pytest.raises(ValueError, match="consumível"):
            _evoluir(app_db, p, rel)
        db.session.rollback()
        assert estoque.quantidade == 1
        assert p.forma_pokemon_id == eevee.id
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 0


def test_especial_requer_liberacao_individual_e_nao_herda_outra_evolucao(app_db):
    with app_db.app_context():
        eevee, umbreon, espeon = _form("eevee"), _form("umbreon", 11), _form("espeon", 12)
        r1 = _relacao(eevee, umbreon, tipo="especial", req={
            "tipo_relacao": "evolucao", "requer_liberacao_mestre": True,
            "condicao": "Ritual do mestre",
        })
        r2 = _relacao(eevee, espeon, tipo="especial", req={
            "tipo_relacao": "evolucao", "requer_liberacao_mestre": True,
        })
        p1 = _pokemon(app_db, eevee, posicao=1)
        p2 = _pokemon(app_db, eevee, posicao=2)
        db.session.commit()
        with pytest.raises(ValueError, match="liberação individual"):
            _evoluir(app_db, p1, r1)
        db.session.rollback()

        _autorizar(app_db, p1, r1)
        db.session.commit()
        with pytest.raises(ValueError, match="liberação individual"):
            _evoluir(app_db, p1, r2)
        db.session.rollback()
        with pytest.raises(ValueError, match="liberação individual"):
            _evoluir(app_db, p2, r1)
        db.session.rollback()

        resultado = _evoluir(app_db, p1, r1)
        db.session.commit()
        assert resultado.destino_nome == "Umbreon"
        assert p1.forma_pokemon_id == umbreon.id
        assert p2.forma_pokemon_id == eevee.id
        aut = db.session.scalar(select(AutorizacaoEvolucaoPokemon))
        assert not aut.ativo and aut.revogado_em is not None


def test_material_especial_galarica_exige_liberacao_e_consume_item(app_db):
    with app_db.app_context():
        origem = _form("slowpoke-galar")
        destino = _form("slowbro-galar", 10)
        rel = _relacao(origem, destino, tipo="especial", req={
            "tipo_relacao": "evolucao", "requer_liberacao_mestre": True,
            "item_especifico_pokeapi": "galarica-cuff",
            "gatilho_pokeapi": "3",
        })
        p = _pokemon(app_db, origem)
        db.session.commit()
        _autorizar(app_db, p, rel)
        db.session.commit()
        with pytest.raises(ValueError, match="Material necessário ausente"):
            _evoluir(app_db, p, rel)
        db.session.rollback()
        estoque = _material(app_db, "bracelete-galariano", "Bracelete Galariano", 1)
        db.session.commit()
        consulta = consultar_evolucoes_pokemon(
            p, db.session.get(Personagem, _ids(app_db)["personagem"])
        )
        assert consulta.opcoes[0].pode_evoluir
        resultado = _evoluir(app_db, p, rel)
        db.session.commit()
        assert resultado.item_consumido == "Bracelete Galariano"
        assert p.forma_pokemon_id == destino.id
        assert db.session.get(PersonagemItem, estoque.id) is None


def test_condicao_regional_com_nivel_informativo_ainda_exige_nivel_e_mestre(app_db):
    with app_db.app_context():
        personagem = db.session.get(Personagem, _ids(app_db)["personagem"])
        personagem.nivel = 18
        origem = _form("rattata-alola")
        destino = _form("raticate-alola", 10)
        rel = _relacao(origem, destino, tipo="especial", req={
            "tipo_relacao": "evolucao", "requer_liberacao_mestre": True,
            "nivel_informativo": 20, "condicao": "Durante a noite",
        })
        p = _pokemon(app_db, origem)
        db.session.commit()
        _autorizar(app_db, p, rel)
        db.session.commit()
        with pytest.raises(ValueError, match="nível 20"):
            _evoluir(app_db, p, rel)
        db.session.rollback()
        personagem.nivel = 20
        db.session.commit()
        resultado = _evoluir(app_db, p, rel)
        db.session.commit()
        assert resultado.destino_nome == "Raticate-alola"


def test_desmaio_permanece_desmaiado_sem_cura_automatica(app_db):
    with app_db.app_context():
        forma = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        evoluida = _form("charmeleon", 12)
        rel = _relacao(forma, evoluida)
        p = _pokemon(app_db, forma)
        p.pv_atual = 0
        db.session.commit()
        out = _evoluir(app_db, p, rel)
        db.session.commit()
        assert out.pv_novo == 0 and p.pv_atual == 0


def test_pokemon_no_campo_nao_evolui(app_db):
    with app_db.app_context():
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        destino = _form("charmeleon", 10)
        rel = _relacao(origem, destino)
        p = _pokemon(app_db, origem)
        db.session.add(PokemonEmCampo(
            campanha_id=_ids(app_db)["campanha"], pokemon_id=p.id, time_numero=1,
        ))
        db.session.commit()
        with pytest.raises(ValueError, match="Campo"):
            _evoluir(app_db, p, rel)
        db.session.rollback()
        assert p.forma_pokemon_id == origem.id


def test_rollback_por_falha_de_recalculo_restaura_estoque_e_forma(app_db, monkeypatch):
    with app_db.app_context():
        eevee, vaporeon = _form("eevee"), _form("vaporeon", 10)
        rel = _relacao(eevee, vaporeon, tipo="item", req={
            "tipo_relacao": "evolucao", "item_nome": "Pedra da Água",
            "item_codigo_pokeapi": "water-stone",
        })
        p = _pokemon(app_db, eevee)
        estoque = _material(app_db, "water-stone", "Pedra da Água", 1)
        db.session.commit()
        from app.services import evolucao_efetiva_service as svc
        original = svc.calcular_pokemon
        contagem = {"n": 0}
        def falhar_segundo_calculo(*args, **kwargs):
            contagem["n"] += 1
            if contagem["n"] == 2:
                raise ValueError("falha artificial no recálculo")
            return original(*args, **kwargs)
        monkeypatch.setattr(svc, "calcular_pokemon", falhar_segundo_calculo)
        with pytest.raises(ValueError, match="falha artificial"):
            _evoluir(app_db, p, rel)
        db.session.rollback()
        assert db.session.get(Pokemon, p.id).forma_pokemon_id == eevee.id
        assert db.session.scalar(select(PersonagemItem.quantidade)) == 1
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 0


def test_rota_somente_jogador_com_csrf_e_confirmacao_da_ficha(app_db, client_db):
    with app_db.app_context():
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        destino = _form("charmeleon", 10)
        rel = _relacao(origem, destino)
        p = _pokemon(app_db, origem)
        db.session.commit()
        pid, relid, origem_id, destino_id = p.id, rel.id, origem.id, destino.id
    url = f"/jogador/pokemon/{pid}/evolucoes/{relid}/evoluir"
    assert client_db.post(url).status_code == 302
    assert _login(client_db, "mestre-db", "senha-db").status_code == 302
    assert client_db.post(url, data={"csrf_token": "abc"}).status_code == 302
    client_db.post("/logout")
    assert _login(client_db, "bartz-db", "abc123").status_code == 302
    pagina = client_db.get("/jogador/dashboard")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert "Evoluir" in html and "Charmeleon" in html
    with client_db.session_transaction() as sess:
        csrf = sess["csrf_acao_evolucao"]
    assert client_db.post(url, data={"csrf_token": "errado"}).status_code == 403
    with app_db.app_context():
        assert db.session.get(Pokemon, pid).forma_pokemon_id == origem_id
    resposta = client_db.post(url, data={"csrf_token": csrf, "retorno": "boxes"})
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.get(Pokemon, pid).forma_pokemon_id == destino_id
    pagina = client_db.get("/jogador/dashboard")
    assert "evolucao-disponivel.svg" not in pagina.get_data(as_text=True)


def test_sessao_outro_jogador_nao_pode_evoluir_pokemon_alheio(app_db):
    with app_db.app_context():
        origem = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        destino = _form("charmeleon", 10)
        rel = _relacao(origem, destino)
        p = _pokemon(app_db, origem)
        db.session.commit()
        with pytest.raises(PermissionError):
            evoluir_pokemon(
                pokemon_id=p.id, relacao_id=rel.id, personagem_id=p.personagem_id,
                campanha_id=_ids(app_db)["campanha"], usuario_id=_ids(app_db)["mestre"],
            )
        assert db.session.get(Pokemon, p.id).forma_pokemon_id == origem.id
