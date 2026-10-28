"""Etapa 10A.6: vínculos explícitos e busca sem alterar o catálogo original."""
from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import json

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

RAIZ = Path(__file__).resolve().parents[1]


def _modulo():
    spec = spec_from_file_location('ankar_formas_isoladas', RAIZ / 'app/services/ankar_formas_service.py')
    mod = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _catalogo():
    return json.loads((RAIZ / 'app/data/catalogo_ankar_visual.json').read_text(encoding='utf-8'))


def test_33_pendencias_com_correspondencias_explicitas():
    mod = _modulo()
    aliases = mod.carregar_aliases()['aliases']
    nomes = {e['pokemon'] for l in _catalogo()['locais'] for z in l['zonas']
             for t in z['tabelas'] for e in t['encontros']}
    assert len(aliases) == 33
    assert set(aliases).issubset(nomes)
    assert sum(map(len, aliases.values())) == 44
    assert aliases['Grimer-A'][0]['codigo'] == 'grimer-alola'
    assert aliases['Oricorio (G)'][0]['codigo'] == 'oricorio-sensu'
    assert aliases['Shellos (A)'][0]['codigo'] == aliases['Shellos (R)'][0]['codigo'] == 'shellos'


def test_variantes_ambiguas_exigem_escolha_sem_aleatoriedade():
    mod = _modulo()
    aliases = mod.carregar_aliases()['aliases']
    multi = {nome for nome, opcoes in aliases.items() if len(opcoes) > 1}
    assert multi == {'Basculin', 'Burmy', 'Eiscue', 'Indeedee', 'Minior', 'Morpeko', 'Pumpkaboo', 'Wishiwashi'}
    formas = [SimpleNamespace(id=f'id-{item["codigo"]}', codigo=item['codigo'], nome=item['nome'],
                             ativo=True, imagem_url=f'/sprites/{item["codigo"]}.png', imagem_shiny_url=None)
              for opcoes in aliases.values() for item in opcoes]
    for nome in aliases:
        opcoes = mod.opcoes_formas(nome, formas)
        assert len(opcoes) == len(aliases[nome]), nome
        assert [opcao['codigo'] for opcao in opcoes] == [i['codigo'] for i in aliases[nome]]


def test_regional_nao_cai_na_especie_base_quando_falta_forma():
    mod = _modulo()
    grimer = SimpleNamespace(id='1', codigo='grimer', nome='Grimer', imagem_url='', imagem_shiny_url='', ativo=True)
    assert mod.opcoes_formas('Grimer-A', [grimer]) == []
    assert mod.opcoes_formas('Grimer', [grimer])[0]['nome'] == 'Grimer'


def test_forma_com_acento_mantem_chave_utilizada_pelo_template():
    mod = _modulo()
    flabebe = SimpleNamespace(id='a', codigo='flabebe', nome='Flabébé', imagem_url='x', imagem_shiny_url='', ativo=True)
    info = mod.indices_formas_locais(['Flabébé'], [flabebe])
    assert info['flabébé']['id'] == 'a'


def test_atalhos_de_busca_contem_forma_do_catalogo():
    mod = _modulo()
    assert 'Corsola (Galar)' in mod.apelidos_pesquisa('Corsola-G')
    assert 'Oricorio (Pom-Pom)' in mod.apelidos_pesquisa('Oricorio (E)')
    assert mod.apelidos_pesquisa('Rattata') == []


def test_template_permite_busca_de_pokemon_e_exibe_formas():
    # Renderiza diretamente sem Flask para preservar os testes antigos.
    catalogo = _catalogo()
    mapa = json.loads((RAIZ / 'app/data/mapa_ankar_pontos.json').read_text(encoding='utf-8'))
    env = Environment(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block estilos_finais %}{% endblock %}{% block conteudo %}{% endblock %}{% block scripts %}{% endblock %}'}),
        FileSystemLoader(RAIZ / 'templates'),
    ]))
    env.globals['url_for'] = lambda endpoint, **kw: '/static/' + kw['filename'] if endpoint == 'static' else '/regiao/ankar/' + kw.get('slug', '')
    index = env.get_template('regiao/indice.html').render(catalogo=catalogo, mapa=mapa)
    assert 'data-pokemon-indice=' in index and 'data-pokemon-resultado' in index
    assert 'Ex.: Grimer' in index
    rota = next(l for l in catalogo['locais'] if l['id'] == 'rota-4')
    vinculos = {'corsola-g': {'id':'1','imagem':'/static/corsola.png','nome':'Corsola (Galar)',
                             'quantidade':1,'observacao':'', 'opcoes':[{'id':'1','codigo':'corsola-galar','nome':'Corsola (Galar)','imagem':'/static/corsola.png'}]}}
    html = env.get_template('regiao/detalhe.html').render(local=rota, formas=vinculos, encontrados_por=[{'id':'x','nome':'Mestre'}])
    assert 'data-formas=' in html and 'corsola-galar' in html
    assert 'id="ankar-forma-id"' in html and 'id="ankar-forma-seletor"' in html


def test_css_e_js_continuam_isolados_e_preservam_mapa():
    js = (RAIZ/'static/js/atlas-ankar.js').read_text(encoding='utf-8')
    css = (RAIZ/'static/css/atlas-ankar.css').read_text(encoding='utf-8')
    assert 'data-pokemon-resultado' in js and 'idForma.value' in js
    assert "mostrarCategoria('todos')" in js
    assert 'data-mapa-zoom' not in js
    assert '.ankar-local-pokemon-match' in css


def test_documentacao_idempotente_e_utf8(tmp_path):
    spec = spec_from_file_location('documentacao_10a6', RAIZ / 'scripts/registrar_atlas_10a6.py')
    mod = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    pasta = tmp_path/'docs'
    pasta.mkdir()
    for nome in ('CONTINUIDADE_PROJETO.md', 'DIARIO_DESENVOLVIMENTO.md'):
        (pasta/nome).write_text('Histórico: Pokémon e Ankar.\n', encoding='utf-8')
    assert len(mod.registrar(tmp_path)) == 2
    assert mod.registrar(tmp_path) == []
    for nome in ('CONTINUIDADE_PROJETO.md', 'DIARIO_DESENVOLVIMENTO.md'):
        texto = (pasta/nome).read_text(encoding='utf-8')
        assert texto.startswith('Histórico: Pokémon e Ankar.')
        assert texto.count(mod.MARCA) == 1
