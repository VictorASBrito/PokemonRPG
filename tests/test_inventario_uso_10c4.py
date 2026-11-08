"""Regressão leve da interação de mochila (Etapa 10C.4).

Rodar APÓS: python scripts/instalar_inventario_10c4.py
Sem PostgreSQL; não altera inventários.
"""
from __future__ import annotations

from pathlib import Path
import importlib.util
import shutil
import subprocess

from jinja2 import Environment
import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _instalador():
    arquivo = RAIZ / 'scripts/instalar_inventario_10c4.py'
    spec = importlib.util.spec_from_file_location('instalador_10c4', arquivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_template_e_fluxo_sem_formulario_de_uso_no_painel_direito():
    html = (RAIZ / 'templates/jogador/inventario.html').read_text(encoding='utf-8')
    assert 'ANKAR_10C4_USO_LINHA' in html, 'Execute antes o instalador 10C.4.'
    Environment().parse(html)
    assert html.count('data-ativar-uso=') == 1  # único bloco repetido por item
    assert 'data-uso-efeitos=' in html
    assert 'data-pokemon-alvo=' in html
    assert 'data-formulario-uso' in html
    assert 'data-uso-aviso' in html
    assert 'data-uso-cancelar' in html
    assert 'data-equipar-item=' in html
    assert 'data-equipar-cancelar' in html
    assert 'inventario-equipar-10c4' in html
    assert 'inventario-mapa-estatico' in html
    assert 'Efeitos cadastrados' not in html
    assert 'Registrar uso' not in html
    assert 'Ver mapa da Região de Ankar</button>' not in html
    assert 'Gerenciamento do mestre · Ajustar quantidade' in html
    assert 'inventario-uso-10c4.js' in html


def test_carrega_status_dos_pokemon_da_equipe():
    src = (RAIZ/'app/services/inventario_service.py').read_text(encoding='utf-8')
    assert 'selectinload(Pokemon.status_ativos)' in src


def test_instalador_idempotente():
    assert _instalador().preparar(RAIZ) == {
        RAIZ/'templates/jogador/inventario.html':(RAIZ/'templates/jogador/inventario.html').read_text(encoding='utf-8'),
        RAIZ/'app/services/inventario_service.py':(RAIZ/'app/services/inventario_service.py').read_text(encoding='utf-8'),
    }


def test_regras_elegibilidade_js():
    if not shutil.which('node'):
        pytest.skip('Node não instalado; verificação sintática JS opcional.')
    fonte = RAIZ/'static/js/inventario-uso-10c4.js'
    script = r'''
      const assert=require('node:assert/strict');
      const {elegivel}=require(process.argv[1]);
      const mk=(atual,maximo,s=[])=>({atual,maximo,status:new Set(s)});
      assert.equal(elegivel([{tipo:'recuperar_pv',alvo:'pokemon'}],mk(10,100)),true);
      assert.equal(elegivel([{tipo:'recuperar_pv',alvo:'pokemon'}],mk(100,100)),false);
      assert.equal(elegivel([{tipo:'recuperar_pv',alvo:'pokemon'}],mk(1,NaN)),false);
      assert.equal(elegivel([{tipo:'remover_status',alvo:'pokemon',status_id:'paralisado'}],mk(100,100,['paralisado'])),true);
      assert.equal(elegivel([{tipo:'remover_status',alvo:'pokemon',status_id:'paralisado'}],mk(100,100,['congelado'])),false);
      assert.equal(elegivel([{tipo:'remover_status',alvo:'pokemon',todos:true}],mk(100,100,['congelado'])),true);
      assert.equal(elegivel([{tipo:'remover_status',alvo:'pokemon',todos:true}],mk(100,100,[])),false);
      assert.equal(elegivel([{tipo:'recuperar_pv',alvo:'personagem'}],mk(10,100)),false);
    '''
    p=subprocess.run(['node','-e',script,str(fonte)],capture_output=True,text=True)
    assert p.returncode == 0,p.stderr


def test_scripts_compilam():
    import ast
    ast.parse((RAIZ/'scripts/instalar_inventario_10c4.py').read_text(encoding='utf-8'))
