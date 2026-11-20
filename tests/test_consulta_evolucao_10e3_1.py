"""10E.3.1: elegibilidade de evolução apenas para consulta, por Pokémon."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    EspeciePokemon, EvolucaoPokemon, FormaPokemon, Item,
    Personagem, PersonagemItem, Pokemon,
)
from app.services.consulta_evolucao_service import consultar_evolucoes_pokemon

def _login(client, login="mestre-db", senha="senha-db"):
    resposta = client.post("/login", data={"login": login, "senha": senha})
    assert resposta.status_code == 302



def _form(codigo: str, *, categoria="normal") -> FormaPokemon:
    forma = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == codigo))
    if forma is not None:
        return forma
    especie = EspeciePokemon(codigo=codigo, nome=codigo.capitalize(), ativo=True)
    forma = FormaPokemon(
        especie=especie, codigo=codigo, nome=codigo.capitalize(),
        categoria=categoria, ativo=True,
    )
    db.session.add(forma)
    db.session.flush()
    return forma


def _ligar(origem, destino, *, tipo="nivel", requisitos=None, ativo=True):
    if requisitos is None:
        requisitos = {"tipo_relacao": "evolucao", "nivel": 16}
    r = EvolucaoPokemon(
        forma_origem_id=origem.id, forma_destino_id=destino.id,
        tipo_requisito=tipo, requisitos=requisitos, ativo=ativo,
    )
    db.session.add(r)
    db.session.flush()
    return r


def _pokemon(personagem, forma, *, nome="Faísca"):
    pokemon = Pokemon(
        personagem_id=personagem.id, forma_pokemon_id=forma.id,
        apelido=nome, genero="Macho", shiny=True, pv_atual=21,
        localizacao="box", posicao=1, ativo=True,
    )
    db.session.add(pokemon)
    db.session.flush()
    return pokemon


def _personagem(app):
    return db.session.get(Personagem, uuid.UUID(app.config["TEST_IDS"]["personagem"]))


def _criar_item(codigo, nome, personagem, quantidade=1):
    item = Item(codigo=codigo, nome=nome, preco=500, ativo=True, consumivel=True)
    db.session.add(item)
    db.session.flush()
    db.session.add(PersonagemItem(
        personagem_id=personagem.id, item_id=item.id, quantidade=quantidade,
    ))
    db.session.flush()
    return item


def _contadores():
    return {
        "pokemons": db.session.scalar(select(func.count(Pokemon.id))),
        "relacoes": db.session.scalar(select(func.count(EvolucaoPokemon.id))),
        "itens_mochila": db.session.scalar(select(func.count(PersonagemItem.id))),
    }


def test_nivel_compartilhado_habilita_evolucao_sem_modificar_instancia(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        charmander, charmeleon = _form("charmander"), _form("charmeleon")
        _ligar(charmander, charmeleon, requisitos={
            "tipo_relacao": "evolucao", "nivel": 16,
            "origem_importacao": "10E.2.4", "aprovado_mestre": False,
            "requer_liberacao_mestre": False,
        })
        pokemon = _pokemon(personagem, charmander)
        db.session.commit()
        antes = (pokemon.id, pokemon.forma_pokemon_id, pokemon.pv_atual,
                 pokemon.apelido, pokemon.shiny, _contadores())
        consulta = consultar_evolucoes_pokemon(pokemon, personagem)
        assert consulta.nivel_treinador == 48
        assert len(consulta.opcoes) == 1
        opcao = consulta.opcoes[0]
        assert (opcao.estado, opcao.nivel_necessario) == ("disponivel", 16)
        assert "Nível 16 do treinador" == opcao.requisito_texto
        assert (pokemon.id, pokemon.forma_pokemon_id, pokemon.pv_atual,
                pokemon.apelido, pokemon.shiny, _contadores()) == antes


def test_nivel_insuficiente_e_sem_evolucao_depois(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        personagem.nivel = 12
        charmander, charmeleon = _form("charmander"), _form("charmeleon")
        _ligar(charmander, charmeleon, requisitos={"tipo_relacao": "evolucao", "nivel": 16})
        pokemon = _pokemon(personagem, charmander)
        db.session.commit()
        consulta = consultar_evolucoes_pokemon(pokemon, personagem)
        opcao = consulta.opcoes[0]
        assert opcao.estado == "nivel_insuficiente"
        assert "4 nível(is)" in opcao.orientacao
        assert pokemon.forma_pokemon_id == charmander.id


def test_pedra_somente_se_estiver_na_mochila_do_treinador(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        eevee, vaporeon, jolteon = (
            _form("eevee"), _form("vaporeon"), _form("jolteon")
        )
        _ligar(eevee, vaporeon, tipo="item", requisitos={
            "tipo_relacao": "evolucao", "item_nome": "Pedra da Água",
            "item_codigo_pokeapi": "water-stone",
        })
        _ligar(eevee, jolteon, tipo="item", requisitos={
            "tipo_relacao": "evolucao", "item_nome": "Pedra do Trovão",
            "item_codigo_pokeapi": "thunder-stone",
        })
        pokemon = _pokemon(personagem, eevee)
        _criar_item("pedra-agua", "Pedra da Água", personagem, quantidade=2)
        db.session.commit()
        c1 = consultar_evolucoes_pokemon(pokemon, personagem)
        estados = {op.destino_codigo: op for op in c1.opcoes}
        assert estados["vaporeon"].estado == "disponivel"
        assert estados["vaporeon"].quantidade_pedra == 2
        assert estados["jolteon"].estado == "pedra_ausente"
        assert estados["jolteon"].quantidade_pedra == 0
        assert db.session.scalar(select(PersonagemItem.quantidade)) == 2
        assert pokemon.forma_pokemon_id == eevee.id


def test_estoque_zero_item_inativo_e_item_equipado_nao_contam(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        eevee, flareon = _form("eevee"), _form("flareon")
        _ligar(eevee, flareon, tipo="item", requisitos={
            "tipo_relacao": "evolucao", "item_nome": "Pedra do Fogo",
        })
        pokemon = _pokemon(personagem, eevee)
        item = _criar_item("fire-stone", "Fire Stone", personagem, quantidade=0)
        pokemon.item_equipado_id = item.id
        db.session.commit()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "pedra_ausente"
        db.session.scalar(select(PersonagemItem)).quantidade = 1
        item.ativo = False
        db.session.commit()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "pedra_ausente"


def test_evolucoes_especiais_eevee_nunca_sao_liberadas_por_catalogo(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        eevee = _form("eevee")
        pokemon = _pokemon(personagem, eevee)
        for codigo, req in (
            ("umbreon", {"tipo_relacao": "evolucao",
                         "aprovado_mestre": True, "requer_liberacao_mestre": True}),
            ("espeon", {"tipo_relacao": "evolucao",
                        "condicao": "Somente durante o dia", "aprovado_mestre": True}),
            ("sylveon", {"tipo_relacao": "evolucao", "detalhes_pokeapi": {
                "known_move_type_id": "18", "minimum_happiness": "160",
            }}),
        ):
            destino = _form(codigo)
            _ligar(eevee, destino, tipo="especial", requisitos=req)
        db.session.commit()
        c = consultar_evolucoes_pokemon(pokemon, personagem)
        assert len(c.opcoes) == 3
        assert {x.estado for x in c.opcoes} == {"requer_mestre"}
        assert all("liberação individual" in x.orientacao for x in c.opcoes)


def test_condicoes_regionais_nunca_liberadas_por_nivel_ou_pedra(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        rattata = _form("rattata-alola", categoria="regional")
        raticate = _form("raticate-alola", categoria="regional")
        cubone = _form("cubone")
        marowak = _form("marowak-alola", categoria="regional")
        pikachu = _form("pikachu")
        raichu = _form("raichu-alola", categoria="regional")
        _ligar(rattata, raticate, tipo="especial", requisitos={
            "tipo_relacao": "evolucao", "nivel_informativo": 20,
            "condicao": "Nível 20 durante a noite",
            "requer_liberacao_mestre": True,
        })
        _ligar(cubone, marowak, tipo="especial", requisitos={
            "tipo_relacao": "evolucao", "condicao": "Noite na região Alola",
        })
        _ligar(pikachu, raichu, tipo="especial", requisitos={
            "tipo_relacao": "evolucao", "item_nome": "Pedra do Trovão",
            "condicao": "Região de Alola",
        })
        pokemon = _pokemon(personagem, rattata)
        db.session.commit()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "requer_mestre"
        pokemon.forma_pokemon_id = cubone.id
        db.session.flush()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "requer_mestre"
        pokemon.forma_pokemon_id = pikachu.id
        db.session.flush()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "requer_mestre"


def test_troca_item_especial_e_pedra_com_genero_bloqueados(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        origem, destino = _form("kirlia"), _form("gallade")
        rel = _ligar(origem, destino, tipo="especial", requisitos={
            "tipo_relacao": "evolucao", "item_especifico_pokeapi": "dawn-stone",
            "detalhes_pokeapi": {"gender_id": "2"},
            "requer_liberacao_mestre": True,
        })
        pokemon = _pokemon(personagem, origem)
        db.session.commit()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "requer_mestre"
        rel.tipo_requisito = "troca"
        rel.requisitos = {"tipo_relacao": "evolucao", "aprovado_mestre": True}
        db.session.flush()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "requer_mestre"
        rel.tipo_requisito = "item"
        rel.requisitos = {"tipo_relacao": "evolucao", "item_nome": "Disco Dúbio"}
        db.session.flush()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "requer_mestre"


def test_relacoes_inativas_e_nao_permanentes_nao_aparecem(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        charmander, charmeleon, charizard = (
            _form("charmander"), _form("charmeleon"), _form("charizard")
        )
        _ligar(charmander, charmeleon, ativo=False)
        _ligar(charmander, charizard, tipo="especial",
               requisitos={"tipo_relacao": "mega", "condicao": "Pedra Chave"})
        pokemon = _pokemon(personagem, charmander)
        db.session.commit()
        assert not consultar_evolucoes_pokemon(pokemon, personagem).possui_evolucoes


def test_entradas_desconhecidas_falham_fechadas_sem_evolucao(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        charmander, charmeleon = _form("charmander"), _form("charmeleon")
        rel = _ligar(charmander, charmeleon, tipo="nivel",
                     requisitos={"tipo_relacao": "evolucao", "nivel": "16"})
        pokemon = _pokemon(personagem, charmander)
        db.session.commit()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "requer_mestre"
        rel.requisitos = {"tipo_relacao": "evolucao", "nivel": 16,
                          "item_nome": "Pedra da Água"}
        db.session.flush()
        assert consultar_evolucoes_pokemon(pokemon, personagem).opcoes[0].estado == "requer_mestre"


def test_rejeita_consulta_de_pokemon_de_outro_treinador(app_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        charmander = _form("charmander")
        pokemon = _pokemon(personagem, charmander)
        outro = Personagem(
            usuario_id=personagem.usuario_id,
            campanha_id=personagem.campanha_id,
            nome="Outro treinador", nivel=50, ativo=True,
        )
        # Sem salvar: basta um identificador distinto para recusar acesso.
        outro.id = uuid.uuid4()
        with pytest.raises(ValueError, match="não pertence"):
            consultar_evolucoes_pokemon(pokemon, outro)


def test_ficha_jogador_e_mestre_exibem_previa_sem_controles_de_evolucao(app_db, client_db):
    with app_db.app_context():
        personagem = _personagem(app_db)
        charmander, charmeleon = _form("charmander"), _form("charmeleon")
        _ligar(charmander, charmeleon, requisitos={
            "tipo_relacao": "evolucao", "nivel": 16,
        })
        pokemon = _pokemon(personagem, charmander)
        db.session.commit()
        id_pokemon = pokemon.id
        id_personagem = personagem.id
        forma_original_id = charmander.id

    assert client_db.get(f"/jogador/pokemon/{id_pokemon}").status_code == 302
    _login(client_db, "bartz-db", "abc123")
    ficha = client_db.get(f"/jogador/pokemon/{id_pokemon}")
    assert ficha.status_code == 200
    html = ficha.get_data(as_text=True)
    assert "Evoluções de Charmander" in html
    assert "Requisito atendido" in html
    assert "Consulta somente leitura" in html
    assert "A ação de evoluir será desenvolvida" in html
    assert "Evoluir agora" not in html

    client_db.post("/logout")
    _login(client_db)
    mestre = client_db.get(f"/mestre/jogadores/{id_personagem}/pokemon/{id_pokemon}")
    assert mestre.status_code == 200
    assert "Evoluções de Charmander" in mestre.get_data(as_text=True)
    with app_db.app_context():
        salvo = db.session.get(Pokemon, id_pokemon)
        assert salvo.forma_pokemon_id == forma_original_id
        assert salvo.shiny is True
        assert salvo.pv_atual == 21
        assert db.session.scalar(select(func.count(PersonagemItem.id))) == 0
