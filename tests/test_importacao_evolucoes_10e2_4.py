"""10E.2.4: geração oficial de 430 árvores / autorização individual."""
from __future__ import annotations

import re
import uuid
from collections import Counter

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    EspeciePokemon, EvolucaoPokemon, FormaPokemon, HistoricoAlteracao, Pokemon
)
from app.services.arvore_evolutiva_service import montar_arvore_evolutiva
from app.services.evolucoes_admin_service import salvar_relacao
from app.services.importacao_evolucoes_service import (
    FRASE_CONFIRMACAO,
    carregar_base_evolutiva,
    consultar_plano_evolucoes,
    planejar_importacao_evolucoes,
    verificar_liberacao_individual,
)


def _login(client, login="mestre-db", senha="senha-db"):
    assert client.post("/login", data={"login": login, "senha": senha}).status_code == 302


def _montar_catalogo_minimo(app_db):
    """Inclui somente as formas presentes nos 430 arcos da fonte revisada."""
    dados = carregar_base_evolutiva()["relacoes"]
    with app_db.app_context():
        existentes = {
            f.codigo: f for f in db.session.scalars(select(FormaPokemon)).all()
        }
        desejados = {}
        for rel in dados:
            desejados[rel["origem"]] = rel["origem_numero"]
            desejados[rel["destino"]] = rel["destino_numero"]
        for codigo, numero in desejados.items():
            if codigo in existentes:
                continue
            especie = EspeciePokemon(
                codigo=f"teste-evolucao-{codigo}", nome=codigo,
                numero=numero, personalizada=False, ativo=True,
            )
            forma = FormaPokemon(
                especie=especie, codigo=codigo, nome=codigo,
                categoria="regional" if codigo.endswith("-galar") else "normal",
                ativo=True,
            )
            db.session.add(forma)
        db.session.commit()
    return desejados


def _plano_sem_gravar(app_db):
    runner = app_db.test_cli_runner()
    resposta = runner.invoke(args=["catalogo", "gerar-arvores-pokemon"])
    assert resposta.exit_code == 0, resposta.output[-2000:]
    m = re.search(r"Assinatura do plano: ([a-f0-9]{64})", resposta.output)
    assert m is not None
    return m.group(1), resposta.output


def _confirmado(assinatura):
    return [
        "catalogo", "gerar-arvores-pokemon", "--aplicar",
        "--plano", assinatura, "--backup-confirmado", "--confirmar",
        FRASE_CONFIRMACAO,
    ]


def test_base_pokeapi_completa_e_categorias_conservadoras():
    dados = carregar_base_evolutiva()
    assert dados["numero_maximo"] == 898
    assert dados["resumo"] == {
        "total": 430, "auto": 340, "level": 297,
        "stones": 43, "manual": 90, "unmapped": 0, "conflicting": 0,
    }
    relacoes = dados["relacoes"]
    destinos = {r["destino"]: r for r in relacoes}
    assert len(destinos) == 430
    assert destinos["charmeleon"]["nivel"] == 16
    assert destinos["charizard"]["nivel"] == 36
    assert destinos["vaporeon"]["pedra"] == "Pedra da Água"
    assert destinos["leafeon"]["pedra"] == "Pedra da Folha"
    assert destinos["glaceon"]["pedra"] == "Pedra do Gelo"
    assert all(destinos[x]["classe"] == "mestre" for x in (
        "espeon", "umbreon", "sylveon", "gallade", "froslass",
        "porygon2", "porygon-z", "obstagoon", "sirfetch-d",
    ))
    assert destinos["nidorino"]["origem"] == "nidoran-2"
    assert destinos["perrserker"]["origem"] == "meowth-galar"
    assert destinos["mr-rime"]["origem"] == "mr-mime-galar"
    assert destinos["vivillon"]["nivel"] == 12
    assert all(x["classe"] == "automatica" for x in relacoes if x["metodo"] == "pedra")


