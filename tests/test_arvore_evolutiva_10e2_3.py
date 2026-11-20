"""10E.2.3: árvore de famílias e ampliação revisada de evoluções."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import EspeciePokemon, EvolucaoPokemon, FormaPokemon, HistoricoAlteracao, Pokemon
from app.services.arvore_evolutiva_service import (
    MAX_NOS_ARVORE, descrever_requisito, montar_arvore_evolutiva,
)
from app.services.evolucoes_admin_service import (
    _referencias_revisadas_10e2_3, cadastrar_sugestao, sugestoes_verificadas,
)


def _login(client, usuario="mestre-db", senha="senha-db"):
    resposta = client.post("/login", data={"login": usuario, "senha": senha})
    assert resposta.status_code == 302


def _formas(*codigos):
    encontrados = {
        f.codigo: f for f in db.session.scalars(
            select(FormaPokemon).where(FormaPokemon.codigo.in_(codigos))
        )
    }
    for codigo in codigos:
        if codigo not in encontrados:
            especie = EspeciePokemon(codigo=codigo, nome=codigo.capitalize(), ativo=True)
            forma = FormaPokemon(
                especie=especie, codigo=codigo, nome=codigo.capitalize(),
                categoria="normal", ativo=True,
            )
            db.session.add(forma)
            encontrados[codigo] = forma
    db.session.flush()
    return encontrados


def _relacao(origem, destino, *, tipo="evolucao", gatilho="nivel",
             nivel=16, condicao=None, ativo=True, requisitos=None):
    r = EvolucaoPokemon(
        forma_origem_id=origem.id,
        forma_destino_id=destino.id,
        tipo_requisito=gatilho,
        requisitos=requisitos if requisitos is not None else {
            "tipo_relacao": tipo,
            "nivel": nivel,
            "condicao": condicao,
        },
        ativo=ativo,
    )
    db.session.add(r)
    db.session.flush()
    return r


def _codigos(camada):
    return {n.codigo for n in camada}


def test_arvore_mostra_estagios_ramos_e_convergencia_sem_duplicar_nos(app_db):
    with app_db.app_context():
        f = _formas("eevee", "vaporeon", "jolteon", "sylveon")
        _relacao(f["eevee"], f["vaporeon"], gatilho="item", nivel=None,
                 requisitos={"tipo_relacao": "evolucao", "item_nome": "Pedra da Água"})
        _relacao(f["eevee"], f["jolteon"], gatilho="item", nivel=None,
                 requisitos={"tipo_relacao": "evolucao", "item_nome": "Pedra do Trovão"})
        # Fusão artificial para testar o algoritmo, NÃO é regra oficial.
        _relacao(f["vaporeon"], f["sylveon"], nivel=20)
        _relacao(f["jolteon"], f["sylveon"], nivel=20)
        db.session.commit()

        arvore = montar_arvore_evolutiva(f["sylveon"])
        assert arvore.quantidade_formas == 4
        assert len(arvore.camadas) == 3
        assert _codigos(arvore.camadas[0]) == {"eevee"}
        assert _codigos(arvore.camadas[1]) == {"vaporeon", "jolteon"}
        assert _codigos(arvore.camadas[2]) == {"sylveon"}
        assert len(arvore.camadas[2][0].predecessores) == 2
        assert {p.origem_nome for p in arvore.camadas[2][0].predecessores} == {
            "Jolteon", "Vaporeon",
        }
        assert arvore.camadas[2][0].selecionado is True
        assert arvore.truncada is False
        assert arvore.ciclo_legado is False
        assert arvore.relacoes_especiais == []


def test_mega_alternativa_e_regional_separadas_de_evolucoes_permanentes(app_db):
    with app_db.app_context():
        f = _formas("charizard", "charmeleon")
        mega = FormaPokemon(
            especie_id=f["charizard"].especie_id, codigo="charizard-mega-vis",
            nome="Charizard (Mega Visual)", categoria="mega", ativo=True,
        )
        reg = FormaPokemon(
            especie_id=f["charizard"].especie_id, codigo="charizard-regional-vis",
            nome="Charizard (Regional Visual)", categoria="regional", ativo=True,
        )
        alt = FormaPokemon(
            especie_id=f["charizard"].especie_id, codigo="charizard-alt-vis",
            nome="Charizard (Alternativo Visual)", categoria="alternativa", ativo=True,
        )
        db.session.add_all([mega, reg, alt])
        db.session.flush()
        _relacao(f["charmeleon"], f["charizard"], nivel=36)
        for dest, tipo, gatilho in [
            (mega, "mega", "mega_pedra"), (reg, "regional", "linhagem"),
            (alt, "alternativa", "condicao"),
        ]:
            _relacao(f["charizard"], dest, tipo=tipo, gatilho=gatilho, nivel=None)
        db.session.commit()
        arvore = montar_arvore_evolutiva(f["charizard"])
        assert arvore.quantidade_formas == 2
        assert arvore.total_relacoes_permanentes == 1
        assert len(arvore.relacoes_especiais) == 3
        assert {r.requisitos["tipo_relacao"] for r in arvore.relacoes_especiais} == {
            "mega", "regional", "alternativa",
        }


def test_arvore_ignora_inativas_e_respeita_legado_sem_tipo(app_db):
    with app_db.app_context():
        f = _formas("bulbasaur", "ivysaur", "venusaur")
        _relacao(f["bulbasaur"], f["ivysaur"], requisitos={"nivel": 16})
        _relacao(f["ivysaur"], f["venusaur"], ativo=False)
        db.session.commit()
        arvore = montar_arvore_evolutiva(f["bulbasaur"])
        assert arvore.quantidade_formas == 2
        assert arvore.total_relacoes_permanentes == 1
        assert descrever_requisito(next(iter(db.session.scalars(
            select(EvolucaoPokemon).where(EvolucaoPokemon.ativo.is_(True))
        )))) == "Nível 16 do treinador"
        assert _codigos(arvore.camadas[-1]) == {"ivysaur"}


def test_ciclo_legado_nao_gera_recursao_infinita_ou_edicoes(app_db):
    with app_db.app_context():
        f = _formas("eevee", "vaporeon", "jolteon")
        _relacao(f["eevee"], f["vaporeon"])
        _relacao(f["vaporeon"], f["jolteon"])
        _relacao(f["jolteon"], f["eevee"])
        db.session.commit()
        antes = db.session.scalar(select(func.count(EvolucaoPokemon.id)))
        arvore = montar_arvore_evolutiva(f["eevee"])
        assert arvore.quantidade_formas == 3
        assert arvore.ciclo_legado is True
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == antes


def test_fontes_ampliadas_e_propostas_pendentes_nao_podem_ser_aprovadas(app_db, client_db):
    propostas = _referencias_revisadas_10e2_3()
    assert len(propostas) == 12
    assert sum(p["status"] == "aprovavel" for p in propostas) == 7
    assert sum(p["status"] == "pendente_decisao" for p in propostas) == 5
    with app_db.app_context():
        f = _formas(
            "eevee", "vaporeon", "jolteon", "flareon", "leafeon",
            "glaceon", "espeon", "umbreon", "sylveon",
        )
        db.session.commit()
        sugestoes = sugestoes_verificadas(f["eevee"])
        assert len(sugestoes) == 8
        assert {p["destino"] for p in sugestoes if p["status"] == "pendente_decisao"} == {
            "espeon", "umbreon", "sylveon",
        }
        assert all(p["alerta_ankar"] for p in sugestoes if p["status"] == "aprovavel")
        relacao, erros = cadastrar_sugestao(f["eevee"], "espeon", usuario_id=None)
        assert relacao is None and any("decisão narrativa" in erro for erro in erros)
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0

        relacao, erros = cadastrar_sugestao(f["eevee"], "vaporeon", usuario_id=None)
        assert not erros and relacao is not None
        assert relacao.tipo_requisito == "item"
        assert relacao.requisitos["item_nome"] == "Pedra da Água"
        assert relacao.requisitos["aprovado_mestre"] is True
        assert relacao.requisitos["fonte_url"].startswith("https://pokeapi.co/")
        assert "amizade" in relacao.observacoes.lower()
        assert len(sugestoes_verificadas(f["eevee"])) == 7
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 1

    _login(client_db)
    url = f"/mestre/catalogo/pokemons/{f['eevee'].id}/relacoes"
    pagina = client_db.get(url)
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert "Pendente de decisão do mestre" in html
    assert "Estilhaço do Sol" in html
    assert "Pedra do Gelo" in html
    # A rota rejeita POST forjado para um caso pendente.
    bloqueado = client_db.post(f"{url}/verificada/espeon")
    assert bloqueado.status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 1


def test_arvore_url_visivel_e_permissoes_mestre(app_db, client_db):
    with app_db.app_context():
        f = _formas("charmander", "charmeleon", "charizard")
        _relacao(f["charmander"], f["charmeleon"], nivel=16)
        _relacao(f["charmeleon"], f["charizard"], nivel=36)
        db.session.commit()
        charmander_id = f["charmander"].id
    url = f"/mestre/catalogo/pokemons/{charmander_id}/arvore"
    assert client_db.get(url).status_code == 302
    _login(client_db, "bartz-db", "abc123")
    assert client_db.get(url).status_code == 302
    client_db.get("/sair")
    _login(client_db)
    pagina = client_db.get(url)
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert "Árvore de Charmander" in html
    assert "Estágio 3" in html
    assert "Charmeleon" in html
    assert "Charizard" in html
    assert "Nível 36 do treinador" in html
    relacoes = client_db.get(
        f"/mestre/catalogo/pokemons/{charmander_id}/relacoes"
    )
    assert relacoes.status_code == 200
    assert "Ver árvore da família" in relacoes.get_data(as_text=True)


def test_visualizacao_nao_altera_pokemon_do_jogador(app_db, client_db):
    with app_db.app_context():
        f = _formas("charmander", "charmeleon")
        _relacao(f["charmander"], f["charmeleon"], nivel=16)
        personagem_id = uuid.UUID(app_db.config["TEST_IDS"]["personagem"])
        pokemon = Pokemon(
            personagem_id=personagem_id,
            forma_pokemon_id=f["charmander"].id,
            apelido="Faísca", genero="Fêmea", shiny=True, pv_atual=24,
            localizacao="box", posicao=1, ativo=True,
        )
        db.session.add(pokemon)
        db.session.commit()
        pokemon_id, charmander_id = pokemon.id, f["charmander"].id
    _login(client_db)
    resposta = client_db.get(f"/mestre/catalogo/pokemons/{charmander_id}/arvore")
    assert resposta.status_code == 200
    with app_db.app_context():
        salvo = db.session.get(Pokemon, pokemon_id)
        assert (salvo.forma_pokemon_id, salvo.pv_atual, salvo.shiny, salvo.apelido) == (
            charmander_id, 24, True, "Faísca",
        )
