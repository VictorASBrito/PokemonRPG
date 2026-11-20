"""10E.1: ordem original da Pokédex em todas as listas de formas e espécies."""
from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models.db import EspeciePokemon, FormaPokemon
from app.services.catalogo_admin_service import listar_formas_admin, opcoes_catalogo
from app.services.pokemon_db_service import listar_formas_ativas, pesquisar_formas_autocomplete


def _preparar_formas(app_db):
    """A carga de produção conserva ordem_catalogo no JSON de cada forma."""
    with app_db.app_context():
        ordem = {
            "bulbasaur": 1,
            "charmander": 5,
            "squirtle": 10,
            "caterpie": 14,
            "weedle": 17,
            "pidgey": 21,
            "rattata": 25,
        }
        for forma in db.session.scalars(select(FormaPokemon)).all():
            forma.configuracoes = {"ordem_catalogo": ordem[forma.codigo]}
        db.session.add(
            FormaPokemon(
                especie=EspeciePokemon(
                    codigo="abomasnow-customizado", nome="Abomasnow", numero=None,
                    ativo=True,
                ),
                codigo="abomasnow-customizado", nome="Abomasnow",
                categoria="personalizada", ativo=True,
            )
        )
        db.session.commit()


def test_formas_seguem_ordem_importada_e_customizadas_por_ultimo(app_db):
    _preparar_formas(app_db)
    with app_db.app_context():
        nomes = [f.nome for f in listar_formas_ativas()]
        assert nomes[:3] == ["Bulbasaur", "Charmander", "Squirtle"]
        assert nomes[-1] == "Abomasnow"
        consulta = listar_formas_admin(por_pagina=36)
        assert [f.nome for f in consulta.itens] == nomes
        opcoes = opcoes_catalogo()
        assert [e.nome for e in opcoes.especies][:3] == [
            "Bulbasaur", "Charmander", "Squirtle"
        ]


def test_autocomplete_sem_busca_segue_pokedex(app_db):
    _preparar_formas(app_db)
    with app_db.app_context():
        nomes = [x["valor"] for x in pesquisar_formas_autocomplete("", limite=20)]
        assert nomes[:3] == ["Bulbasaur", "Charmander", "Squirtle"]
        assert nomes[-1] == "Abomasnow"


def test_catologo_visual_abre_em_bulbasaur(app_db, client_db):
    _preparar_formas(app_db)
    assert client_db.post("/login", data={
        "login": "mestre-db", "senha": "senha-db"
    }).status_code == 302
    pagina = client_db.get("/mestre/catalogo/pokemons")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert html.index("<h2>Bulbasaur</h2>") < html.index("<h2>Charmander</h2>")
    assert html.index("<h2>Charmander</h2>") < html.index("<h2>Abomasnow</h2>")


def test_registros_sem_ordem_usam_numero_nacional_como_fallback(app_db):
    with app_db.app_context():
        formas = db.session.scalars(select(FormaPokemon)).all()
        for f in formas:
            f.configuracoes = None
            f.especie.numero = {"bulbasaur":1,"charmander":4,"squirtle":7,
                                "caterpie":10,"weedle":13,"pidgey":16,
                                "rattata":19}[f.codigo]
        db.session.commit()
        assert [f.nome for f in listar_formas_ativas()][:3] == [
            "Bulbasaur", "Charmander", "Squirtle"
        ]
