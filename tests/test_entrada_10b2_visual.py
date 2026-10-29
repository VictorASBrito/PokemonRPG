from __future__ import annotations

import importlib.util
from pathlib import Path

from jinja2 import DictLoader, Environment

RAIZ = Path(__file__).resolve().parents[1]


def _texto(caminho: str) -> str:
    return (RAIZ / caminho).read_text(encoding="utf-8")


def test_copy_e_slot_mestre_preservam_rota_original():
    html = _texto("templates/entrada_personagens.html")
    assert "Escolha seu personagem para abrir a ficha.</p>" in html
    assert "use o slot coringa" not in html
    assert 'class="entrada-rodape' not in html
    assert '<small>Outras contas</small>' not in html
    assert '<span class="entrada-nome">Mestre</span>' in html
    assert "filename='img/pokebola.png'" in html
    assert "url_for('entrada_personagens.coringa')" in html
    assert 'name="csrf_token"' in html
    assert "url_for('entrada_personagens.entrar_com_personagem', numero=slot.numero)" in html
    assert "★" not in html
    assert "v='10b2'" in html


def test_circulos_e_sprites_tamanho_uniforme():
    css = _texto("static/css/entrada-personagens.css")
    assert ".entrada-sprite { width:var(--slot); height:var(--slot);" in css
    assert ".entrada-coringa-icone { width:var(--slot); height:var(--slot);" in css
    assert "object-fit:contain" in css
    assert "image-rendering:pixelated" in css
    assert "max-height:78%" in css
    assert "--slot:clamp(64px,6.6vw,94px)" in css
    assert "--slot:clamp(52px,14vw,62px)" in css
    assert "width:auto; height:78%" in css
    assert "top:94%" in css
    assert "@media(max-width:640px)" in css


def test_template_jinja_renderiza_nove_jogadores_mais_mestre():
    template = _texto("templates/entrada_personagens.html")
    ambiente = Environment(loader=DictLoader({"base.html": "{% block conteudo %}{% endblock %}",
                                                    "entrada_personagens.html": template}), autoescape=True)
    ambiente.globals["url_for"] = lambda endpoint, **kw: f"/{endpoint}/{kw.get('numero','')}"
    slots = [{"numero": i, "x": 50, "y": 50, "nome": f"Personagem {i}",
              "imagem": f"/sprite-{i}.png", "disponivel": True} for i in range(1, 10)]
    html = ambiente.get_template("entrada_personagens.html").render(slots=slots, entrada_csrf="abc")
    assert html.count('class="entrada-posicao"') == 9
    assert html.count('class="entrada-personagem"') == 9
    assert html.count('name="csrf_token"') == 9
    assert 'class="entrada-coringa"' in html
    assert 'Mestre</span>' in html
    assert 'Coringa</span>' not in html


def test_registro_documentacao_idempotente(tmp_path):
    (tmp_path / "docs").mkdir()
    for nome in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        (tmp_path / "docs" / nome).write_text("Histórico original\n", encoding="utf-8")
    src = RAIZ / "scripts/registrar_entrada_10b2.py"
    spec = importlib.util.spec_from_file_location("doc10b2", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod.registrar(tmp_path)) == 2
    assert len(mod.registrar(tmp_path)) == 0
    for nome in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        txt = (tmp_path / "docs" / nome).read_text(encoding="utf-8")
        assert txt.count(mod.MARCADOR) == 1
        assert txt.startswith("Histórico original")
