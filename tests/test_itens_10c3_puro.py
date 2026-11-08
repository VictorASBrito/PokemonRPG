"""Teste sem Flask: confirma estrutura, somatórios e regras de rolagem."""
import ast
import importlib.util
import json
import pathlib
import re
import secrets
from decimal import Decimal
from types import SimpleNamespace
import pytest

ROOT=pathlib.Path(__file__).resolve().parents[1]


def _funcs():
    text=(ROOT/'app/services/efeitos_itens_10c3.py').read_text(encoding='utf-8')
    tree=ast.parse(text)
    wanted={'quantidade_recuperada','efeitos_estruturados','exige_alvo_pokemon'}
    tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
    m=SimpleNamespace();ns={'re':re,'secrets':secrets,'Decimal':Decimal,'Any':object,'TIPOS_TERAPEUTICOS':{'recuperar_pv','remover_status'},'_DADOS':re.compile(r'^([1-9][0-9]?)d([1-9][0-9]{0,2})(?:\+([0-9]{1,4}))?$',re.I)}
    exec(compile(tree,str(ROOT/'app/services/efeitos_itens_10c3.py'),'exec'),ns)
    return SimpleNamespace(**{k:ns[k] for k in wanted})


def test_manifesto_codigo_unico_e_cobre_todas_origens():
    d=json.loads((ROOT/'app/data/itens_padronizados_10c3.json').read_text(encoding='utf-8'))
    origem=[r['origem'] for r in d['origens']]
    metas={r['codigo'] for r in d['padronizados']}
    assert len(origem)==77 and len(set(origem))==77
    assert len(metas)==len(d['padronizados'])==48
    assert all(x['destino'] is None or x['destino'] in metas for x in d['origens'])
    assert sum(x['destino'] is None for x in d['origens'])==21
    assert any(x['codigo']=='mapa-da-regiao-de-ankar' and not x['origens'] for x in d['padronizados'])


def test_terapias_e_diferencas_de_nomes():
    d=json.loads((ROOT/'app/data/itens_padronizados_10c3.json').read_text(encoding='utf-8'))
    mapa={x['origem']:x['destino'] for x in d['origens']}
    assert mapa['importado-ficha-greatball']==mapa['importado-ficha-bola-grande']=='grande-bola'
    assert mapa['importado-ficha-cura-queima']==mapa['importado-ficha-cura-queimaduras']=='cura-queimaduras'
    assert mapa['importado-ficha-colar'] != mapa['importado-ficha-colar-quebrado']
    modelos={x['codigo']:x for x in d['padronizados']}
    assert modelos['pocao']['efeitos_modelo']['efeitos'][0]['valor']==20
    assert modelos['cura-paralisia']['efeitos_modelo']['efeitos'][0]['codigos_status']==['paralisado']
    assert modelos['elixir']['efeitos_modelo'] is None  # PP não automatizado


def test_aplica_regras_de_pv_sem_execucao_arbitraria():
    m=_funcs()
    assert m.quantidade_recuperada({'operacao':'fixo','valor':20},50)==20
    assert m.quantidade_recuperada({'operacao':'percentual','valor':25},80)==20
    assert m.quantidade_recuperada({'operacao':'dados','expressao':'2d6+3'},80,rolar=lambda f:4)==11
    for exp in ['999d999','1d6+99999','__import__("os")','2d6*2']:
        with pytest.raises(ValueError):m.quantidade_recuperada({'operacao':'dados','expressao':exp},80)


def test_identifica_quando_precisa_alvo():
    f=_funcs().exige_alvo_pokemon
    assert f(SimpleNamespace(efeitos={'versao':1,'efeitos':[{'tipo':'recuperar_pv','alvo':'pokemon'}]}))
    assert f(SimpleNamespace(efeitos={'versao':1,'efeitos':[{'tipo':'remover_status','alvo':'pokemon'}]}))
    assert not f(SimpleNamespace(efeitos=None))
    assert not f(SimpleNamespace(efeitos={'versao':1,'efeitos':[{'tipo':'texto','texto':'Especial'}]}))


def test_instalador_idempotente_e_nao_deleta_fontes(tmp_path):
    from importlib.util import spec_from_file_location,module_from_spec
    s=spec_from_file_location('instalador_10c3',ROOT/'scripts/instalar_itens_10c3.py');m=module_from_spec(s);s.loader.exec_module(m)
    files={
        'app/services/inventario_service.py':'''def usar_item_consumivel(\n    *,\n    personagem_id: str,\n    item_id: str,\n    quantidade: Any = 1,\n    usuario_id: str = None,\n):\n    registro = _registro_inventario(personagem.id, item.id, bloquear=True)\n    antes = _snapshot_registro(registro)\n    depois = {\n            "efeitos": item.efeitos,\n    }\n\ndef equipar_item_pokemon(): pass\n''',
        'app/routes/inventario.py':'''from app.services.inventario_apresentacao import BOLSAS, VERSAO_INTERFACE, preparar_equipe, preparar_itens\n\nfoo={\n        bolsas=BOLSAS,\n}\ndef x():\n  return _executar(\n        quantidade=request.form.get("quantidade", 1),\n  )\n''',
        'templates/jogador/inventario.html':'''{% block estilos_finais %}{% endblock %}\n<p class="inventario-nds-item-descricao">none</p>\n                        <p class="inventario-nds-item-descricao">{{ item.descricao or 'Sem descrição cadastrada.' }}</p>\n                                <button type="submit" class="inventario-nds-acao">Usar</button>\n{% endblock %}\n{% block scripts %}{% endblock %}'''
    }
    for name,src in files.items():p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(src,encoding='utf-8')
    changed=m.instalar(tmp_path)
    assert len(changed)==3
    assert m.instalar(tmp_path)==[]
    assert (tmp_path/'app/services/inventario_service.py').with_name('inventario_service.py.bak-10c3').exists()
    assert 'ANKAR_10C3_CURA' in (tmp_path/'app/services/inventario_service.py').read_text(encoding='utf-8')
