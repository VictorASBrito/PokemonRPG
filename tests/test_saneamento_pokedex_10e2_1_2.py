"""10E.2.1.2: reparo seguro e auditável, com autorização em duas etapas."""
from __future__ import annotations

import re
import uuid
from types import SimpleNamespace

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import EspeciePokemon, FormaPokemon, HistoricoAlteracao, Pokemon
from app.services.auditoria_pokedex_service import (
    auditar_pokedex,
    carregar_fonte_pokedex,
    construir_referencia_pokedex,
)
from app.services.importacao.catalogo_importer import CatalogoImporter
from app.services.importacao.utils import categoria_forma
from app.services.saneamento_pokedex_service import (
    CONFIRMACAO_SANEAMENTO,
    codigo_especie_oficial,
    planejar_saneamento,
)


def _preparar_legado_completo(app_db):
    """Replica as 897 espécies NULL / 1064 formas do relatório enviado."""
    fonte = carregar_fonte_pokedex()
    formas_referencia, especies_referencia = construir_referencia_pokedex(fonte)
    with app_db.app_context():
        especies_existentes = {
            e.codigo: e for e in db.session.scalars(select(EspeciePokemon)).all()
        }
        for nome in especies_referencia:
            codigo = codigo_especie_oficial(nome)
            if nome == "Nidoran♂":
                continue  # importador antigo juntava os dois sexos
            if codigo not in especies_existentes:
                novo = EspeciePokemon(
                    codigo=codigo, nome=nome, numero=None,
                    personalizada=False, ativo=True,
                )
                db.session.add(novo)
                especies_existentes[codigo] = novo
        db.session.flush()

        formas_existentes = {
            f.codigo: f for f in db.session.scalars(select(FormaPokemon)).all()
        }
        for registro in fonte:
            codigo_forma = registro["id"]
            ref = formas_referencia[codigo_forma]
            codigo_especie = (
                "nidoran" if codigo_forma == "nidoran-2"
                else codigo_especie_oficial(ref.especie)
            )
            especie = especies_existentes[codigo_especie]
            if codigo_forma in formas_existentes:
                forma = formas_existentes[codigo_forma]
                forma.especie_id = especie.id
                forma.configuracoes = {"ordem_catalogo": ref.ordem}
            else:
                forma = FormaPokemon(
                    especie_id=especie.id, codigo=codigo_forma, nome=ref.nome,
                    categoria=categoria_forma(registro), ativo=True,
                    configuracoes={"ordem_catalogo": ref.ordem},
                )
                db.session.add(forma)
                formas_existentes[codigo_forma] = forma

        # As duas formas adicionais do relatório devem sobreviver ao saneamento.
        db.session.add_all([
            FormaPokemon(
                especie_id=especies_existentes["bulbasaur"].id,
                codigo="ankar-extra-1", nome="Bulbasaur (Ankar Extra)",
                categoria="personalizada", ativo=True,
            ),
            FormaPokemon(
                especie_id=especies_existentes["charmander"].id,
                codigo="ankar-extra-2", nome="Charmander (Ankar Extra)",
                categoria="personalizada", ativo=True,
            ),
        ])
        db.session.flush()

        # O reparo do catálogo não deve alterar a instância capturada.
        personagem_id = uuid.UUID(app_db.config["TEST_IDS"]["personagem"])
        pokemon = Pokemon(
            personagem_id=personagem_id,
            forma_pokemon_id=formas_existentes["nidoran-2"].id,
            apelido="Nido de Teste", genero="Macho",
            shiny=True, pv_atual=23, localizacao="box", posicao=1, ativo=True,
        )
        db.session.add(pokemon)
        db.session.commit()
        app_db.config["TEST_POKEMON_SANEAMENTO"] = str(pokemon.id)


def _simular(app_db):
    resultado = app_db.test_cli_runner().invoke(
        args=["catalogo", "sanear-pokedex"]
    )
    assert resultado.exit_code == 0, resultado.output[-2000:]
    assinatura = re.search(r"Assinatura do plano: ([a-f0-9]{64})", resultado.output)
    assert assinatura, resultado.output[-1800:]
    return assinatura.group(1), resultado.output


