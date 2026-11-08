"""Testes independentes do Flask para o patch 10C.4.2."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/instalar_aviso_selecao_10c4_2.py"


def modulo():
    spec = importlib.util.spec_from_file_location("patch_10c4_2", SCRIPT)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def criar_base(tmp_path):
    # Conteúdo anterior à instalação, com âncoras reais das Etapas 10C.4/10C.4.1.
    bases = {
        "static/js/inventario-uso-10c4.js": ROOT / "tests/fixtures_10c4_2/inventario-uso-10c4.js",
        "static/js/avisos-toast-10c4-1.js": ROOT / "tests/fixtures_10c4_2/avisos-toast-10c4-1.js",
        "static/css/inventario-uso-10c4.css": ROOT / "tests/fixtures_10c4_2/inventario-uso-10c4.css",
    }
    # Fontes de teste do estado anterior, incluídas com este pacote.
    for path, source in bases.items():
        if not source.exists():
            pytest.skip("Fontes-base locais da preparação não disponíveis")
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    template = '''{# ANKAR_10C4_USO_LINHA #}
<link rel="stylesheet" href="{{ url_for('static', filename='css/inventario-uso-10c4.css', v='10c4') }}">
            <div class="inventario-nds-logo-copy">
                <strong>BAG</strong>
                <small>{{ personagem.nome }}</small>
            </div>
        </div>
        <div class="inventario-uso-aviso" data-uso-aviso role="status" aria-live="polite" hidden>
            <span data-uso-mensagem></span>
            <button type="button" data-uso-cancelar>Cancelar</button>
        </div>
<script src="{{ url_for('static', filename='js/inventario-uso-10c4.js', v='10c4') }}" defer></script>'''
    path = tmp_path / "templates/jogador/inventario.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template, encoding="utf-8")
    path = tmp_path / "templates/base.html"
    path.write_text('''{# AVISOS_TOAST_10C4_1 #}
<script src="{{ url_for('static', filename='js/avisos-toast-10c4-1.js', v='10c4-1') }}" defer></script>''', encoding="utf-8")


def test_instala_preservando_cancelamento_e_sem_banner(tmp_path):
    criar_base(tmp_path)
    m = modulo()
    mudancas = m.instalar(tmp_path)
    assert len(mudancas) == 5
    template = (tmp_path / "templates/jogador/inventario.html").read_text(encoding="utf-8")
    assert 'data-uso-cancelar' in template
    assert 'data-uso-aviso hidden' in template
    assert 'data-uso-mensagem' not in template
    assert 'role="status" aria-live="polite"' not in template
    assert '10c4-2' in template
    assert m.instalar(tmp_path) == []
    assert len(list(tmp_path.rglob('*.bak-10c4-2'))) == 5


def test_toast_dinamico_tem_1500ms_e_texto_seguro(tmp_path):
    criar_base(tmp_path)
    modulo().instalar(tmp_path)
    source = (tmp_path / "static/js/avisos-toast-10c4-1.js").read_text(encoding="utf-8")
    assert "aviso.dataset.tempoMs = '1500'" in source
    assert "mensagem.textContent = String(texto)" in source
    assert "iniciarAviso(aviso)" in source
    assert "window.PokemonRPGToast = Object.freeze" in source
    assert "fecharDinamico()" in source
    assert "avisos.forEach(iniciarAviso)" in source


def test_mochila_nao_deixa_aviso_fixo_e_mantem_selecao(tmp_path):
    criar_base(tmp_path)
    modulo().instalar(tmp_path)
    fonte = (tmp_path / "static/js/inventario-uso-10c4.js").read_text(encoding="utf-8")
    assert "PokemonRPGToast?.mostrar" in fonte
    assert "PokemonRPGToast?.fecharDinamico" in fonte
    assert "if (msgWrap) msgWrap.hidden = false; // apenas Cancelar" in fonte
    assert "Nenhum Pokémon da equipe pode receber o efeito agora.', 'aviso'" in fonte
    assert "card.classList.toggle('inventario-uso-elegivel', pode)" in fonte
    assert "data-uso-cancelar" in fonte


def test_javascript_valido(tmp_path):
    criar_base(tmp_path)
    modulo().instalar(tmp_path)
    if not shutil.which("node"):
        pytest.skip("Node não instalado")
    for name in ("inventario-uso-10c4.js", "avisos-toast-10c4-1.js"):
        f = tmp_path / "static/js" / name
        p = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr


def test_preflight_bloqueia_dependencias_ausentes(tmp_path):
    criar_base(tmp_path)
    (tmp_path / 'templates/base.html').write_text('sem toasts globais', encoding='utf-8')
    with pytest.raises(RuntimeError, match='10C.4.1'):
        modulo().instalar(tmp_path)
    assert not list(tmp_path.rglob('*.bak-10c4-2'))
