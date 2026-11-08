"""Testes sem Flask: instalacao global dos avisos e renderizacao segura de Jinja."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, select_autoescape

from scripts.instalar_avisos_toast_10c4_1 import (
    ANTIGO_FLASH, CSS_ANTIGO, JS_ANTIGO, MARCADOR, NOVO_FLASH,
    instalar, preparar,
)

ROOT = Path(__file__).resolve().parents[1]


def preparar_raiz(tmp_path: Path) -> Path:
    (tmp_path / "templates").mkdir()
    for recurso in ("static/css/avisos-toast-10c4-1.css", "static/js/avisos-toast-10c4-1.js"):
        caminho = tmp_path / recurso
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes((ROOT / recurso).read_bytes())
    template = "\n".join((
        "<html>", "<head>", CSS_ANTIGO, "</head>", "<body>",
        ANTIGO_FLASH, JS_ANTIGO, "</body>", "</html>",
    ))
    (tmp_path / "templates/base.html").write_text(template, encoding="utf-8")
    return tmp_path


def test_instala_toast_global_e_eh_idempotente(tmp_path):
    raiz = preparar_raiz(tmp_path)
    arquivo = raiz / "templates/base.html"
    original = arquivo.read_text(encoding="utf-8")
    assert instalar(raiz) is True
    texto = arquivo.read_text(encoding="utf-8")
    assert texto.count("get_flashed_messages(with_categories=true)") == 1
    assert MARCADOR in texto
    assert 'data-tempo-ms="1500"' in texto
    assert 'class="alerta alerta-{{ categoria }}"' not in texto
    assert "avisos-toast-10c4-1.css" in texto
    assert "avisos-toast-10c4-1.js" in texto
    assert texto.index('id="conteudo-principal"') < texto.index('data-avisos-toast')
    assert (raiz / "templates/base.html.bak-10c4-1").read_text(encoding="utf-8") == original
    assert instalar(raiz) is False
    assert arquivo.read_text(encoding="utf-8") == texto


def test_ancora_alterada_impede_qualquer_escrita(tmp_path):
    raiz = preparar_raiz(tmp_path)
    arquivo = raiz / "templates/base.html"
    arquivo.write_text(arquivo.read_text(encoding="utf-8").replace("role=\"alert\"", "role=\"status\""), encoding="utf-8")
    original = arquivo.read_text(encoding="utf-8")
    with pytest.raises(RuntimeError, match="ancora ausente"):
        instalar(raiz)
    assert arquivo.read_text(encoding="utf-8") == original
    assert not (raiz / "templates/base.html.bak-10c4-1").exists()


def test_falha_sem_recurso_nao_modifica_o_template(tmp_path):
    raiz = preparar_raiz(tmp_path)
    (raiz / "static/js/avisos-toast-10c4-1.js").unlink()
    texto = (raiz / "templates/base.html").read_text(encoding="utf-8")
    with pytest.raises(RuntimeError, match="Arquivo do pacote"):
        instalar(raiz)
    assert (raiz / "templates/base.html").read_text(encoding="utf-8") == texto


def test_renderiza_categorias_e_escapa_conteudo():
    env = Environment(autoescape=select_autoescape(default=True))
    template = env.from_string(NOVO_FLASH)
    mensagens = [
        ("sucesso", "Ficha salva com sucesso no PostgreSQL."),
        ("erro", '<script>alert("XSS")</script>'),
        ("aviso", "Dados verificados."),
        ("categoria-nova", "Informacao adicional."),
    ]
    html = template.render(get_flashed_messages=lambda **_: mensagens)
    assert html.count('data-tempo-ms="1500"') == 4
    assert 'aviso-toast--sucesso' in html
    assert 'aviso-toast--erro' in html
    assert 'aviso-toast--aviso' in html
    assert 'aviso-toast--info' in html
    assert 'role="alert"' in html
    assert '&lt;script&gt;' in html
    assert '<script>alert(' not in html
    assert 'Ficha salva com sucesso no PostgreSQL.' in html


def test_javascript_tem_sintaxe_valida_e_documentacao_registra_sem_duplicar(tmp_path):
    js = ROOT / "static/js/avisos-toast-10c4-1.js"
    if shutil.which("node"):
        subprocess.run(["node", "--check", str(js)], check=True, capture_output=True, text=True)
    from scripts.registrar_documentacao_avisos_10c4_1 import MARCADOR as DOC_MARCADOR, registrar
    docs = tmp_path / "docs"
    docs.mkdir()
    arquivo = docs / "ETAPA_10C4_INVENTARIO_USO_VISUAL.md"
    arquivo.write_text("# Documento de interface\n", encoding="utf-8")
    assert registrar(tmp_path) == ["docs/ETAPA_10C4_INVENTARIO_USO_VISUAL.md"]
    assert registrar(tmp_path) == []
    assert arquivo.read_text(encoding="utf-8").count(DOC_MARCADOR) == 1
