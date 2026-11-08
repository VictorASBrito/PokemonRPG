"""Integração contra banco de testes. Não executar sobre PostgreSQL de produção."""
from __future__ import annotations
import uuid
from sqlalchemy import select
from app.extensions import db
from app.models.db import Item, Personagem, Pokemon, PersonagemItem, FormaPokemon, PokemonStatus, StatusCondicao


def preparar(app_db, *,status=False):
    with app_db.app_context():
        p=db.session.get(Personagem,uuid.UUID(app_db.config['TEST_IDS']['personagem']))
        forma=db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo=='charmander'))
        pokemon=Pokemon(personagem_id=p.id,forma_pokemon_id=forma.id,pv_atual=1,localizacao='box',posicao=1,ativo=True)
        codigo='teste-curar-paralisia' if status else 'teste-pocao'
        st=db.session.scalar(select(StatusCondicao).where(StatusCondicao.codigo=='paralisado')) if status else None
        efeito={'tipo':'remover_status','alvo':'pokemon','status_id':str(st.id),'todos':False} if status else {'tipo':'recuperar_pv','alvo':'pokemon','operacao':'fixo','valor':20}
        item=Item(codigo=codigo,nome='Item Teste',consumivel=True,equipavel=False,uso_em_batalha=True,preco=0,efeitos={'versao':1,'efeitos':[efeito]},ativo=True)
        db.session.add_all([pokemon,item]);db.session.flush()
        if status:db.session.add(PokemonStatus(pokemon_id=pokemon.id,status_id=st.id))
        db.session.add(PersonagemItem(personagem_id=p.id,item_id=item.id,quantidade=2));db.session.commit()
        return str(p.id),str(item.id),str(pokemon.id)


def _mestre(client):
    assert client.post('/login',data={'login':'mestre-db','senha':'senha-db'}).status_code in (302,303)


def test_cura_exige_alvo_e_consome_uma_unidade(app_db,client_db):
    p,i,k=preparar(app_db);_mestre(client_db)
    route=f'/mestre/jogadores/{p}/inventario/usar'
    client_db.post(route,data={'item_id':i,'quantidade':'1'})
    with app_db.app_context():
        assert db.session.get(Pokemon,uuid.UUID(k)).pv_atual==1
        assert db.session.scalar(select(PersonagemItem.quantidade).where(PersonagemItem.item_id==uuid.UUID(i)))==2
    client_db.post(route,data={'item_id':i,'pokemon_id':k,'quantidade':'1'})
    with app_db.app_context():
        assert db.session.get(Pokemon,uuid.UUID(k)).pv_atual>1
        assert db.session.scalar(select(PersonagemItem.quantidade).where(PersonagemItem.item_id==uuid.UUID(i)))==1


def test_remocao_status_no_pokemon_correto(app_db,client_db):
    p,i,k=preparar(app_db,status=True);_mestre(client_db)
    route=f'/mestre/jogadores/{p}/inventario/usar'
    client_db.post(route,data={'item_id':i,'pokemon_id':k,'quantidade':'1'})
    with app_db.app_context():
        assert db.session.scalar(select(PokemonStatus.id).where(PokemonStatus.pokemon_id==uuid.UUID(k))) is None
        assert db.session.scalar(select(PersonagemItem.quantidade).where(PersonagemItem.item_id==uuid.UUID(i)))==1
    # Não consumir ao tentar tratar uma condição já ausente.
    client_db.post(route,data={'item_id':i,'pokemon_id':k,'quantidade':'1'})
    with app_db.app_context():
        assert db.session.scalar(select(PersonagemItem.quantidade).where(PersonagemItem.item_id==uuid.UUID(i)))==1
