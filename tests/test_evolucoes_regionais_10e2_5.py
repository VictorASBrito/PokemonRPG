"""10E.2.5: sanar lacunas das árvores regionais sem afetar campanha."""
from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    EspeciePokemon, EvolucaoPokemon, FormaPokemon, HistoricoAlteracao, Pokemon,
)
from app.services.arvore_evolutiva_service import montar_arvore_evolutiva
from app.services.evolucoes_admin_service import salvar_relacao
from app.services.importacao_evolucoes_service import (
    FRASE_REGIONAIS,
    carregar_base_evolutiva,
    carregar_base_regional,
    consultar_plano_evolucoes,
    verificar_liberacao_individual,
)


def _login(client, login="mestre-db", senha="senha-db"):
    assert client.post("/login", data={"login": login, "senha": senha}).status_code == 302


def _preparar_regionais(app_db):
    """Cria as formas dos 17 vínculos, usando número nacional compartilhado."""
    relacoes = carregar_base_regional()["relacoes"]
    with app_db.app_context():
        existentes = {f.codigo: f for f in db.session.scalars(select(FormaPokemon)).all()}
        por_numero = {
            e.numero: e for e in db.session.scalars(select(EspeciePokemon)).all()
            if e.numero is not None
        }
        desejados = {}
        for relacao in relacoes:
            desejados[relacao["origem"]] = relacao["origem_numero"]
            desejados[relacao["destino"]] = relacao["destino_numero"]
        for codigo, numero in desejados.items():
            if codigo in existentes:
                continue
            especie = por_numero.get(numero)
            if especie is None:
                especie = EspeciePokemon(
                    codigo=f"regional-fixture-{numero}", nome=f"Espécie #{numero}",
                    numero=numero, personalizada=False, ativo=True,
                )
                db.session.add(especie)
                por_numero[numero] = especie
            forma = FormaPokemon(
                especie=especie, codigo=codigo, nome=codigo,
                categoria="regional" if (
                    "-alola" in codigo or "-galar" in codigo
                ) else "normal",
                ativo=True,
            )
            db.session.add(forma)
        db.session.commit()
        return {x.codigo: str(x.id) for x in db.session.scalars(
            select(FormaPokemon).where(FormaPokemon.codigo.in_(desejados.keys()))
        )}


def _simular(app_db):
    resposta = app_db.test_cli_runner().invoke(
        args=["catalogo", "completar-arvores-regionais"]
    )
    assert resposta.exit_code == 0, resposta.output[-1800:]
    assinatura = re.search(r"Assinatura do plano: ([a-f0-9]{64})", resposta.output)
    assert assinatura, resposta.output
    return assinatura.group(1), resposta.output


def _aplicar_args(assinatura):
    return [
        "catalogo", "completar-arvores-regionais", "--aplicar",
        "--plano", assinatura, "--backup-confirmado", "--confirmar",
        FRASE_REGIONAIS,
    ]


def test_auditoria_regionais_fonte_completa_sem_misturar_formas():
    dados = carregar_base_regional()
    assert dados["resumo"] == {
        "total": 17, "automaticas": 8, "niveis": 5,
        "pedras": 3, "especiais": 9,
    }
    rel = dados["relacoes"]
    base = carregar_base_evolutiva()["relacoes"]
    par = lambda r: (r["origem"], r["destino"])
    assert len({par(r) for r in rel + base}) == 447
    pares = {par(r): r for r in rel}
    assert pares[("sandshrew-alola", "sandslash-alola")]["pedra"] == "Pedra do Gelo"
    assert pares[("vulpix-alola", "ninetales-alola")]["pedra"] == "Pedra do Gelo"
    assert pares[("diglett-alola", "dugtrio-alola")]["nivel"] == 26
    assert pares[("geodude-alola", "graveler-alola")]["nivel"] == 25
    assert pares[("grimer-alola", "muk-alola")]["nivel"] == 38
    assert pares[("ponyta-galar", "rapidash-galar")]["nivel"] == 40
    assert pares[("zigzagoon-galar", "linoone-galar")]["nivel"] == 20
    assert pares[("darumaka-galar", "darmanitan-galar-normal")]["pedra"] == "Pedra do Gelo"
    assert all(x["classe"] == "mestre" for x in rel if x["metodo"] == "especial")
    assert pares[("rattata-alola", "raticate-alola")]["nivel_informativo"] == 20
    assert pares[("slowpoke-galar", "slowbro-galar")]["item_especifico"] == "galarica-cuff"
    assert pares[("slowpoke-galar", "slowking-galar")]["item_especifico"] == "galarica-wreath"
    assert ("darmanitan-galar-normal", "darmanitan-galar-zen") not in pares
    assert not any(x["destino"].endswith("-zen") for x in rel)


