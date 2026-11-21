"""Trocas pela aplicação Flask: dois participantes, revisão e atomicidade."""
import re
from uuid import UUID

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    CampanhaMembro, HistoricoAlteracao, Personagem, Pokemon, TrocaPokemon, Usuario, Regra, RegraValor,
)
from app.services.senha_service import gerar_hash_senha


@pytest.fixture()
def cenario(app_db):
    with app_db.app_context():
        cfg = app_db.config["TEST_IDS"]
        a = db.session.get(Personagem, UUID(cfg["personagem"]))
        jogadores = [a]
        for n in (2, 3):
            u = Usuario(login=f"troca{n}", nome=f"Jogador {n}", perfil="jogador",
                        senha_hash=gerar_hash_senha("senha-troca"), ativo=True)
            p = Personagem(usuario=u, campanha_id=a.campanha_id, nome=f"Treinador {n}", nivel=48)
            db.session.add_all([u, p, CampanhaMembro(usuario=u, campanha_id=a.campanha_id, papel="jogador")])
            jogadores.append(p)
        db.session.flush()
        ofertas = []
        for jogador in jogadores[:2]:
            lista = []
            for pos in range(1, 5):
                p = Pokemon(personagem_id=jogador.id, forma_pokemon_id=UUID(cfg["formas"]["bulbasaur"]),
                            apelido=f"{jogador.nome} {pos}", localizacao="box", posicao=pos,
                            shiny=pos == 1, pv_atual=10, genero="Macho")
                db.session.add(p)
                lista.append(p)
            ofertas.append(lista)
        db.session.flush()
        saida = ([str(p.id) for p in jogadores], [[str(p.id) for p in lista] for lista in ofertas])
        db.session.commit()
    clientes = [app_db.test_client() for _ in range(3)]
    for c, login, senha in zip(clientes, ("bartz-db", "troca2", "troca3"), ("abc123", "senha-troca", "senha-troca")):
        assert c.post("/login", data={"login": login, "senha": senha}).status_code in (302, 303)
    return app_db, clientes, *saida


def token(c, rota="/jogador/boxes/trocas/"):
    r = c.get(rota)
    assert r.status_code == 200
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.get_data(as_text=True))
    assert m
    return m.group(1)


def iniciar(c, destino):
    r = c.post("/jogador/boxes/trocas/nova", data={"destinatario": destino, "csrf_token": token(c)})
    assert r.status_code == 303
    return r.headers["Location"]


def agir(c, rota, acao, revisao, ids=()):
    r = c.post(rota + "/acao", data={"acao": acao, "revisao": str(revisao),
               "pokemon_id": list(ids), "csrf_token": token(c, rota)})
    assert r.status_code == 303
    return c.get(rota)


def estado(app, rota):
    with app.app_context():
        t = db.session.get(TrocaPokemon, UUID(rota.rsplit("/", 1)[1]))
        return t.estado, t.revisao, t.confirmou_a, t.confirmou_b


@pytest.mark.parametrize("na,nb", [(1, 1), (3, 3), (1, 0), (0, 3), (1, 3)])
def test_troca_conserva_identidades_e_exige_dupla_confirmacao(cenario, na, nb):
    app, (a, b, terceiro), (pa, pb, _), (oa, ob) = cenario
    assert "Trocas Pokémon" in a.get("/jogador/boxes").get_data(as_text=True)
    rota = iniciar(a, pb)
    assert estado(app, rota) == ("pendente", 0, False, False)
    assert terceiro.get(rota).status_code == 404
    assert a.post(rota + "/acao", data={"acao": "aceitar"}).status_code == 403
    agir(a, rota, "aceitar", 0)
    assert estado(app, rota)[0] == "pendente"
    agir(b, rota, "aceitar", 0)
    rev = 1
    if na:
        agir(a, rota, "ofertar", rev, oa[:na])
        rev += 1
    if nb:
        agir(b, rota, "ofertar", rev, ob[:nb])
        rev += 1
    agir(a, rota, "confirmar", rev)
    assert estado(app, rota) == ("negociacao", rev, True, False)
    with app.app_context():
        assert str(db.session.get(Pokemon, UUID(oa[0])).personagem_id) == pa
    agir(b, rota, "confirmar", rev)
    assert estado(app, rota) == ("concluida", rev+1, True, True)
    with app.app_context():
        for ids, origem, destino, n in ((oa, pa, pb, na), (ob, pb, pa, nb)):
            for pos, id_ in enumerate(ids):
                p = db.session.get(Pokemon, UUID(id_))
                assert str(p.personagem_id) == (destino if pos < n else origem)
                assert p.localizacao == "box" and p.pv_atual == 10 and p.shiny == (pos == 0)
        assert len(db.session.scalars(select(Pokemon)).all()) == 8
        assert len(db.session.scalars(select(HistoricoAlteracao).where(HistoricoAlteracao.acao == "troca")).all()) == na+nb
    # Reenvio da confirmação final não duplica a transferência.
    agir(b, rota, "confirmar", rev)
    assert estado(app, rota)[0] == "concluida"


def test_revisao_limite_propriedade_e_cancelamento(cenario):
    app, (a, b, _), (_, pb, _), (oa, ob) = cenario
    rota = iniciar(a, pb)
    agir(b, rota, "aceitar", 0)
    agir(a, rota, "confirmar", 1)  # vazio dos dois lados
    agir(a, rota, "ofertar", 1, oa)  # quatro
    agir(a, rota, "ofertar", 1, ob[:1])  # pertence ao outro
    agir(a, rota, "ofertar", 1, [oa[0], oa[0]])
    assert estado(app, rota) == ("negociacao", 1, False, False)
    agir(a, rota, "ofertar", 1, oa[:1])
    agir(a, rota, "confirmar", 2)
    agir(b, rota, "ofertar", 2, ob[:1])
    assert estado(app, rota) == ("negociacao", 3, False, False)
    agir(a, rota, "confirmar", 2)  # revisão obsoleta
    assert estado(app, rota) == ("negociacao", 3, False, False)
    agir(b, rota, "cancelar", 3)
    assert estado(app, rota)[0] == "cancelada"


def test_box_cheia_e_oferta_indisponivel_nao_transferem(cenario):
    app, (a, b, _), (pa, pb, _), (oa, ob) = cenario
    rota = iniciar(a, pb)
    agir(b, rota, "aceitar", 0)
    agir(a, rota, "ofertar", 1, oa[:1])
    agir(a, rota, "confirmar", 2)
    with app.app_context():
        regra = db.session.scalar(select(Regra).where(Regra.codigo == "tamanho-box"))
        valor = db.session.scalar(select(RegraValor).where(RegraValor.regra_id == regra.id))
        valor.valor = 4
        db.session.commit()
    agir(b, rota, "confirmar", 2)
    assert estado(app, rota) == ("negociacao", 2, True, False)
    with app.app_context():
        p = db.session.get(Pokemon, UUID(oa[0]))
        assert str(p.personagem_id) == pa
        p.localizacao = "equipe"
        db.session.commit()
    agir(b, rota, "confirmar", 2)
    assert estado(app, rota) == ("negociacao", 2, True, False)
    with app.app_context():
        assert str(db.session.get(Pokemon, UUID(oa[0])).personagem_id) == pa
        assert str(db.session.get(Pokemon, UUID(ob[0])).personagem_id) == pb
