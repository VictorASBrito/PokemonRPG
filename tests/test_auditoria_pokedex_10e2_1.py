"""Regressões 10E.2.1: auditoria somente leitura da fonte e do PostgreSQL."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models.db import EspeciePokemon, FormaPokemon
from app.services.auditoria_pokedex_service import (
    auditar_pokedex,
    carregar_fonte_pokedex,
    construir_referencia_pokedex,
)


FONTE_MINIMA = [
    {"id": "bulbasaur", "nome": "Bulbasaur", "ordem_catalogo": 1},
    {"id": "venusaur", "nome": "Venusaur", "ordem_catalogo": 2},
    {"id": "venusaur-mega", "nome": "Venusaur (Mega)", "ordem_catalogo": 3},
    {"id": "nidoran", "nome": "Nidoran♀", "ordem_catalogo": 4},
    {"id": "nidoran-2", "nome": "Nidoran♂", "ordem_catalogo": 5},
]


def _especie(nome, codigo=None, numero=None, personalizada=False):
    return SimpleNamespace(
        id=f"especie-{codigo or nome}",
        codigo=codigo or nome.lower(),
        nome=nome,
        numero=numero,
        personalizada=personalizada,
        ativo=True,
    )


def _forma(codigo, nome, especie, ordem):
    return SimpleNamespace(
        id=f"forma-{codigo}",
        codigo=codigo,
        nome=nome,
        especie_id=especie.id,
        configuracoes={"ordem_catalogo": ordem},
        ativo=True,
    )


def _catalogo_correto():
    especies = [
        _especie("Bulbasaur", "bulbasaur", 1),
        _especie("Venusaur", "venusaur", 2),
        _especie("Nidoran♀", "nidoran", 3),
        _especie("Nidoran♂", "nidoran-m", 4),
    ]
    por_nome = {especie.nome: especie for especie in especies}
    formas = [
        _forma(registro["id"], registro["nome"],
               por_nome[registro["nome"].split(" (")[0]],
               registro["ordem_catalogo"])
        for registro in FONTE_MINIMA
    ]
    return especies, formas


def test_referencia_diferencia_formas_numeros_e_simbolos_de_nidoran():
    formas, especies = construir_referencia_pokedex(carregar_fonte_pokedex())
    assert len(formas) == 1064
    assert len(especies) == 898
    assert formas["bulbasaur"].numero == 1
    assert formas["venusaur"].numero == 3
    assert formas["venusaur-mega"].numero == 3
    assert formas["charmander"].numero == 4
    assert formas["nidoran"].numero == 29
    assert formas["nidoran-2"].numero == 32
    assert formas["darmanitan-galar-zen"].numero == 555
    assert formas["morpeko-faminto"].numero == 877
    assert formas["calyrex-cavaleiro-gelado"].numero == 898
    assert especies["Nidoran♀"] == 29 and especies["Nidoran♂"] == 32


def test_referencia_rejeita_ordens_e_codigos_duplicados():
    with pytest.raises(ValueError, match="duplicados"):
        construir_referencia_pokedex([
            FONTE_MINIMA[0],
            {"id": "bulbasaur", "nome": "Bulbasaur", "ordem_catalogo": 2},
        ])
    with pytest.raises(ValueError, match="duplicados"):
        construir_referencia_pokedex([
            FONTE_MINIMA[0],
            {"id": "outra", "nome": "Outra", "ordem_catalogo": 1},
        ])


def test_catalogo_correto_sem_erros_e_mega_compartilha_numero():
    especies, formas = _catalogo_correto()
    resultado = auditar_pokedex(especies, formas, FONTE_MINIMA)
    assert resultado.erros == 0
    assert resultado.avisos == 0
    assert resultado.formas_oficiais_presentes == 5
    assert resultado.especies_fonte == 4
    assert resultado.para_dict()["modo"] == "somente_leitura"


def test_detecta_colisao_legada_nidoran_sem_alterar_instancias():
    especies, formas = _catalogo_correto()
    femea = next(especie for especie in especies if especie.nome == "Nidoran♀")
    especies = [especie for especie in especies if especie.nome != "Nidoran♂"]
    macho = next(forma for forma in formas if forma.codigo == "nidoran-2")
    macho.especie_id = femea.id
    femea.numero = None

    anterior = [(f.codigo, f.especie_id) for f in formas]
    auditoria = auditar_pokedex(
        especies, formas, FONTE_MINIMA,
        pokemons_por_forma={macho.id: 3},
    )
    assert auditoria.erros >= 2
    tipos = {(a.tipo, a.codigo) for a in auditoria.achados}
    assert ("vinculo_especie_incorreto", "nidoran-2") in tipos
    assert ("especie_oficial_ausente", "Nidoran♂") in tipos
    assert ("numero_nacional_ausente", "nidoran") in tipos
    assert next(
        a for a in auditoria.achados if a.tipo == "vinculo_especie_incorreto"
    ).pokemons_ativos == 3
    assert [(f.codigo, f.especie_id) for f in formas] == anterior
    assert femea.numero is None


def test_detecta_numeracao_ordem_e_formas_faltantes_sem_corrigir():
    especies, formas = _catalogo_correto()
    especies[1].numero = 999
    mega = next(forma for forma in formas if forma.codigo == "venusaur-mega")
    venusaur = next(forma for forma in formas if forma.codigo == "venusaur")
    venusaur.configuracoes = {"ordem_catalogo": 800}
    formas.remove(mega)
    # Formas ausentes e ordem divergente devem ser avisos separados.
    resultado = auditar_pokedex(especies, formas, FONTE_MINIMA)
    tipos = {(a.tipo, a.codigo) for a in resultado.achados}
    assert ("numero_nacional_incorreto", "venusaur") in tipos
    assert ("ordem_forma_divergente", "venusaur") in tipos
    assert ("forma_oficial_ausente", "venusaur-mega") in tipos
    assert especies[1].numero == 999
    assert venusaur.configuracoes == {"ordem_catalogo": 800}


def test_personalizada_sem_numero_e_valida_mas_colisao_gera_aviso():
    especies, formas = _catalogo_correto()
    inedita = _especie("Forma de Ankar", "ankar", numero=None, personalizada=True)
    especies.append(inedita)
    assert auditar_pokedex(especies, formas, FONTE_MINIMA).avisos == 0
    inedita.numero = 2
    resultado = auditar_pokedex(especies, formas, FONTE_MINIMA)
    assert any(a.tipo == "numero_personalizado_colide_nacional" for a in resultado.achados)


def test_json_escapa_simbolos_windows_cp1252(app_db):
    """Exportação JSON deve funcionar com stdout cp1252 do Windows."""
    from app.services.auditoria_pokedex_service import (
        auditar_pokedex, carregar_fonte_pokedex,
    )
    from app.commands.catalogo import _texto_compativel_saida

    assert _texto_compativel_saida("Nidoran♂", codificacao="cp1252") == r"Nidoran\u2642"
    assert _texto_compativel_saida("Nidoran♀", codificacao="cp1252") == r"Nidoran\u2640"
    assert _texto_compativel_saida("Pokémon", codificacao="cp1252") == "Pokémon"
    assert _texto_compativel_saida("Nidoran♂", codificacao="utf-8") == "Nidoran♂"

    runner = app_db.test_cli_runner()
    resposta = runner.invoke(args=["catalogo", "auditar-pokedex", "--json"])
    assert resposta.exit_code == 0, resposta.output[-1800:]
    assert "Nidoran\\u2642" in resposta.output
    assert "Nidoran\\u2640" in resposta.output
    resposta.output.encode("cp1252")  # não deve lançar UnicodeEncodeError
    dados = json.loads(resposta.output)
    assert any(
        "Nidoran♂" in achado["mensagem"] for achado in dados["achados"]
    )
    assert dados["modo"] == "somente_leitura"

    # Modo texto deve ser legível em terminais antigos: só símbolos
    # fora de cp1252 são escapados, preservando acentos disponíveis.
    resultado = auditar_pokedex([], [], carregar_fonte_pokedex())
    aviso = next(
        a.mensagem for a in resultado.achados if "Nidoran♂" in a.mensagem
    )
    legivel = _texto_compativel_saida(aviso, codificacao="cp1252")
    assert r"Nidoran\u2642" in legivel
    legivel.encode("cp1252")


def test_cli_pokedex_texto_json_e_somente_leitura(app_db):
    with app_db.app_context():
        especie = db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "bulbasaur")
        )
        forma = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "bulbasaur")
        )
        antes = (especie.numero, forma.especie_id, forma.configuracoes)
    runner = app_db.test_cli_runner()
    texto = runner.invoke(args=["catalogo", "auditar-pokedex"])
    assert texto.exit_code == 0, texto.output[-1800:]
    assert "SOMENTE LEITURA" in texto.output
    assert "numero_nacional_ausente" in texto.output
    assert "898 espécie(s)" in texto.output
    assert "1064 forma(s)" in texto.output

    resposta_json = runner.invoke(args=["catalogo", "auditar-pokedex", "--json"])
    assert resposta_json.exit_code == 0, resposta_json.output[-1800:]
    dados = json.loads(resposta_json.output)
    assert dados["modo"] == "somente_leitura"
    assert dados["fonte"] == {"formas": 1064, "especies": 898}
    assert dados["avisos"] > 0

    with app_db.app_context():
        especie = db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "bulbasaur")
        )
        forma = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "bulbasaur")
        )
        assert (especie.numero, forma.especie_id, forma.configuracoes) == antes


def test_cli_sinaliza_erro_vinculo_mas_nao_modifica_registro(app_db):
    with app_db.app_context():
        forma = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "bulbasaur")
        )
        especie_errada = db.session.scalar(
            select(EspeciePokemon).where(EspeciePokemon.codigo == "charmander")
        )
        forma.especie_id = especie_errada.id
        db.session.commit()
        id_vinculo = forma.especie_id

    resultado = app_db.test_cli_runner().invoke(
        args=["catalogo", "auditar-pokedex", "--todos"]
    )
    assert resultado.exit_code != 0
    assert "vinculo_especie_incorreto" in resultado.output
    assert "nenhuma alteração foi aplicada" in resultado.output
    with app_db.app_context():
        forma = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "bulbasaur")
        )
        assert forma.especie_id == id_vinculo