def test_simulacao_nao_grava_e_exige_backup_assinatura(app_db):
    _montar_catalogo_minimo(app_db)
    assinatura, texto = _plano_sem_gravar(app_db)
    assert "340 regulares + 90 com liberação individual" in texto
    assert "SIMULAÇÃO: somente leitura" in texto
    runner = app_db.test_cli_runner()
    for args in [
        ["catalogo", "gerar-arvores-pokemon", "--aplicar"],
        ["catalogo", "gerar-arvores-pokemon", "--aplicar", "--plano", assinatura],
        ["catalogo", "gerar-arvores-pokemon", "--aplicar", "--plano", "0" * 64,
         "--backup-confirmado", "--confirmar", FRASE_CONFIRMACAO],
    ]:
        resposta = runner.invoke(args=args)
        assert resposta.exit_code != 0, resposta.output
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 0


def test_aplicacao_430_relacoes_idempotente_e_100pct_preservacao_da_box(app_db):
    _montar_catalogo_minimo(app_db)
    with app_db.app_context():
        charmander = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "charmander")
        )
        pokemon = Pokemon(
            personagem_id=uuid.UUID(app_db.config["TEST_IDS"]["personagem"]),
            forma_pokemon_id=charmander.id, apelido="Chaminha",
            shiny=True, pv_atual=21, genero="Macho", localizacao="box",
            posicao=1, ativo=True,
        )
        db.session.add(pokemon)
        db.session.commit()
        pokemon_id, original_forma = pokemon.id, pokemon.forma_pokemon_id
    assinatura, _ = _plano_sem_gravar(app_db)
    resultado = app_db.test_cli_runner().invoke(args=_confirmado(assinatura))
    assert resultado.exit_code == 0, resultado.output[-1800:]
    assert "430 relações criadas" in resultado.output

    with app_db.app_context():
        relacoes = list(db.session.scalars(select(EvolucaoPokemon)).all())
        assert len(relacoes) == 430
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 430
        metodos = Counter(
            ("mestre" if r.requisitos["requer_liberacao_mestre"] else
             r.tipo_requisito)
            for r in relacoes
        )
        assert metodos == {"nivel": 297, "item": 43, "mestre": 90}
        trio = [
            r for r in relacoes
            if r.forma_destino.codigo in {"espeon", "umbreon", "sylveon"}
        ]
        assert len(trio) == 3
        assert all(r.ativo and r.requisitos["liberacao_individual"] for r in trio)
        assert all(not verificar_liberacao_individual(
            r, autorizada_pelo_mestre=False
        ) for r in trio)
        assert all(verificar_liberacao_individual(
            r, autorizada_pelo_mestre=True
        ) for r in trio)
        salvo = db.session.get(Pokemon, pokemon_id)
        assert (salvo.forma_pokemon_id, salvo.shiny, salvo.pv_atual,
                salvo.apelido, salvo.localizacao, salvo.posicao) == (
                    original_forma, True, 21, "Chaminha", "box", 1,
                )
        eevee = db.session.scalar(
            select(FormaPokemon).where(FormaPokemon.codigo == "eevee")
        )
        arvore = montar_arvore_evolutiva(eevee)
        assert arvore.total_relacoes_permanentes == 8
        assert len(arvore.camadas) == 2
        assert any(
            "liberação individual" in a.requisito.lower()
            for no in arvore.camadas[1] for a in no.predecessores
        )

    nova_assinatura, texto = _plano_sem_gravar(app_db)
    assert nova_assinatura != assinatura
    assert "0 regulares + 0 com liberação individual" in texto
    segunda = app_db.test_cli_runner().invoke(args=_confirmado(nova_assinatura))
    assert segunda.exit_code == 0, segunda.output
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 430


