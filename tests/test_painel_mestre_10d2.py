"""Testes isolados 10D.2. Testes integrados Flask são opcionais no CI local."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def modulo():
    spec = importlib.util.spec_from_file_location('instala_10d2', ROOT / 'scripts' / 'instalar_painel_mestre_10d2.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fixture(raiz):
    blocos = {
        'app/routes/mestre.py': '''mestre_bp = Blueprint("mestre", __name__, url_prefix="/mestre")
    return render_template(
        "mestre/dashboard.html",
        campanha=painel.campanha,
@mestre_bp.get("/jogadores")
@perfil_obrigatorio("mestre")
def jogadores():
    return render_template('mestre/jogadores.html')


def _validar_novo_jogador(nome):
    return []
''',
        'app/services/painel_mestre_service.py': '''jogadores.append(
            {
                "login": personagem.usuario.login,
            }
        )
''',
        'templates/mestre/dashboard.html': '''{% extends "base.html" %}
{% block estilos %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/painel-mestre.css') }}">
{% endblock %}
{% block conteudo %}
<section class="painel-mestre-metricas" aria-label="Resumo da campanha">
  <div>Jogadores</div>
</section>
<section class="cartao painel-mestre-filtros ui-card">Busca</section>
<div class="painel-mestre-acoes-topo">
        <a class="botao botao-secundario botao-link" href="{{ url_for('catalogo_admin.dashboard') }}">Catálogo</a>
</div>
<section>
{% for jogador in jogadores %}
            <div class="painel-jogador-links">
                <form method="post" class="formulario-nivel-mestre" action="x">
                  <button>Salvar nível</button>
                </form>
        <a class="botao botao-primario botao-link" href="{{ url_for('boxes.boxes_mestre', jogador_id=jogador.get('id')) }}">Box</a>
    </div>
        </header>

        <div class="painel-jogador-resumo">
          <section>Atributos</section>
        </div>

        {% if jogador.get('alertas') %}Alertas{% endif %}
        {% if jogador.get('foto_url') %}<img class="painel-jogador-avatar" src="x">{% else %}<span>A</span>{% endif %}
        {% if pokemon.get('nome') != pokemon.get('especie') %}<small>{{ pokemon.get('especie') }}</small>{% endif %}
        <form class="controle-pv-rapido controle-pv-pokemon" method="post" action="x" data-pv-form>
           <button type="submit" data-delta="-10">-10</button>
        </form>
{% endfor %}
</section>
{% endblock %}

{% block scripts %}
    JS
{% endblock %}
''',
        'static/js/painel-mestre.js': '''(() => {
    const mostrarMensagem = (texto, erro = false) => {
        mensagem.textContent = texto;
    };

    const atualizarNumerosOrdem = () => {};
    document.querySelectorAll('[data-pv-form]').forEach((form) => {
        form.addEventListener('submit', async (evento) => {
            evento.preventDefault();
            const botao = evento.submitter;
            const delta = botao?.dataset.delta;
            if (!delta) return;
            const botoes = [...form.querySelectorAll('button')];
        });
    });
    atualizarNumerosOrdem();
    aplicarPesquisa();
})();
''',
        'templates/base.html': '''{% if session.get('perfil') == 'mestre' %}
                    <a href="{{ url_for('mestre.jogadores') }}">Jogadores</a>
{% endif %}
''',
    }
    for nome, texto in blocos.items():
        p = raiz / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding='utf-8')


def test_instalacao_previa_e_idempotente(tmp_path):
    fixture(tmp_path)
    m = modulo()
    esperado = list(m.TRANSFORMADORES)
    assert m.instalar(tmp_path, verificar=True) == esperado
    assert not (tmp_path/'relatorios').exists()
    assert m.instalar(tmp_path) == esperado
    assert m.instalar(tmp_path, verificar=True) == []
    assert m.instalar(tmp_path) == []
    for nome in esperado:
        assert m.MARKER in (tmp_path / nome).read_text(encoding='utf-8'), nome


def test_falha_sem_alterar_arquivos_incompletos(tmp_path):
    fixture(tmp_path)
    caminho = tmp_path/'templates/mestre/dashboard.html'
    caminho.write_text('template novo, incompatível', encoding='utf-8')
    antes = (tmp_path/'app/routes/mestre.py').read_text(encoding='utf-8')
    m = modulo()
    with pytest.raises(m.InstalacaoIncompativel):
        m.instalar(tmp_path)
    assert (tmp_path/'app/routes/mestre.py').read_text(encoding='utf-8') == antes


def test_template_compilavel(tmp_path):
    from jinja2 import Environment
    fixture(tmp_path)
    modulo().instalar(tmp_path)
    texto = (tmp_path / 'templates/mestre/dashboard.html').read_text(encoding='utf-8')
    Environment().parse(texto)
    assert 'data-cura-10d2' in texto
    assert 'painel-mestre-metricas' not in texto
    assert 'data-operacao="menos"' in texto
    assert "painel-pokemon-especie" in texto


def test_js_valido(tmp_path):
    fixture(tmp_path)
    modulo().instalar(tmp_path)
    if shutil.which('node') is None:
        pytest.skip('node ausente')
    javascript = tmp_path / 'static/js/painel-mestre.js'
    r = subprocess.run(['node','--check',str(javascript)],capture_output=True,text=True)
    assert r.returncode == 0, r.stderr


def test_servico_sintaxe_e_registro_historico():
    origem = (ROOT / 'app/services/cura_mestre_10d2.py').read_text(encoding='utf-8')
    compile(origem, 'cura_mestre_10d2.py', 'exec')
    for texto in ('carregar_contexto_pokemon', 'with_for_update()', 'db.session.delete(relacao)',
                  'HistoricoAlteracao', 'db.session.commit()', 'Pokemon.ativo.is_(True)'):
        assert texto in origem


def test_css_regras_basicas():
    css = (ROOT/'static/css/painel-mestre-10d2.css').read_text(encoding='utf-8')
    assert '@media (max-width: 640px)' in css
    assert '.painel-mestre-central' in css
    assert 'grid-template-columns: repeat(6' in css
    assert 'painel-pokemon-info > small' in css
    try:
        import tinycss2
    except ImportError:
        return
    regras = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
    assert not [e for e in regras if e.type == 'error']
