"""11C — Preferência de ordem, autorização e migração incremental em SQLite."""
from pathlib import Path
from uuid import UUID
import runpy

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select, text

from app.extensions import db
from app.models.db import Item, Personagem, PersonagemItem, Usuario, CampanhaMembro
from app.services.inventario_service import carregar_contexto_inventario
from app.services.senha_service import gerar_hash_senha


def test_migration_preserva_registros_existentes():
    engine = create_engine("sqlite://")
    arquivo = Path(__file__).resolve().parents[1] / "migrations/versions/d11c00000001_ordem_inventario.py"
    mod = runpy.run_path(str(arquivo))
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE personagem_itens (id INTEGER PRIMARY KEY, quantidade INTEGER)"))
        conn.execute(text("INSERT INTO personagem_itens VALUES (1, 7)"))
        with Operations.context(MigrationContext.configure(conn)):
            mod["upgrade"]()
            assert conn.execute(text("SELECT quantidade, ordem_bolsa FROM personagem_itens")).one() == (7, None)
            mod["downgrade"]()
            assert conn.execute(text("SELECT quantidade FROM personagem_itens")).scalar_one() == 7
            assert "ordem_bolsa" not in {c["name"] for c in inspect(conn).get_columns("personagem_itens")}
    engine.dispose()


def test_ordem_persistida_isolada_e_novos_itens_no_final(app_db, client_db):
    with app_db.app_context():
        dono = db.session.get(Personagem, UUID(app_db.config["TEST_IDS"]["personagem"]))
        usuario = Usuario(login="outro-11c", nome="Outro", perfil="jogador", ativo=True,
                          senha_hash=gerar_hash_senha("abc123"))
        outro = Personagem(usuario=usuario, campanha_id=dono.campanha_id, nome="Outro",
                          nivel=1, pv_atual=10, ativo=True)
        db.session.add_all([usuario, outro, CampanhaMembro(campanha_id=dono.campanha_id,
                            usuario=usuario, papel="jogador")])
        a = Item(codigo="ordem-a", nome="Corda", ativo=True)
        b = Item(codigo="ordem-b", nome="Lanterna", ativo=True)
        c = Item(codigo="ordem-c", nome="Machado", ativo=True)
        fruta = db.session.scalar(select(Item).where(Item.codigo == "baga-laranja"))
        db.session.add_all([a, b, c])
        db.session.flush()
        db.session.add_all([PersonagemItem(personagem_id=dono.id, item_id=i.id, quantidade=2)
                            for i in [a, b, fruta]])
        db.session.add(PersonagemItem(personagem_id=outro.id, item_id=c.id, quantidade=1))
        db.session.commit()
        dono_id, outro_id = dono.id, outro.id
        ai, bi, ci, fi = map(lambda i: str(i.id), [a, b, c, fruta])

    assert client_db.post("/login", data={"login": "bartz-db", "senha": "abc123"}).status_code == 302
    url = "/jogador/inventario/ordem"
    for itens in [[ai], [ai, ai], [ai, ci], [ai, fi], ["inválido", ai]]:
        assert client_db.post(url, json={"bolsa": "avulsos", "itens": itens}).status_code == 400
    assert client_db.post(url, json={"bolsa": "outra", "itens": [bi, ai]}).status_code == 400
    assert client_db.post(url, data={"bolsa": "avulsos", "itens": [bi, ai]}).status_code == 400
    assert client_db.post(url, json={"bolsa": "avulsos", "itens": [bi, ai]}).get_json() == {"ok": True}

    with app_db.app_context():
        contexto = carregar_contexto_inventario(dono_id)
        assert [str(r.item_id) for r in contexto.inventario][:2] == [bi, ai]
        assert all(r.quantidade == 2 for r in contexto.inventario)
        outro_registro = db.session.scalar(select(PersonagemItem).where(PersonagemItem.personagem_id == outro_id))
        assert outro_registro.quantidade == 1 and outro_registro.ordem_bolsa is None
        novo = Item(codigo="ordem-novo", nome="Abacate utilitário", ativo=True)
        db.session.add(novo)
        db.session.flush()
        novo_id = novo.id
        db.session.add(PersonagemItem(personagem_id=dono_id, item_id=novo_id, quantidade=2))
        db.session.commit()
        contexto = carregar_contexto_inventario(dono_id)
        assert [str(r.item_id) for r in contexto.inventario if str(r.item_id) != fi] == [bi, ai, str(novo_id)]

    # Alterar personagem na sessão não permite salvar a Bag de outro usuário.
    with client_db.session_transaction() as sess:
        sess["personagem_id"] = str(outro_id)
    assert client_db.post(url, json={"bolsa": "avulsos", "itens": [ci]}).status_code == 403