def test_previa_somente_leitura_e_bloqueios_de_assinatura(app_db):
    _preparar_regionais(app_db)
    assinatura, texto = _simular(app_db)
    assert "8 regulares e 9 especiais" in texto
    assert "SIMULAÇÃO concluída: nenhuma gravação" in texto
    runner = app_db.test_cli_runner()
    for args in [
        ["catalogo", "completar-arvores-regionais", "--aplicar"],
        ["catalogo", "completar-arvores-regionais", "--aplicar", "--plano", assinatura],
        ["catalogo", "completar-arvores-regionais", "--aplicar", "--plano", "0" * 64,
         "--backup-confirmado", "--confirmar", FRASE_REGIONAIS],
    ]:
        resposta = runner.invoke(args=args)
        assert resposta.exit_code != 0, resposta.output
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 0


def test_aplica_17_preserva_pokemon_e_eh_idempotente(app_db):
    ids = _preparar_regionais(app_db)
    with app_db.app_context():
        pokemon = Pokemon(
            personagem_id=uuid.UUID(app_db.config["TEST_IDS"]["personagem"]),
            forma_pokemon_id=uuid.UUID(ids["vulpix-alola"]),
            apelido="Aurora", shiny=True, pv_atual=19, genero="Fêmea",
            localizacao="box", posicao=1, ativo=True,
        )
        db.session.add(pokemon)
        db.session.commit()
        pokemon_id = pokemon.id
    assinatura, _ = _simular(app_db)
    resultado = app_db.test_cli_runner().invoke(args=_aplicar_args(assinatura))
    assert resultado.exit_code == 0, resultado.output[-1800:]
    assert "APLICADO: 17 novos vínculos regionais (8 regulares e 9" in resultado.output
    with app_db.app_context():
        relacoes = list(db.session.scalars(select(EvolucaoPokemon)).all())
        assert len(relacoes) == 17
        assert db.session.scalar(select(func.count(HistoricoAlteracao.id))) == 17
        mestre = [r for r in relacoes if r.requisitos["requer_liberacao_mestre"]]
        assert len(mestre) == 9
        assert all(r.requisitos["liberacao_individual"] for r in mestre)
        assert all(not verificar_liberacao_individual(
            r, autorizada_pelo_mestre=False
        ) for r in mestre)
        assert all(verificar_liberacao_individual(
            r, autorizada_pelo_mestre=True
        ) for r in mestre)
        assert len([r for r in relacoes if not r.requisitos["requer_liberacao_mestre"]]) == 8
        assert all(r.requisitos["origem_importacao"] == "10E.2.5" for r in relacoes)
        todos = {r.forma_destino.codigo: r for r in relacoes}
        assert "região" in todos["raichu-alola"].requisitos["condicao"]
        assert todos["raticate-alola"].requisitos["nivel_informativo"] == 20
        assert todos["darmanitan-galar-normal"].tipo_requisito == "item"
        assert todos["darmanitan-galar-normal"].requisitos["item_nome"] == "Pedra do Gelo"
        salvo = db.session.get(Pokemon, pokemon_id)
        assert (str(salvo.forma_pokemon_id), salvo.apelido, salvo.shiny,
                salvo.pv_atual, salvo.localizacao, salvo.posicao) == (
                    ids["vulpix-alola"], "Aurora", True, 19, "box", 1,
                )
        vulpix = db.session.scalar(select(FormaPokemon).where(
            FormaPokemon.codigo == "vulpix-alola"
        ))
        arvore = montar_arvore_evolutiva(vulpix)
        assert arvore.quantidade_formas == 2
        assert [x.codigo for x in arvore.camadas[1]] == ["ninetales-alola"]

    segunda_assinatura, txt = _simular(app_db)
    assert segunda_assinatura != assinatura
    assert "0 regulares e 0 especiais" in txt
    assert app_db.test_cli_runner().invoke(args=_aplicar_args(segunda_assinatura)).exit_code == 0
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 17