def test_preserva_relacao_existente_e_bloqueio_mestre_em_edicao(app_db):
    _montar_catalogo_minimo(app_db)
    with app_db.app_context():
        eevee = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "eevee"))
        espeon = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "espeon"))
        # Referência cadastrada antes do importador nunca é sobrescrita.
        original = EvolucaoPokemon(
            forma_origem_id=eevee.id, forma_destino_id=espeon.id,
            tipo_requisito="especial",
            requisitos={"tipo_relacao": "evolucao", "condicao": "Evento da campanha",
                        "requer_liberacao_mestre": True},
            ativo=False,
        )
        db.session.add(original)
        db.session.commit()
        original_id = original.id
        plano = consultar_plano_evolucoes()
        assert plano.ja_existentes == 1
        assert plano.mestre_pendentes == 89

    assinatura, _ = _plano_sem_gravar(app_db)
    resposta = app_db.test_cli_runner().invoke(args=_confirmado(assinatura))
    assert resposta.exit_code == 0, resposta.output
    with app_db.app_context():
        rel = db.session.get(EvolucaoPokemon, original_id)
        assert rel.ativo is False
        assert rel.requisitos["condicao"] == "Evento da campanha"
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 430

        umbreon = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "umbreon"))
        importada = db.session.scalar(select(EvolucaoPokemon).where(
            EvolucaoPokemon.forma_origem_id == eevee.id,
            EvolucaoPokemon.forma_destino_id == umbreon.id,
        ))
        _, erros = salvar_relacao(eevee, {
            "relacao_id": str(importada.id), "destino_id": str(umbreon.id),
            "tipo_relacao": "evolucao", "tipo_requisito": "especial",
            "condicao": "O mestre decide quando liberar", "fonte": "mestre",
        }, usuario_id=None)
        assert not erros
        db.session.refresh(importada)
        assert importada.requisitos["requer_liberacao_mestre"] is True
        assert importada.requisitos["liberacao_individual"] is True


def test_guarda_exige_mestre_tambem_para_legacy_de_troca_ou_amistade(app_db):
    with app_db.app_context():
        f = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "bulbasaur"))
        for gatilho, requisitos in [
            ("troca", {"tipo_relacao": "evolucao"}),
            ("amizade", {"tipo_relacao": "evolucao"}),
            ("item", {"tipo_relacao": "evolucao", "item_nome": "Disco Dúbio"}),
            ("nivel", {"tipo_relacao": "evolucao", "nivel": 22,
                       "condicao": "Durante a noite"}),
        ]:
            rel = EvolucaoPokemon(
                forma_origem_id=f.id, forma_destino_id=uuid.uuid4(),
                tipo_requisito=gatilho, requisitos=requisitos, ativo=True,
            )
            assert not verificar_liberacao_individual(rel, autorizada_pelo_mestre=False)
            assert verificar_liberacao_individual(rel, autorizada_pelo_mestre=True)


def test_rejeita_catalogo_incompleto_antes_de_escrever(app_db):
    with app_db.app_context():
        plano = consultar_plano_evolucoes()
        assert plano.bloqueios
        assert any("Forma ausente" in e for e in plano.bloqueios)
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0


def test_tela_mestre_tem_previa_csrf_e_confirmacao(app_db, client_db):
    _montar_catalogo_minimo(app_db)
    url = "/mestre/catalogo/pokemons/gerar-arvores"
    assert client_db.get(url).status_code == 302
    _login(client_db, "bartz-db", "abc123")
    assert client_db.get(url).status_code == 302
    client_db.post("/logout")
    _login(client_db)
    response = client_db.get(url)
    assert response.status_code == 200, response.status_code
    assert "340" in response.get_data(as_text=True)
    with client_db.session_transaction() as sess:
        token = sess["arvores_pokemon_csrf"]
    assinatura, _ = _plano_sem_gravar(app_db)
    sem_token = client_db.post(url, data={
        "assinatura": assinatura, "backup_confirmado": "1",
        "confirmar": FRASE_CONFIRMACAO,
    })
    assert sem_token.status_code == 200
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0
    sucesso = client_db.post(url, data={
        "csrf_token": token, "assinatura": assinatura,
        "backup_confirmado": "1", "confirmar": FRASE_CONFIRMACAO,
    })
    assert sucesso.status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 430


def test_roll_back_se_falhar_durante_geracao(app_db, monkeypatch):
    _montar_catalogo_minimo(app_db)
    assinatura, _ = _plano_sem_gravar(app_db)

    def falhar(*args, **kwargs):
        original = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        original.ativo = False
        db.session.flush()
        raise ValueError("falha proposital no meio da transação")

    monkeypatch.setattr("app.commands.catalogo.aplicar_plano_evolucoes", falhar)
    resposta = app_db.test_cli_runner().invoke(args=_confirmado(assinatura))
    assert resposta.exit_code != 0
    with app_db.app_context():
        charmander = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == "charmander"))
        assert charmander.ativo is True
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0
