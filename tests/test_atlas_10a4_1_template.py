"""Compatibilidade do Atlas 10A.4 com renderização isolada e com contexto Flask.

Não usa banco de dados, nem exige executar o servidor. Regressão do
UndefinedError: 'formas' is undefined visto no Windows.
"""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

RAIZ = Path(__file__).resolve().parents[1]


def _renderizar(local: dict, **extras) -> str:
    env = Environment(loader=ChoiceLoader([
        DictLoader({"base.html": "{% block estilos_finais %}{% endblock %}{% block conteudo %}{% endblock %}{% block scripts %}{% endblock %}"}),
        FileSystemLoader(str(RAIZ / "templates")),
    ]))

    def url_for(endpoint: str, **kwargs) -> str:
        if endpoint == "static":
            return "/static/" + kwargs["filename"]
        if endpoint == "regiao.indice_ankar":
            return "/regiao/ankar" + ("?local=" + kwargs["local"] if "local" in kwargs else "")
        if endpoint == "regiao.detalhe_ankar":
            return "/regiao/ankar/" + kwargs["slug"]
        if endpoint == "regiao.gerar_encontro_atlas":
            return "/regiao/ankar/" + kwargs["slug"] + "/gerar-encontro"
        raise AssertionError(f"Endpoint inesperado: {endpoint}")

    env.globals["url_for"] = url_for
    return env.get_template("regiao/detalhe.html").render(local=local, **extras)


def _rota1() -> dict:
    dados = json.loads((RAIZ / "app/data/catalogo_ankar_visual.json").read_text(encoding="utf-8"))
    return next(local for local in dados["locais"] if local["id"] == "rota-1")


def test_ficha_sem_contexto_opcional_nao_gera_erro():
    html = _renderizar(_rota1(), ponto_mapa={"numero": "1"})
    assert "Tentacool" in html
    assert "60-75" in html  # Mantém a sobreposição original do d100.
    assert "Ver localização no mapa" in html
    assert "ankar-gerar-dialog" not in html  # Não cria sem jogadores informados.


def test_ficha_com_contexto_completo_mantem_acao_de_gerar():
    html = _renderizar(
        _rota1(),
        formas={"tentacool": {"id": "forma-1", "imagem": "/static/img/teste.png"}},
        encontrados_por=[{"id": "jogador-1", "nome": "Treinador de Teste"}],
        descricao_paragrafos=["Descrição de teste. Mais informações aqui."],
        atlas_csrf="token-teste",
    )
    assert 'data-ankar-gerar' in html
    assert "/static/img/teste.png" in html
    assert 'action="/regiao/ankar/rota-1/gerar-encontro"' in html
    assert 'name="csrf_token" value="token-teste"' in html
    assert 'Treinador de Teste' in html
    assert "Descrição de teste" in html


def test_documentacao_acrescentada_uma_vez(tmp_path):
    from importlib.util import module_from_spec, spec_from_file_location

    caminho = RAIZ / "scripts/registrar_correcao_atlas_10a4_1.py"
    spec = spec_from_file_location("registrar_atlas_10a4_1_teste", caminho)
    assert spec and spec.loader
    modulo = module_from_spec(spec)
    spec.loader.exec_module(modulo)

    (tmp_path / "docs").mkdir()
    for nome in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        (tmp_path / "docs" / nome).write_text("Histórico original.\n", encoding="utf-8")
    assert len(modulo.registrar(tmp_path)) == 2
    assert modulo.registrar(tmp_path) == []
    for nome in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        conteudo = (tmp_path / "docs" / nome).read_text(encoding="utf-8")
        assert conteudo.startswith("Histórico original.\n")
        assert conteudo.count(modulo.MARCA) == 1