def test_linhas_anteriores_preservadas_e_edicao_nao_libera_especial(app_db):
    ids = _preparar_regionais(app_db)
    with app_db.app_context():
        origem = db.session.scalar(select(FormaPokemon).where(
            FormaPokemon.codigo == "rattata-alola"
        ))
        destino = db.session.scalar(select(FormaPokemon).where(
            FormaPokemon.codigo == "raticate-alola"
        ))
        legado = EvolucaoPokemon(
            forma_origem_id=origem.id, forma_destino_id=destino.id,
            tipo_requisito="especial", requisitos={"tipo_relacao": "evolucao",
                "condicao": "Conceder à campanha", "requer_liberacao_mestre": True},
            ativo=False,
        )
        db.session.add(legado)
        db.session.commit()
        legado_id = legado.id
        plano = consultar_plano_evolucoes(apenas_regionais=True)
        assert plano.ja_existentes == 1
        assert plano.mestre_pendentes == 8
    assinatura, _ = _simular(app_db)
    assert app_db.test_cli_runner().invoke(args=_aplicar_args(assinatura)).exit_code == 0
    with app_db.app_context():
        rel = db.session.get(EvolucaoPokemon, legado_id)
        assert rel.ativo is False
        assert rel.requisitos["condicao"] == "Conceder à campanha"
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 17
        galar = db.session.scalar(select(FormaPokemon).where(
            FormaPokemon.codigo == "slowpoke-galar"
        ))
        slowbro = db.session.scalar(select(FormaPokemon).where(
            FormaPokemon.codigo == "slowbro-galar"
        ))
        especial = db.session.scalar(select(EvolucaoPokemon).where(
            EvolucaoPokemon.forma_origem_id == galar.id,
            EvolucaoPokemon.forma_destino_id == slowbro.id,
        ))
        _, erros = salvar_relacao(galar, {
            "relacao_id": str(especial.id), "destino_id": str(slowbro.id),
            "tipo_relacao": "evolucao", "tipo_requisito": "especial",
            "condicao": "Mestre autoriza com Galárica", "fonte": "mestre",
        }, usuario_id=None)
        assert not erros
        db.session.refresh(especial)
        assert especial.requisitos["requer_liberacao_mestre"] is True
        assert especial.requisitos["liberacao_individual"] is True


def test_web_mestre_previa_csrf_e_confirmacao_isolada(app_db, client_db):
    _preparar_regionais(app_db)
    url = "/mestre/catalogo/pokemons/gerar-arvores?regionais=1"
    assert client_db.get(url).status_code == 302
    _login(client_db, "bartz-db", "abc123")
    assert client_db.get(url).status_code == 302
    client_db.post("/logout")
    _login(client_db)
    pagina = client_db.get(url)
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert "Completar árvores regionais" in html
    assert "Darmanitan" in html
    assert "8" in html and "9" in html
    with client_db.session_transaction() as sess:
        token = sess["arvores_pokemon_csrf"]
    assinatura, _ = _simular(app_db)
    sem_token = client_db.post(url, data={
        "assinatura": assinatura,
        "backup_confirmado": "1", "confirmar": FRASE_REGIONAIS,
    })
    assert sem_token.status_code == 200
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0
    resposta = client_db.post(url, data={
        "csrf_token": token, "assinatura": assinatura,
        "backup_confirmado": "1", "confirmar": FRASE_REGIONAIS,
    })
    assert resposta.status_code == 302
    with app_db.app_context():
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 17


def test_catalogo_incompleto_bloqueia_sem_inserir(app_db):
    with app_db.app_context():
        plano = consultar_plano_evolucoes(apenas_regionais=True)
        assert plano.bloqueios
        assert any("Forma ausente" in x for x in plano.bloqueios)
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0


def test_erro_no_meio_da_operacao_faz_rollback(app_db, monkeypatch):
    _preparar_regionais(app_db)
    assinatura, _ = _simular(app_db)

    def falhar(*args, **kwargs):
        forma = db.session.scalar(select(FormaPokemon).where(
            FormaPokemon.codigo == "vulpix-alola"
        ))
        forma.ativo = False
        db.session.flush()
        raise ValueError("falha simulada após flush")

    monkeypatch.setattr("app.commands.catalogo.aplicar_plano_evolucoes", falhar)
    resultado = app_db.test_cli_runner().invoke(args=_aplicar_args(assinatura))
    assert resultado.exit_code != 0
    with app_db.app_context():
        forma = db.session.scalar(select(FormaPokemon).where(
            FormaPokemon.codigo == "vulpix-alola"
        ))
        assert forma.ativo is True
        assert db.session.scalar(select(func.count(EvolucaoPokemon.id))) == 0
