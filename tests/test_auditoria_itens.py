"""Regressões para o novo diagnóstico read-only de itens."""
from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models.db import Item
from app.services.auditoria_itens_service import auditar_itens


def _categoria():
    return [{"id": "1", "codigo": "bagas", "nome": "Bagas", "ativo": True}]


def _item(**alteracoes):
    item = {
        "codigo": "baga-laranja", "nome": "Baga Laranja", "categoria_id": "1",
        "preco": 200, "ativo": True, "consumivel": True, "equipavel": True,
        "uso_em_batalha": True,
        "efeitos": {"versao": 1, "efeitos": [
            {"tipo": "recuperar_pv", "alvo": "pokemon", "operacao": "fixo", "valor": 10}
        ]},
    }
    item.update(alteracoes)
    return item


def test_auditoria_dados_corretos_nao_aponta_inconsistencias():
    resultado = auditar_itens([_item()], _categoria())
    assert resultado.total_itens == 1
    assert resultado.categorias == {"bagas": 1}
    assert resultado.erros == 0
    assert resultado.avisos == 0


def test_auditoria_distingue_erro_de_aviso_e_detecta_duplicacoes():
    dados = [
        _item(efeitos={"versao": 1, "efeitos": "invalido"}),
        _item(codigo="BAGA-LARANJA", preco=1_000_000_000, nome="baga laranja"),
    ]
    resultado = auditar_itens(dados, _categoria())
    assert resultado.erros >= 3  # documento, preço, código em caixa diferente
    assert resultado.avisos >= 1  # provável duplicata de nome
    assert any("lista 'efeitos'" in a.mensagem for a in resultado.achados)
    assert any("Códigos equivalentes" in a.mensagem for a in resultado.achados)


def test_auditoria_referencias_de_efeitos_invalidas():
    item = _item(efeitos={"versao": 1, "efeitos": [
        {"tipo": "remover_status", "status_id": "status-desconhecido"},
        {"tipo": "alterar_atributo", "atributo": "forca-inexistente"},
        {"tipo": "modificar_calculo", "chave": "x", "tipo_id": "tipo-inexistente"},
        {"tipo": ["malformado"]},
    ]})
    resultado = auditar_itens([item], _categoria())
    assert resultado.erros == 4


def test_auditoria_informa_formato_legado_como_aviso():
    resultado = auditar_itens([_item(efeitos={"texto": "Um efeito narrativo."})], _categoria())
    assert resultado.erros == 0
    assert resultado.avisos == 1


def test_comando_auditar_itens_nao_altera_o_banco(app_db):
    with app_db.app_context():
        item = db.session.execute(select(Item).where(Item.codigo == "baga-laranja")).scalar_one()
        antes = (item.preco, item.efeitos)
    resultado = app_db.test_cli_runner().invoke(args=["catalogo", "auditar-itens"])
    assert resultado.exit_code == 0, resultado.output
    assert "somente leitura" in resultado.output
    assert "0 erro(s), 0 aviso(s)" in resultado.output
    with app_db.app_context():
        item = db.session.execute(select(Item).where(Item.codigo == "baga-laranja")).scalar_one()
        assert (item.preco, item.efeitos) == antes


def test_comando_auditar_itens_encontra_documento_efeitos_malformado(app_db):
    with app_db.app_context():
        item = db.session.execute(select(Item).where(Item.codigo == "baga-laranja")).scalar_one()
        item.efeitos = {"versao": 1, "efeitos": {"tipo": "texto"}}
        db.session.commit()
    resultado = app_db.test_cli_runner().invoke(args=["catalogo", "auditar-itens", "--todos"])
    assert resultado.exit_code != 0
    assert "Documento de efeitos sem lista" in resultado.output
    with app_db.app_context():
        item = db.session.execute(select(Item).where(Item.codigo == "baga-laranja")).scalar_one()
        assert item.efeitos == {"versao": 1, "efeitos": {"tipo": "texto"}}
