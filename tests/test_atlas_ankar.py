"""Testes sem Flask/PostgreSQL: estrutura e fidelidade do catálogo visual."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
JSON = RAIZ / "app/data/catalogo_ankar_visual.json"


def _modulo(nome, path):
    spec = importlib.util.spec_from_file_location(nome, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_extracao_totais_e_tipos():
    c = json.loads(JSON.read_text(encoding="utf-8"))
    assert c["resumo"] == {"locais":119,"rotas":73,"cidades":26,"interesses":20,"tabelas":352,"encontros":2683}
    assert len(c["locais"]) == len({i["id"] for i in c["locais"]})


def test_rota_1_preserva_terrenos_habitats_e_acessos():
    locais = json.loads(JSON.read_text(encoding="utf-8"))["locais"]
    rota = next(i for i in locais if i["id"] == "rota-1")
    assert rota["habitat_principal"] == "Oceano"
    assert rota["habitat_secundario"] == "Profundezas"
    assert rota["terrenos"] == ["Água"]
    assert [t["terreno"] for z in rota["zonas"] for t in z["tabelas"]] == ["ÁGUA","PROFUNDEZAS","PESCA"]
    assert rota["acessos"][0]["destino_id"] == "gym-01-psy"
    t = rota["zonas"][0]["tabelas"][0]["encontros"]
    assert [(e["pokemon"],e["d100"],e["captura"]) for e in t[:4]] == [
        ("Tentacool","1-30",75),("Staryu","31-45",90),("Mantyke","46-55",40),("Pyukumuku","56-60",25)]
    assert t[4]["pokemon"] == "Skrelp" and t[4]["d100"] == "60-75"  # Não reescrever sobreposição.


def test_excel_data_reconstituida_sem_perder_valor_original():
    locais = json.loads(JSON.read_text(encoding="utf-8"))["locais"]
    cidade = next(i for i in locais if i["id"] == "gym-01-psy")
    e = cidade["zonas"][0]["tabelas"][0]["encontros"][0]
    assert e["pokemon"] == "Abra" and e["d100"] == "1-5"
    assert e["faixa_reconstituida"] is True
    assert e["d100_original"] == "43952"


def test_marcardor_x_e_zonas_paralelas_preservados():
    locais = json.loads(JSON.read_text(encoding="utf-8"))["locais"]
    cidade = next(i for i in locais if i["id"] == "gym-01-psy")
    e = cidade["zonas"][0]["tabelas"][0]["encontros"][1]
    assert e["pokemon"] == "x" and e["marcador"] is True and e["d100"] == "6-10"
    caverna = next(i for i in locais if i["id"] == "p-01-caverna-magnetica")
    assert [z["nome"] for z in caverna["zonas"]][:2] == ["ZONA 01","ZONA 02"]
    assert [z["tabelas"][0]["terreno"] for z in caverna["zonas"]][:2] == ["CAVERNA","CAVERNA"]


def test_acessos_para_cidade_com_numero():
    locais = json.loads(JSON.read_text(encoding="utf-8"))["locais"]
    p = next(i for i in locais if i["id"] == "p-02-tunel-dos-pescadores")
    assert any(a["nome"] == "Cidade 7" and a["destino_id"] == "gym-07-bug" for a in p["acessos"])


def test_conversao_d100_nao_inventa_intervalo_invalido():
    m = _modulo("ler_catalogo_ankar", RAIZ / "scripts/gerar_catalogo_ankar.py")
    assert m.faixa_d100(43009) == ("1-10", True, True)
    assert m.faixa_d100("60-75") == ("60-75", False, True)
    assert m.faixa_d100("91-10") == ("91-10", False, False)
    assert m.faixa_d100(None) == ("", False, False)


def test_instalador_e_idempotente_e_nao_altera_jogador(tmp_path):
    m = _modulo("instalador_ankar", RAIZ / "scripts/instalar_atlas_ankar.py")
    (tmp_path/'app').mkdir(); (tmp_path/'templates').mkdir(); (tmp_path/'docs').mkdir()
    app = tmp_path/'app/__init__.py'
    app.write_text("    from app.routes.boxes import boxes_bp\n    app.register_blueprint(boxes_bp)\n",encoding='utf-8')
    base = tmp_path/'templates/base.html'
    alvo = '<a href="{{ url_for(\'combates.painel\') }}">Campo</a>'
    base.write_text(alvo+'\n'+alvo+'\n'+alvo,encoding='utf-8')
    (tmp_path/'docs/CONTINUIDADE_PROJETO.md').write_text('CONTEXTO\n',encoding='utf-8')
    (tmp_path/'docs/DIARIO_DESENVOLVIMENTO.md').write_text('DIÁRIO\n',encoding='utf-8')
    primeira = m.instalar(tmp_path)
    depois = (
        app.read_text(encoding='utf-8'),
        base.read_text(encoding='utf-8'),
        (tmp_path/'docs/DIARIO_DESENVOLVIMENTO.md').read_text(encoding='utf-8'),
    )
    segunda = m.instalar(tmp_path)
    assert primeira['app'] is True and primeira['base'] is True
    assert segunda == {'app':False,'base':False,'docs':[]}
    assert depois == (
        app.read_text(encoding='utf-8'),
        base.read_text(encoding='utf-8'),
        (tmp_path/'docs/DIARIO_DESENVOLVIMENTO.md').read_text(encoding='utf-8'),
    )
    assert base.read_text(encoding='utf-8').count("regiao.indice_ankar") == 2
    assert base.read_text(encoding='utf-8').endswith(alvo)


def test_todos_acessos_vinculados_apontam_para_locais_existentes():
    locais = json.loads(JSON.read_text(encoding='utf-8'))['locais']
    ids = {l['id'] for l in locais}
    assert all(a['destino_id'] in ids for l in locais for a in l['acessos'] if a['destino_id'])
