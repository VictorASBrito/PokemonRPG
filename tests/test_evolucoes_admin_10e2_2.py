"""10E.2.2: edição de relações do catálogo sem afetar Pokémon de jogadores."""
from __future__ import annotations

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import EspeciePokemon, EvolucaoPokemon, FormaPokemon, HistoricoAlteracao
from app.services.evolucoes_admin_service import (
    cadastrar_sugestao, desativar_relacao, listar_relacoes, salvar_relacao,
    sugestoes_verificadas,
)


def _login(client_db, login="mestre-db", senha="senha-db"):
    resposta = client_db.post("/login", data={"login": login, "senha": senha})
    assert resposta.status_code == 302


def _preparar(app_db):
    with app_db.app_context():
        resultado = {
            f.codigo: str(f.id) for f in db.session.scalars(select(FormaPokemon)).all()
        }
        for codigo in (
            "ivysaur", "venusaur", "charmeleon", "charizard", "wartortle", "blastoise",
            "eevee", "vaporeon", "morpeko",
        ):
            if codigo not in resultado:
                especie = EspeciePokemon(codigo=codigo, nome=codigo.capitalize(), ativo=True)
                forma = FormaPokemon(
                    especie=especie, codigo=codigo, nome=codigo.capitalize(),
                    categoria="normal", ativo=True,
                )
                db.session.add(forma)
        db.session.flush()
        morpeko = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "morpeko")
        )
        eevee = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "eevee")
        )
        charizard = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "charizard")
        )
        db.session.add_all([
            FormaPokemon(especie_id=morpeko.especie_id, codigo="morpeko-faminto",
                        nome="Morpeko (Faminto)", categoria="alternativa", ativo=True),
            FormaPokemon(especie_id=charizard.especie_id, codigo="charizard-mega-x",
                        nome="Charizard (Mega X)", categoria="mega", ativo=True),
            FormaPokemon(especie_id=eevee.especie_id, codigo="eevee-regional",
                        nome="Eevee (Regional)", categoria="regional", ativo=True),
        ])
        db.session.commit()
        return {
            f.codigo: str(f.id) for f in db.session.scalars(select(FormaPokemon)).all()
        }


def _dados(destino_id, **kwargs):
    dados = {
        "destino_id": destino_id,
        "tipo_relacao": "evolucao",
        "tipo_requisito": "nivel",
        "nivel": "16",
        "fonte": "combinada",
        "fonte_url": "https://pokeapi.co/api/v2/evolution-chain/2/",
        "observacoes": "PokeAPI e Pokémon Database: nível 16.",
    }
    dados.update(kwargs)
    return dados


def _origem(codigo):
    return db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == codigo))


def test_editor_exige_perfil_mestre(app_db, client_db):
    ids = _preparar(app_db)
    url = f"/mestre/catalogo/pokemons/{ids['charmander']}/relacoes"
    assert client_db.get(url).status_code == 302
    _login(client_db, "bartz-db", "abc123")
    resposta = client_db.get(url)
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0


def test_sugestao_verificada_cadastrada_so_apos_aprovacao(app_db, client_db):
    ids = _preparar(app_db)
    _login(client_db)
    url = f"/mestre/catalogo/pokemons/{ids['charmander']}/relacoes"
    resposta = client_db.get(url)
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "Evoluções verificadas" in html
    assert "Charmeleon" in html
    assert "Aprovar e cadastrar" in html
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0

    resposta = client_db.post(f"{url}/verificada/charmeleon")
    assert resposta.status_code == 302
    with app_db.app_context():
        relacao = db.session.scalar(select(EvolucaoPokemon))
        assert relacao.tipo_requisito == "nivel"
        assert relacao.requisitos["nivel"] == 16
        assert relacao.requisitos["tipo_relacao"] == "evolucao"
        assert relacao.requisitos["fonte"] == "combinada"
        assert relacao.requisitos["aprovado_mestre"] is True
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 1

    segunda = client_db.post(f"{url}/verificada/charmeleon")
    assert segunda.status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 1


def test_evolucao_editor_permite_atualizar_e_desativar_com_historico(app_db, client_db):
    ids = _preparar(app_db)
    _login(client_db)
    url = f"/mestre/catalogo/pokemons/{ids['charmander']}/relacoes"
    primeira = client_db.post(url, data=_dados(ids["charmeleon"]))
    assert primeira.status_code == 302

    with app_db.app_context():
        relacao = db.session.scalar(select(EvolucaoPokemon))
        rel_id = str(relacao.id)
        assert relacao.ativo
    atualizar = client_db.post(url, data=_dados(
        ids["charmeleon"], relacao_id=rel_id, nivel="20",
        observacoes="Regra de Ankar alterada pelo mestre.",
    ))
    assert atualizar.status_code == 302
    with app_db.app_context():
        relacao = db.session.scalar(select(EvolucaoPokemon))
        assert relacao.requisitos["nivel"] == 20
        assert relacao.observacoes.startswith("Regra de Ankar")

    desativar = client_db.post(f"{url}/{rel_id}/desativar")
    assert desativar.status_code == 302
    with app_db.app_context():
        relacao = db.session.scalar(select(EvolucaoPokemon))
        assert relacao.ativo is False
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 3


