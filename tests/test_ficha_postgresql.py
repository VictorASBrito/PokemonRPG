from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models.db import (
    Atributo,
    Campanha,
    CampanhaMembro,
    CategoriaItem,
    ConjuntoRegras,
    HistoricoAlteracao,
    Insignia,
    Item,
    Personagem,
    PersonagemAtributo,
    PersonagemInsignia,
    PersonagemItem,
    Regra,
    RegraValor,
    Usuario,
)
from app.services.importacao.utils import uuid_legado
from app.services.senha_service import gerar_hash_senha


def _app_ficha(monkeypatch, tmp_path: Path):
    banco = tmp_path / "ficha.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{banco}")
    app = create_app()

    origem = Path(__file__).resolve().parent.parent / "data"
    data_dir = tmp_path / "data"
    shutil.copytree(origem, data_dir)
    app.config.update(TESTING=True, SECRET_KEY="teste", DATA_DIR=data_dir)

    tabelas = [
        Usuario.__table__,
        Campanha.__table__,
        CampanhaMembro.__table__,
        Atributo.__table__,
        Regra.__table__,
        ConjuntoRegras.__table__,
        RegraValor.__table__,
        Personagem.__table__,
        PersonagemAtributo.__table__,
        CategoriaItem.__table__,
        Item.__table__,
        PersonagemItem.__table__,
        Insignia.__table__,
        PersonagemInsignia.__table__,
        HistoricoAlteracao.__table__,
    ]
    with app.app_context():
        db.metadata.create_all(db.engine, tables=tabelas)
        campanha = Campanha(codigo="ankar", nome="Ankar", ativo=True)
        usuario = Usuario(
            login="victor-db",
            nome="Victor",
            senha_hash=gerar_hash_senha("abc123"),
            perfil="jogador",
            ativo=True,
        )
        conjunto = ConjuntoRegras(
            campanha=campanha,
            nome="Ankar atual",
            versao="1",
            em_uso=True,
            ativo=True,
        )
        personagem = Personagem(
            id=uuid_legado("personagem", "jog_teste"),
            usuario=usuario,
            campanha=campanha,
            nome="Bartz",
            nivel=48,
            pokedolares=100,
            pv_atual=10,
            ativo=True,
        )
        membro = CampanhaMembro(
            campanha=campanha,
            usuario=usuario,
            papel="jogador",
        )
        db.session.add_all([campanha, usuario, conjunto, personagem, membro])
        db.session.flush()

        for ordem, (codigo, nome) in enumerate(
            [
                ("fisico", "Físico"),
                ("destreza", "Destreza"),
                ("saude", "Saúde"),
                ("conhecimento", "Conhecimento"),
                ("comunicacao", "Comunicação"),
                ("espirito", "Espírito"),
            ],
            start=1,
        ):
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
                    valor=Decimal("1"),
                )
            )

        basicas = {
            "pv-por-ponto-saude": ("PV por Saúde", "inteiro", 10),
            "nivel-minimo": ("Nível mínimo", "inteiro", 1),
            "nivel-maximo": ("Nível máximo", "inteiro", 100),
            "limite-numeros-shiny": ("Limite shiny", "inteiro", 10),
            "tamanho-equipe": ("Tamanho equipe", "inteiro", 6),
        }
        for codigo, (nome, tipo, valor) in basicas.items():
            regra = Regra(
                codigo=codigo,
                nome=nome,
                categoria="personagem",
                tipo_valor=tipo,
                valor_padrao=valor,
                ativo=True,
            )
            db.session.add(regra)
            db.session.flush()
            db.session.add(
                RegraValor(
                    conjunto_regras=conjunto,
                    regra=regra,
                    valor=valor,
                )
            )
        db.session.commit()
    return app


def test_comando_prepara_configuracoes_da_ficha(monkeypatch, tmp_path: Path) -> None:
    app = _app_ficha(monkeypatch, tmp_path)
    runner = app.test_cli_runner()

    resposta = runner.invoke(args=["ficha", "preparar"])
    assert resposta.exit_code == 0, resposta.output
    assert "Configurações da ficha preparadas" in resposta.output

    verificacao = runner.invoke(args=["ficha", "verificar"])
    assert verificacao.exit_code == 0, verificacao.output
    assert "10/10" in verificacao.output


def test_ficha_e_dashboard_usam_postgresql(monkeypatch, tmp_path: Path) -> None:
    app = _app_ficha(monkeypatch, tmp_path)
    runner = app.test_cli_runner()
    assert runner.invoke(args=["ficha", "preparar"]).exit_code == 0

    client = app.test_client()
    assert client.post(
        "/login", data={"login": "victor-db", "senha": "abc123"}
    ).status_code == 302

    resposta = client.post(
        "/jogador/ficha",
        data={
            "nome": "Bartz Atualizado",
            "foto_url": "https://exemplo.com/bartz.png",
            "nivel": "49",
            "idade": "21",
            "genero": "Masculino",
            "origem": "Atleta",
            "classe": "Treinador(a)",
            "estilo_combate": "Agressivo",
            "numeros_shiny": "7, 18",
            "pokedolares": "250",
            "pv_atual": "-5",
            "atributo_fisico": "2",
            "atributo_destreza": "3",
            "atributo_saude": "2",
            "atributo_conhecimento": "1",
            "atributo_comunicacao": "1",
            "atributo_espirito": "1",
            "beneficios_habilidades": "Benefício de teste",
            "anotacoes": "Anotação de teste",
            "item_nome": ["Poção", "Corda"],
            "item_quantidade": ["3", "1"],
            "insignea_nome": ["Insígnia Rocha"],
        },
    )
    assert resposta.status_code == 302

    with app.app_context():
        personagem = db.session.execute(
            select(Personagem).where(Personagem.nome == "Bartz Atualizado")
        ).scalar_one()
        assert personagem.nivel == 49
        assert personagem.pv_atual == -5
        assert personagem.pokedolares == 250
        assert {item.item.nome: item.quantidade for item in personagem.inventario} == {
            "Poção": 3,
            "Corda": 1,
        }
        assert [item.insignia.nome for item in personagem.insignias] == [
            "Insígnia Rocha"
        ]
        assert db.session.scalar(select(HistoricoAlteracao.id)) is not None

    dashboard = client.get("/jogador/dashboard")
    texto = dashboard.get_data(as_text=True)
    assert dashboard.status_code == 200
    assert "Bartz Atualizado" in texto
    assert "49" in texto
    assert "250" in texto
    assert "-5/20" in texto