def test_codigo_especie_diferencia_simbolos_sem_afetar_formas_regionais():
    assert codigo_especie_oficial("Nidoran♀") == "nidoran"
    assert codigo_especie_oficial("Nidoran♂") == "nidoran-m"
    assert codigo_especie_oficial("Venusaur (Mega)") == "venusaur"
    assert codigo_especie_oficial("Darmanitan (Galar Zen)") == "darmanitan"


def test_importador_novo_separa_nidoran_e_reimportacao_idempotente(app_db):
    class Resumo:
        def criado(self, *a): pass
        def atualizado(self, *a): pass
        def removido(self, *a): pass
        def aviso(self, *a): pass

    fonte = SimpleNamespace(catalogo_pokemons={
        "origem": "teste",
        "versao_sistema": "2.5",
        "pokemons": [
            {"id": "nidoran", "nome": "Nidoran♀", "ordem_catalogo": 1,
             "tipos": [], "atributos_base": {}},
            {"id": "nidoran-2", "nome": "Nidoran♂", "ordem_catalogo": 2,
             "tipos": [], "atributos_base": {}},
        ],
    })
    with app_db.app_context():
        for _ in range(2):
            importer = CatalogoImporter(fonte, Resumo())
            importer.importar_especies_formas()
            db.session.commit()
        especies = {
            e.codigo: e for e in db.session.scalars(
                select(EspeciePokemon).where(
                    EspeciePokemon.codigo.in_(["nidoran", "nidoran-m"])
                )
            )
        }
        assert len(especies) == 2
        assert especies["nidoran"].nome == "Nidoran♀"
        assert especies["nidoran-m"].nome == "Nidoran♂"
        femea = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "nidoran"))
        macho = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "nidoran-2"))
        assert femea.especie_id == especies["nidoran"].id
        assert macho.especie_id == especies["nidoran-m"].id


def test_simulacao_obrigatoria_e_garantias_de_backup(app_db):
    _preparar_legado_completo(app_db)
    assinatura, output = _simular(app_db)
    assert "Numeros nacionais NULL a preencher: 897." in output
    assert "Criar especie Nidoran macho (nidoran-m): sim." in output
    assert "Religar forma nidoran-2: sim." in output
    assert "Formas extras preservadas: 2." in output
    assert "Operacoes propostas: 899." in output
    assert "nenhuma gravacao" in output

    runner = app_db.test_cli_runner()
    for args in [
        ["--aplicar"],
        ["--aplicar", "--plano", "0" * 64,
         "--backup-confirmado", "--confirmar", CONFIRMACAO_SANEAMENTO],
        ["--aplicar", "--plano", assinatura,
         "--confirmar", CONFIRMACAO_SANEAMENTO],
        ["--aplicar", "--plano", assinatura, "--backup-confirmado"],
    ]:
        falhou = runner.invoke(args=["catalogo", "sanear-pokedex", *args])
        assert falhou.exit_code != 0, falhou.output[-1200:]

    with app_db.app_context():
        assert db.session.scalar(select(func.count(EspeciePokemon.id))) == 897
        assert db.session.scalar(select(func.count(FormaPokemon.id))) == 1066
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 0
        assert db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "nidoran-m")
        ) is None
        assert db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "bulbasaur")
        ).numero is None