def test_rejeita_ciclo_e_duplicacao_de_evolucoes(app_db):
    ids = _preparar(app_db)
    with app_db.app_context():
        charmander = _origem("charmander")
        charmeleon = _origem("charmeleon")
        charizard = _origem("charizard")
        assert not salvar_relacao(charmander, _dados(ids["charmeleon"]), usuario_id=None)[1]
        assert not salvar_relacao(charmeleon, _dados(ids["charizard"], nivel="36"), usuario_id=None)[1]
        _, erro_ciclo = salvar_relacao(charizard, _dados(ids["charmander"]), usuario_id=None)
        assert any("ciclo" in e for e in erro_ciclo)
        _, duplicado = salvar_relacao(charmander, _dados(ids["charmeleon"]), usuario_id=None)
        assert any("existe" in e for e in duplicado)
        _, igual = salvar_relacao(charmander, _dados(ids["charmander"]), usuario_id=None)
        assert any("consigo" in e for e in igual)
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 2


def test_variantes_mega_e_regionais_tem_regras_distintas(app_db):
    ids = _preparar(app_db)
    with app_db.app_context():
        charizard = _origem("charizard")
        morpeko = _origem("morpeko")
        eevee = _origem("eevee")
        _, erro_mega = salvar_relacao(
            charizard, _dados(ids["charizard-mega-x"], tipo_relacao="mega",
                             tipo_requisito="mega_pedra", nivel="", item_nome=""),
            usuario_id=None,
        )
        assert any("Mega Pedra" in e for e in erro_mega)
        mega, erros = salvar_relacao(
            charizard, _dados(ids["charizard-mega-x"], tipo_relacao="mega",
                             tipo_requisito="mega_pedra", nivel="",
                             item_nome="Charizardite X",
                             condicao="Ativação pelo mestre em combate."),
            usuario_id=None,
        )
        assert not erros and mega.requisitos["tipo_relacao"] == "mega"

        alternativa, erros = salvar_relacao(
            morpeko, _dados(ids["morpeko-faminto"], tipo_relacao="alternativa",
                            tipo_requisito="condicao", nivel="",
                            condicao="Alternar ao fim do turno."),
            usuario_id=None,
        )
        assert not erros and alternativa.requisitos["tipo_relacao"] == "alternativa"

        regional, erros = salvar_relacao(
            eevee, _dados(ids["eevee-regional"], tipo_relacao="regional",
                         tipo_requisito="linhagem", nivel="",
                         condicao="Variante regional, sem mudança livre."),
            usuario_id=None,
        )
        assert not erros and regional.requisitos["tipo_relacao"] == "regional"

        _, invalida = salvar_relacao(
            charizard, _dados(ids["charizard-mega-x"], tipo_relacao="evolucao",
                             tipo_requisito="nivel", nivel="50"),
            usuario_id=None,
        )
        assert any("Mega" in erro for erro in invalida)
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 3


def test_fonte_requisito_e_id_invalido_sao_rejeitados(app_db):
    ids = _preparar(app_db)
    with app_db.app_context():
        charmander = _origem("charmander")
        for formulario in [
            _dados("identificador-invalido"),
            _dados(ids["charmeleon"], nivel="zero"),
            _dados(ids["charmeleon"], tipo_requisito="item", nivel="", item_nome=""),
            _dados(ids["charmeleon"], tipo_requisito="amizade", nivel="", condicao=""),
            _dados(ids["charmeleon"], fonte_url="javascript:alert(1)"),
        ]:
            rel, erros = salvar_relacao(charmander, formulario, usuario_id=None)
            assert rel is None and erros
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0


def test_fluxo_de_relacoes_nao_altera_pokemon_de_jogador(app_db, client_db):
    ids = _preparar(app_db)
    from app.models.db import Pokemon
    import uuid
    with app_db.app_context():
        personagem_id = uuid.UUID(app_db.config["TEST_IDS"]["personagem"])
        pokemon = Pokemon(
            personagem_id=personagem_id, forma_pokemon_id=uuid.UUID(ids["charmander"]),
            apelido="Fagulha", genero="Macho", shiny=True, pv_atual=22,
            localizacao="box", posicao=1, ativo=True,
        )
        db.session.add(pokemon)
        db.session.commit()
        pokemon_id = pokemon.id
    _login(client_db)
    url = f"/mestre/catalogo/pokemons/{ids['charmander']}/relacoes"
    assert client_db.post(url, data=_dados(ids["charmeleon"])).status_code == 302
    with app_db.app_context():
        p = db.session.get(Pokemon, pokemon_id)
        assert (str(p.forma_pokemon_id), p.apelido, p.pv_atual, p.shiny,
                p.localizacao, p.posicao) == (
                    ids["charmander"], "Fagulha", 22, True, "box", 1,
                )


def test_cadeias_referenciadas_confirmadas_para_iniciais(app_db):
    ids = _preparar(app_db)
    esperado = {
        "bulbasaur": ("ivysaur", 16),
        "ivysaur": ("venusaur", 32),
        "charmander": ("charmeleon", 16),
        "charmeleon": ("charizard", 36),
        "squirtle": ("wartortle", 16),
        "wartortle": ("blastoise", 36),
    }
    with app_db.app_context():
        for origem_codigo, (destino_codigo, nivel) in esperado.items():
            origem = _origem(origem_codigo)
            sugestoes = sugestoes_verificadas(origem)
            assert len(sugestoes) == 1
            assert sugestoes[0]["destino"] == destino_codigo
            assert sugestoes[0]["nivel"] == nivel
            relacao, erros = cadastrar_sugestao(origem, destino_codigo, usuario_id=None)
            assert not erros
            assert relacao.requisitos["nivel"] == nivel
            assert relacao.requisitos["fonte"] == "combinada"
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 6
        bulba = _origem("bulbasaur")
        saida, entrada = listar_relacoes(bulba.id)
        assert len(saida) == 1 and len(entrada) == 0
