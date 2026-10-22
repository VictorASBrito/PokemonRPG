"""Regressão: edição parcial do jogador, autorização real e ícones dos tipos."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.db import Pokemon, Usuario
from app.services.pokemon_db_service import atualizar_pokemon_formulario, carregar_contexto_pokemon
from app.services.tipos_visual import tipo_visual


def _criar_como_mestre(app, client):
    assert client.post('/login', data={'login': 'mestre-db', 'senha': 'senha-db'}).status_code == 302
    personagem = app.config['TEST_IDS']['personagem']
    assert client.post(
        f'/mestre/jogadores/{personagem}/equipe/novo?destino=box:box-unica',
        data={'especie_nome': 'Bulbasaur'},
    ).status_code == 302
    with app.app_context():
        pokemon = db.session.scalars(select(Pokemon)).first()
        assert pokemon is not None
        pk = str(pokemon.id)
    assert client.post(
        f'/mestre/jogadores/{personagem}/pokemon/{pk}',
        data={
            'especie_nome': 'Bulbasaur', 'genero': '♂', 'natureza': 'Valente',
            'shiny': '1', 'apelido': 'Original', 'pv_atual': '55',
            'status': 'Nenhum', 'golpe_nome': ['', '', '', ''],
        },
    ).status_code == 302
    assert client.post('/logout').status_code == 302
    return pk


def test_jogador_edita_campos_permitidos_sem_alterar_identidade(app_db, client_db):
    pokemon_id = _criar_como_mestre(app_db, client_db)
    assert client_db.post('/login', data={'login': 'bartz-db', 'senha': 'abc123'}).status_code == 302
    pagina = client_db.get(f'/jogador/pokemon/{pokemon_id}')
    html = pagina.get_data(as_text=True)
    assert pagina.status_code == 200
    for nome in ('especie_nome', 'genero', 'natureza', 'shiny'):
        assert f'name="{nome}"' not in html
    assert 'Bulbasaur' in html and 'Valente' in html and 'Shiny' in html
    assert 'Gerenciar no inventário' in html

    resposta = client_db.post(f'/jogador/pokemon/{pokemon_id}', data={
        'apelido': 'Apelido livre', 'pv_atual': '30', 'status': 'Paralisado',
        'anotacoes': 'Anotação de teste', 'bonus_ataque': '2',
        'golpe_nome': ['Arranhão', '', '', ''],
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon.apelido == 'Apelido livre'
        assert pokemon.pv_atual == 30
        assert pokemon.natureza.nome == 'Valente'
        assert pokemon.genero == '♂'
        assert pokemon.shiny is True
        assert pokemon.forma_pokemon.nome == 'Bulbasaur'
        assert pokemon.status_ativos[0].status.nome == 'Paralisado'
        assert [g.golpe.nome for g in pokemon.golpes] == ['Arranhão']
        assert pokemon.anotacoes == 'Anotação de teste'
        assert any(b.atributo.codigo == 'ataque' and int(b.valor) == 2 for b in pokemon.bonus_atributos)


def test_tester_pode_editar_todos_os_campos_pokemon_na_propria_ficha(app_db, client_db):
    pokemon_id = _criar_como_mestre(app_db, client_db)
    with app_db.app_context():
        usuario = db.session.get(Usuario, uuid.UUID(app_db.config['TEST_IDS']['jogador']))
        usuario.perfil = 'tester'
        db.session.commit()

    assert client_db.post('/login', data={'login': 'bartz-db', 'senha': 'abc123'}).status_code == 302
    pagina = client_db.get(f'/jogador/pokemon/{pokemon_id}')
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    for campo in ('especie_nome', 'genero', 'natureza', 'shiny'):
        assert f'name="{campo}"' in html

    resposta = client_db.post(f'/jogador/pokemon/{pokemon_id}', data={
        'especie_nome': 'Charmander', 'genero': '♀', 'natureza': 'Dócil',
        'apelido': 'Mudou tudo', 'pv_atual': '30',
        'status': 'Nenhum', 'anotacoes': 'Teste completo',
        'bonus_ataque': '1', 'golpe_nome': ['', '', '', ''],
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon.forma_pokemon.nome == 'Charmander'
        assert pokemon.genero == '♀'
        assert pokemon.natureza.nome == 'Dócil'
        assert pokemon.shiny is False
        assert pokemon.apelido == 'Mudou tudo'
        assert pokemon.anotacoes == 'Teste completo'

    # O mesmo Tester também consegue marcar novamente a variação Shiny.
    resposta = client_db.post(f'/jogador/pokemon/{pokemon_id}', data={
        'especie_nome': 'Charmander', 'genero': '♀', 'natureza': 'Dócil',
        'shiny': '1', 'apelido': 'Mudou tudo', 'pv_atual': '30',
        'status': 'Nenhum', 'anotacoes': 'Teste completo',
        'golpe_nome': ['', '', '', ''],
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.get(Pokemon, uuid.UUID(pokemon_id)).shiny is True


def test_tester_perde_edicao_completa_sem_precisar_refazer_login(app_db, client_db):
    pokemon_id = _criar_como_mestre(app_db, client_db)
    with app_db.app_context():
        usuario = db.session.get(Usuario, uuid.UUID(app_db.config['TEST_IDS']['jogador']))
        usuario.perfil = 'tester'
        db.session.commit()
    assert client_db.post('/login', data={'login': 'bartz-db', 'senha': 'abc123'}).status_code == 302
    assert 'name="natureza"' in client_db.get(f'/jogador/pokemon/{pokemon_id}').get_data(as_text=True)

    with app_db.app_context():
        usuario = db.session.get(Usuario, uuid.UUID(app_db.config['TEST_IDS']['jogador']))
        usuario.perfil = 'jogador'
        db.session.commit()

    pagina = client_db.get(f'/jogador/pokemon/{pokemon_id}')
    assert pagina.status_code == 200
    assert 'name="natureza"' not in pagina.get_data(as_text=True)
    resposta = client_db.post(f'/jogador/pokemon/{pokemon_id}', data={
        'natureza': 'Dócil', 'apelido': 'Tentativa proibida',
        'pv_atual': '10', 'status': 'Nenhum',
    })
    assert resposta.status_code == 403
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon.natureza.nome == 'Valente'
        assert pokemon.apelido == 'Original'


@pytest.mark.parametrize('campo,valor', [
    ('especie_nome', 'Charmander'), ('natureza', 'Dócil'),
    ('genero', '♀'), ('shiny', '0'),
])
def test_post_adulterado_e_bloqueado_pelo_backend(app_db, client_db, campo, valor):
    pokemon_id = _criar_como_mestre(app_db, client_db)
    assert client_db.post('/login', data={'login': 'bartz-db', 'senha': 'abc123'}).status_code == 302
    resposta = client_db.post(f'/jogador/pokemon/{pokemon_id}', data={
        'apelido': 'Tentativa proibida', 'pv_atual': '10', 'status': 'Nenhum',
        campo: valor,
    })
    assert resposta.status_code == 403
    with app_db.app_context():
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon.apelido == 'Original'
        assert pokemon.natureza.nome == 'Valente'
        assert pokemon.genero == '♂'
        assert pokemon.shiny is True
        assert pokemon.forma_pokemon.nome == 'Bulbasaur'


def test_servico_recusa_edicao_protegida_por_padrao(app_db, client_db):
    pokemon_id = _criar_como_mestre(app_db, client_db)
    with app_db.app_context():
        contexto = carregar_contexto_pokemon(app_db.config['TEST_IDS']['personagem'])
        resposta, erros = atualizar_pokemon_formulario(
            contexto=contexto, pokemon_id=pokemon_id,
            formulario={'natureza': 'Dócil', 'apelido': 'Tentativa'},
            usuario_responsavel_id=app_db.config['TEST_IDS']['jogador'],
        )
        assert resposta is None
        assert any('Apenas Admin/Mestre ou Tester' in erro for erro in erros)
        pokemon = db.session.get(Pokemon, uuid.UUID(pokemon_id))
        assert pokemon.apelido == 'Original'


def test_tipo_visual_traduz_e_escolhe_cores_por_codigo():
    assert tipo_visual('Fogo') == {'codigo': 'fire', 'nome': 'Fogo'}
    assert tipo_visual('FIRE') == {'codigo': 'fire', 'nome': 'Fogo'}
    assert tipo_visual('Elétrico') == {'codigo': 'electric', 'nome': 'Elétrico'}
    assert tipo_visual('Psychic') == {'codigo': 'psychic', 'nome': 'Psíquico'}
    assert tipo_visual('Fighting') == {'codigo': 'fighting', 'nome': 'Lutador'}
    assert tipo_visual('Bug') == {'codigo': 'bug', 'nome': 'Inseto'}
    assert tipo_visual('Steel') == {'codigo': 'steel', 'nome': 'Metal'}
    assert tipo_visual('Tipo Ankar') == {'codigo': 'personalizado', 'nome': 'Tipo Ankar'}
    raiz = Path(__file__).resolve().parents[1]
    componente = (raiz / 'templates/componentes/tipos.html').read_text(encoding='utf8')
    assert '<img' not in componente
    assert 'etiqueta-tipo--' in componente
    css = (raiz / 'static/css/tipos.css').read_text(encoding='utf8')
    assert all(f'.etiqueta-tipo--{codigo}' in css for codigo in (
        'fire', 'water', 'grass', 'psychic', 'bug', 'steel', 'personalizado',
    ))
    assert not list((raiz / 'static/img/tipos').glob('*.png'))


def test_golpes_detalhados_mais_compactos():
    raiz = Path(__file__).resolve().parents[1]
    html = (raiz / 'templates/jogador/dashboard.html').read_text(encoding='utf8')
    css = (raiz / 'static/css/dashboard.css').read_text(encoding='utf8')
    assert 'pokemon-dashboard-golpe-resumo' in html
    assert 'pokemon-dashboard-golpe-nome' in html
    assert 'pokemon-dashboard-golpe-detalhado dl' not in html
    assert 'pokemon-dashboard-golpe-resumo small' in css
