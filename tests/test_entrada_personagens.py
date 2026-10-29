from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from jinja2 import Environment, DictLoader

RAIZ = Path(__file__).resolve().parents[1]


def _instalador():
    spec = importlib.util.spec_from_file_location("entrada_instalador_teste", RAIZ / "scripts/instalar_entrada_personagens.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_instalacao_idempotente_e_preserva_codigo(tmp_path):
    (tmp_path / "app/routes").mkdir(parents=True)
    (tmp_path / "templates").mkdir()
    (tmp_path / "docs").mkdir()
    init = tmp_path / "app/__init__.py"
    auth = tmp_path / "app/routes/auth.py"
    base = tmp_path / "templates/base.html"
    init.write_text("    from app.routes.auth import auth_bp\n    app.register_blueprint(auth_bp)\n", encoding="utf-8")
    auth.write_text('    return render_template("login.html")\n', encoding="utf-8")
    base.write_text('<a class="botao botao-secundario botao-link" href="{{ url_for(\'auth.trocar_senha\') }}">Senha</a>', encoding="utf-8")
    (tmp_path / "docs/CONTINUIDADE_PROJETO.md").write_text("Contexto\n", encoding="utf-8")
    (tmp_path / "docs/DIARIO_DESENVOLVIMENTO.md").write_text("Diário\n", encoding="utf-8")
    instalador = _instalador()
    resultado = instalador.instalar(tmp_path)
    assert all(resultado.values())
    depois = [p.read_text(encoding="utf-8") for p in (init, auth, base, tmp_path / "docs/DIARIO_DESENVOLVIMENTO.md")]
    resultado2 = instalador.instalar(tmp_path)
    assert not any(resultado2.values())
    assert depois == [p.read_text(encoding="utf-8") for p in (init, auth, base, tmp_path / "docs/DIARIO_DESENVOLVIMENTO.md")]
    assert (tmp_path / "app/__init__.py.antes_10b1.bak").exists()
    assert "ENTRADA_PERSONAGENS_10B1" in depois[1]
    assert depois[3].count("<!-- ENTRADA_PERSONAGENS_10B1 -->") == 1


def test_template_tem_nove_slots_e_coringa():
    html = (RAIZ / "templates/entrada_personagens.html").read_text(encoding="utf-8")
    css = (RAIZ / "static/css/entrada-personagens.css").read_text(encoding="utf-8")
    assert 'action="{{ url_for(\'entrada_personagens.entrar_com_personagem\', numero=slot.numero) }}"' in html
    assert "<input type=\"hidden\" name=\"csrf_token\"" in html
    assert "url_for('entrada_personagens.coringa')" in html
    assert "--x:" in html and "--y:" in html
    assert ".entrada-coringa" in css and "top:94%" in css
    assert "image-rendering:pixelated" in css


def test_coringa_formulario_tradicional_preservado():
    rota = (RAIZ / "app/routes/entrada_personagens.py").read_text(encoding="utf-8")
    assert '@entrada_personagens_bp.get("/login/coringa")' in rota
    assert 'return render_template("login.html")' in rota
    assert 'Usuario.perfil == "jogador"' in (RAIZ / "app/services/entrada_personagens_service.py").read_text(encoding="utf-8")
