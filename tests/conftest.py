from __future__ import annotations

from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models.db import (
    Atributo,
    Campanha,
    CampanhaMembro,
    CategoriaGolpe,
    CategoriaItem,
    ConjuntoRegras,
    EspeciePokemon,
    FormaPokemon,
    FormaPokemonAtributo,
    FormaPokemonTipo,
    Golpe,
    Item,
    Natureza,
    NaturezaModificador,
    Personagem,
    PersonagemAtributo,
    Regra,
    RegraValor,
    StatusCondicao,
    TipoPokemon,
    Usuario,
)
from app.services.senha_service import gerar_hash_senha


@pytest.fixture()
def app_db(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'pokemon.sqlite'}")
    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="teste",
        UPLOAD_IMAGENS_DIR=tmp_path / "uploads",
        UPLOAD_IMAGEM_MAX_BYTES=1024 * 1024,
    )

    with app.app_context():
        db.create_all()

        campanha = Campanha(codigo="ankar", nome="Ankar", ativo=True)
        mestre = Usuario(
            login="mestre-db",
            nome="Mestre do Banco",
            senha_hash=gerar_hash_senha("senha-db"),
            perfil="mestre",
            ativo=True,
        )
        jogador = Usuario(
            login="bartz-db",
            nome="Victor",
            senha_hash=gerar_hash_senha("abc123"),
            perfil="jogador",
            ativo=True,
        )
        personagem = Personagem(
            usuario=jogador,
            campanha=campanha,
            nome="Bartz",
            nivel=48,
            pokedolares=300,
            pv_atual=30,
            estilo_combate="Agressivo",
            numeros_shiny=[7],
            ativo=True,
        )
        db.session.add_all(
            [
                campanha,
                mestre,
                jogador,
                personagem,
                CampanhaMembro(campanha=campanha, usuario=mestre, papel="mestre"),
                CampanhaMembro(campanha=campanha, usuario=jogador, papel="jogador"),
            ]
        )
        db.session.flush()

        atributos_personagem = [
            ("fisico", "Físico"),
            ("destreza", "Destreza"),
            ("saude", "Saúde"),
            ("conhecimento", "Conhecimento"),
            ("comunicacao", "Comunicação"),
            ("espirito", "Espírito"),
        ]
        for ordem, (codigo, nome) in enumerate(atributos_personagem, start=1):
            atributo = Atributo(
                codigo=codigo,
                nome=nome,
                escopo="personagem",
                tipo_valor="inteiro",
                ordem=ordem,
                ativo=True,
            )
            db.session.add(atributo)
            db.session.flush()
            db.session.add(
                PersonagemAtributo(
                    personagem=personagem,
                    atributo=atributo,
                    valor=Decimal("3" if codigo == "saude" else "1"),
                )
            )

        atributos_pokemon: dict[str, Atributo] = {}
        for ordem, (codigo, nome) in enumerate(
            [
                ("pv", "Pontos de Vida"),
                ("ataque", "Ataque"),
                ("defesa", "Defesa"),
                ("ataque_especial", "Ataque Especial"),
                ("defesa_especial", "Defesa Especial"),
                ("velocidade", "Velocidade"),
            ],
            start=20,
        ):
            atributo = Atributo(
                codigo=codigo,
                nome=nome,
                escopo="pokemon",
                tipo_valor="inteiro",
                ordem=ordem,
                ativo=True,
            )
            db.session.add(atributo)
            atributos_pokemon[codigo] = atributo

        conjunto = ConjuntoRegras(
            campanha=campanha,
            nome="Ankar atual",
            versao="1",
            em_uso=True,
            ativo=True,
        )
        db.session.add(conjunto)
        db.session.flush()

        regras = {
            "tamanho-equipe": ("Tamanho da equipe", "limites", "inteiro", 6),
            "tamanho-box": ("Tamanho da Box", "limites", "inteiro", 100),
            "golpes-por-pokemon": ("Golpes por Pokémon", "limites", "inteiro", 4),
            "pv-por-ponto-saude": ("PV por Saúde", "personagem", "inteiro", 10),
            "nivel-minimo": ("Nível mínimo", "personagem", "inteiro", 1),
            "nivel-maximo": ("Nível máximo", "personagem", "inteiro", 100),
            "nivel-inicial": ("Nível inicial", "personagem", "inteiro", 1),
            "limite-numeros-shiny": ("Limite shiny", "personagem", "inteiro", 10),
            "atributos-personagem-config": (
                "Atributos personagem",
                "personagem",
                "json",
                [
                    {"id": codigo, "nome": nome, "minimo": 1, "maximo": 6, "valor_inicial": 1}
                    for codigo, nome in atributos_personagem
                ],
            ),
            "origens-personagem": ("Origens", "personagem", "json", ["Atleta"]),
            "classes-personagem": ("Classes", "personagem", "json", ["Treinador(a)"]),
            "estilos-combate-personagem": (
                "Estilos personagem",
                "personagem",
                "json",
                ["Agressivo", "Resistente", "Tático", "Vigoroso"],
            ),
            "bonus-shiny": (
                "Bônus shiny",
                "pokemon",
                "json",
                {"pv": 10, "ataque": 1, "defesa": 1, "ataque_especial": 1, "defesa_especial": 1, "velocidade": 1},
            ),
            "progressao-pv": (
                "Progressão PV",
                "pokemon",
                "json",
                [{"minimo": 1, "maximo": 999, "par": 1, "impar": 1}],
            ),
            "progressao-atributos": (
                "Progressão atributos",
                "pokemon",
                "json",
                [{"minimo": 0, "maximo": 999, "par": 1, "impar": 1}],
            ),
            "estilos-combate": (
                "Estilos",
                "pokemon",
                "json",
                {"Agressivo": {"ataque": 0.10, "ataque_especial": 0.10}},
            ),
        }
        for codigo, (nome, categoria, tipo, valor) in regras.items():
            regra = Regra(
                codigo=codigo,
                nome=nome,
                categoria=categoria,
                tipo_valor=tipo,
                valor_padrao=valor,
                ativo=True,
            )
            db.session.add(regra)
            db.session.flush()
            db.session.add(RegraValor(conjunto_regras=conjunto, regra=regra, valor=valor))

        tipo_grama = TipoPokemon(codigo="grama", nome="Grama", ativo=True)
        tipo_fogo = TipoPokemon(codigo="fogo", nome="Fogo", ativo=True)
        categoria_fisico = CategoriaGolpe(codigo="fisico", nome="Físico", ativo=True)
        categoria_especial = CategoriaGolpe(codigo="especial", nome="Especial", ativo=True)
        categoria_item = CategoriaItem(codigo="bagas", nome="Bagas", ativo=True)
        item = Item(
            codigo="baga-laranja",
            nome="Baga Laranja",
            categoria=categoria_item,
            preco=200,
            consumivel=True,
            equipavel=True,
            uso_em_batalha=True,
            efeitos={"versao": 1, "efeitos": [{"tipo": "recuperar_pv", "alvo": "pokemon", "operacao": "fixo", "valor": 10}]},
            ativo=True,
        )
        db.session.add_all(
            [tipo_grama, tipo_fogo, categoria_fisico, categoria_especial, categoria_item, item]
        )
        db.session.flush()

        formas: dict[str, FormaPokemon] = {}
        especies = [
            ("bulbasaur", "Bulbasaur", tipo_grama, {"pv": 45, "ataque": 5, "defesa": 5, "ataque_especial": 7, "defesa_especial": 7, "velocidade": 5}),
            ("charmander", "Charmander", tipo_fogo, {"pv": 39, "ataque": 5, "defesa": 4, "ataque_especial": 6, "defesa_especial": 5, "velocidade": 7}),
            ("squirtle", "Squirtle", tipo_grama, {"pv": 44, "ataque": 5, "defesa": 7, "ataque_especial": 5, "defesa_especial": 6, "velocidade": 4}),
            ("caterpie", "Caterpie", tipo_grama, {"pv": 45, "ataque": 3, "defesa": 4, "ataque_especial": 2, "defesa_especial": 2, "velocidade": 5}),
            ("weedle", "Weedle", tipo_grama, {"pv": 40, "ataque": 4, "defesa": 3, "ataque_especial": 2, "defesa_especial": 2, "velocidade": 5}),
            ("pidgey", "Pidgey", tipo_grama, {"pv": 40, "ataque": 5, "defesa": 4, "ataque_especial": 4, "defesa_especial": 4, "velocidade": 6}),
            ("rattata", "Rattata", tipo_grama, {"pv": 30, "ataque": 6, "defesa": 4, "ataque_especial": 3, "defesa_especial": 4, "velocidade": 7}),
        ]
        for codigo, nome, tipo, bases in especies:
            especie = EspeciePokemon(codigo=codigo, nome=nome, ativo=True)
            forma = FormaPokemon(
                especie=especie,
                codigo=codigo,
                nome=nome,
                categoria="normal",
                imagem_url=f"https://img/{codigo}.png",
                imagem_shiny_url=f"https://img/{codigo}-shiny.png",
                ativo=True,
            )
            db.session.add_all([especie, forma])
            db.session.flush()
            db.session.add(FormaPokemonTipo(forma_pokemon=forma, tipo=tipo, posicao=1))
            for atributo_codigo, valor in bases.items():
                db.session.add(
                    FormaPokemonAtributo(
                        forma_pokemon=forma,
                        atributo=atributos_pokemon[atributo_codigo],
                        valor_base=Decimal(str(valor)),
                    )
                )
            formas[codigo] = forma

        golpe_arranhao = Golpe(
            codigo="arranhao",
            nome="Arranhão",
            tipo=tipo_grama,
            categoria=categoria_fisico,
            expressao_dano="2d6",
            precisao=Decimal("100"),
            ativo=True,
        )
        golpe_chamas = Golpe(
            codigo="ataque-de-chamas",
            nome="Ataque de Chamas",
            tipo=tipo_fogo,
            categoria=categoria_especial,
            expressao_dano="4d6",
            precisao=Decimal("90"),
            ativo=True,
        )
        docil = Natureza(codigo="docil", nome="Dócil", ativo=True)
        valente = Natureza(codigo="valente", nome="Valente", ativo=True)
        db.session.add_all([golpe_arranhao, golpe_chamas, docil, valente])
        db.session.flush()
        db.session.add_all(
            [
                NaturezaModificador(
                    natureza=valente,
                    atributo=atributos_pokemon["ataque"],
                    tipo_modificador="percentual",
                    valor=Decimal("0.10"),
                ),
                NaturezaModificador(
                    natureza=valente,
                    atributo=atributos_pokemon["velocidade"],
                    tipo_modificador="percentual",
                    valor=Decimal("-0.10"),
                ),
                StatusCondicao(
                    codigo="paralisado",
                    nome="Paralisado",
                    efeitos={
                        "tipo": "alterar_atributo",
                        "atributo": "velocidade",
                        "percentual": -0.5,
                    },
                    ativo=True,
                ),
                StatusCondicao(
                    codigo="queimando",
                    nome="Queimando",
                    efeitos={
                        "tipo": "alterar_atributo",
                        "atributo": "ataque",
                        "percentual": -0.5,
                    },
                    ativo=True,
                ),
            ]
        )
        db.session.commit()

        app.config["TEST_IDS"] = {
            "campanha": str(campanha.id),
            "mestre": str(mestre.id),
            "jogador": str(jogador.id),
            "personagem": str(personagem.id),
            "formas": {codigo: str(forma.id) for codigo, forma in formas.items()},
        }

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client_db(app_db):
    return app_db.test_client()