def test_aplicacao_atomica_auditoria_limpa_idempotencia_e_pokemon_intacto(app_db):
    _preparar_legado_completo(app_db)
    assinatura, _ = _simular(app_db)
    with app_db.app_context():
        original = db.session.scalar(select(Pokemon).where(Pokemon.apelido == "Nido de Teste"))
        antes = (
            str(original.id), original.forma_pokemon_id, original.apelido,
            original.genero, original.shiny, original.pv_atual,
            original.localizacao, original.posicao,
        )
        extras_antes = {
            f.codigo: str(f.id) for f in db.session.scalars(
                select(FormaPokemon).where(
                    FormaPokemon.codigo.in_(["ankar-extra-1", "ankar-extra-2"])
                )
            )
        }
    resultado = app_db.test_cli_runner().invoke(args=[
        "catalogo", "sanear-pokedex", "--aplicar",
        "--plano", assinatura, "--backup-confirmado",
        "--confirmar", CONFIRMACAO_SANEAMENTO,
    ])
    assert resultado.exit_code == 0, resultado.output[-1800:]
    assert "897 numeros, 1 especie criada, 1 vinculo corrigido" in resultado.output

    with app_db.app_context():
        especies = list(db.session.scalars(select(EspeciePokemon)).all())
        formas = list(db.session.scalars(select(FormaPokemon)).all())
        assert len(especies) == 898
        assert len(formas) == 1066
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 899
        auditoria = auditar_pokedex(especies, formas, carregar_fonte_pokedex())
        assert auditoria.erros == 0
        assert auditoria.avisos == 0
        por_codigo = {e.codigo: e for e in especies}
        assert por_codigo["bulbasaur"].numero == 1
        assert por_codigo["charmander"].numero == 4
        assert por_codigo["nidoran"].numero == 29
        assert por_codigo["nidoran-m"].numero == 32
        assert por_codigo["calyrex"].numero == 898
        macho = next(f for f in formas if f.codigo == "nidoran-2")
        assert macho.especie_id == por_codigo["nidoran-m"].id
        original = db.session.scalar(select(Pokemon).where(Pokemon.apelido == "Nido de Teste"))
        depois = (
            str(original.id), original.forma_pokemon_id, original.apelido,
            original.genero, original.shiny, original.pv_atual,
            original.localizacao, original.posicao,
        )
        assert antes == depois
        extras_depois = {
            f.codigo: str(f.id) for f in formas
            if f.codigo in ["ankar-extra-1", "ankar-extra-2"]
        }
        assert extras_depois == extras_antes

    nova_assinatura, nova_simulacao = _simular(app_db)
    assert nova_assinatura != assinatura
    assert "Operacoes propostas: 0." in nova_simulacao


def test_bloqueia_numero_nacional_incorreto_sem_sobrescrever(app_db):
    _preparar_legado_completo(app_db)
    with app_db.app_context():
        especie = db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "bulbasaur")
        )
        especie.numero = 999
        db.session.commit()
        especies = list(db.session.scalars(select(EspeciePokemon)).all())
        formas = list(db.session.scalars(select(FormaPokemon)).all())
        plano = planejar_saneamento(especies, formas, carregar_fonte_pokedex())
        assert plano.bloqueios
        assert any("bulbasaur" in b for b in plano.bloqueios)

    falha = app_db.test_cli_runner().invoke(args=["catalogo", "sanear-pokedex"])
    assert falha.exit_code != 0
    assert "BLOQUEADO" in falha.output
    with app_db.app_context():
        especie = db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "bulbasaur")
        )
        assert especie.numero == 999
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 0


def test_erro_no_meio_da_aplicacao_desfaz_escritas_ja_executadas(app_db, monkeypatch):
    """Uma falha apos flush deve acionar rollback, nao commit parcial."""
    _preparar_legado_completo(app_db)
    assinatura, _ = _simular(app_db)

    def interromper(plano, especies, formas, fonte):
        bulbasaur = next(e for e in especies if e.codigo == "bulbasaur")
        bulbasaur.numero = 1
        db.session.flush()
        raise ValueError("falha injetada apos o flush")

    monkeypatch.setattr("app.commands.catalogo.aplicar_saneamento", interromper)
    resultado = app_db.test_cli_runner().invoke(args=[
        "catalogo", "sanear-pokedex", "--aplicar",
        "--plano", assinatura, "--backup-confirmado",
        "--confirmar", CONFIRMACAO_SANEAMENTO,
    ])
    assert resultado.exit_code != 0
    with app_db.app_context():
        bulbasaur = db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "bulbasaur")
        )
        assert bulbasaur.numero is None
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 0
        assert db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "nidoran-m")
        ) is None
