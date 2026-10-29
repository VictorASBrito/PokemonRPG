"""Verificações sem Flask da correção do slot Mestre (Etapa 10B.3.2)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def instalador():
    spec = importlib.util.spec_from_file_location("login10b32", ROOT / "scripts/corrigir_login_mestre_10b3_2.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def preparar(raiz: Path):
    for pasta in ("templates", "app/routes", "docs"):
        (raiz / pasta).mkdir(parents=True, exist_ok=True)
    (raiz / "templates/login.html").write_text(
        '''<form method="post" class="formulario">\n<input name="login">\n<input name="senha" type="password">\n</form>\n''',
        encoding="utf-8")
    (raiz / "app/routes/entrada_personagens.py").write_text(
        '''@entrada_personagens_bp.get("/login/coringa")
def coringa():
    if session.get("usuario_id"):
        return redirect(url_for("inicio"))
    return render_template("login.html")

@entrada_personagens_bp.post("/login/personagem/<int:numero>")
def entrar_com_personagem(numero):
    return redirect('/p/teste/')
''', encoding="utf-8")
    (raiz / "app/routes/auth.py").write_text(
        '''@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("usuario_id"):
        return redirect(url_for("inicio"))
    if request.method == "POST":
        resultado = autenticar_usuario(login, senha, campanha)
        return redirect('/painel')
    return render_template("entrada_personagens.html")

@auth_bp.post("/logout")
def logout():
    return redirect('/login')
''', encoding="utf-8")
    for d in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        (raiz / "docs" / d).write_text("Diário do projeto ágil\n", encoding="utf-8")


def test_instalacao_corrige_405_sem_alterar_as_fichas(tmp_path):
    preparar(tmp_path)
    m = instalador()
    r = m.instalar(tmp_path)
    assert r["templates/login.html"] is True
    html = (tmp_path / "templates/login.html").read_text(encoding="utf-8")
    assert 'action="{{ url_for(\'auth.login\') }}"' in html
    entrada = (tmp_path / "app/routes/entrada_personagens.py").read_text(encoding="utf-8")
    assert 'if session.get("usuario_id"):' not in entrada
    assert 'return render_template("login.html")' in entrada
    assert 'entrar_com_personagem(numero)' in entrada
    auth = (tmp_path / "app/routes/auth.py").read_text(encoding="utf-8")
    assert 'if request.method == "GET" and session.get("usuario_id"):' in auth
    assert "autenticar_usuario(login, senha, campanha)" in auth
    assert (tmp_path / "templates/login.html.antes_10b3_2.bak").exists()


def test_aplicacao_duas_vezes_nao_duplica_documentacao(tmp_path):
    preparar(tmp_path)
    m = instalador()
    m.instalar(tmp_path)
    assert all(not mudou for mudou in m.instalar(tmp_path).values())
    doc = (tmp_path / "docs/DIARIO_DESENVOLVIMENTO.md").read_text(encoding="utf-8")
    assert doc.count("<!-- LOGIN_MESTRE_10B3_2 -->") == 1


def test_erro_de_formulario_customizado_nao_modifica_arquivos(tmp_path):
    preparar(tmp_path)
    login = tmp_path / "templates/login.html"
    login.write_text('<form method="post" action="/meu-login-customizado"></form>', encoding="utf-8")
    auth = tmp_path / "app/routes/auth.py"
    antes = auth.read_bytes()
    with pytest.raises(RuntimeError):
        instalador().instalar(tmp_path)
    assert login.read_text(encoding="utf-8").endswith('</form>')
    assert auth.read_bytes() == antes
    assert not (tmp_path / "docs/DIARIO_DESENVOLVIMENTO.md.antes_10b3_2.bak").exists()


def test_formulario_com_action_anterior_coringa_e_corrigido(tmp_path):
    preparar(tmp_path)
    login = tmp_path / "templates/login.html"
    login.write_text('<form action="/login/coringa" method="post" class="formulario"></form>', encoding="utf-8")
    instalador().instalar(tmp_path)
    assert 'action="{{ url_for(\'auth.login\') }}"' in login.read_text(encoding="utf-8")


def test_formulario_action_correta_e_guard_ja_corrigida(tmp_path):
    preparar(tmp_path)
    login = tmp_path / "templates/login.html"
    login.write_text('<form method="post" action="{{ url_for(\'auth.login\') }}"></form>', encoding="utf-8")
    auth = tmp_path / "app/routes/auth.py"
    auth.write_text(auth.read_text(encoding="utf-8").replace(
        'if session.get("usuario_id"):',
        'if request.method == "GET" and session.get("usuario_id"):'))
    resultado = instalador().instalar(tmp_path)
    assert resultado['templates/login.html'] is False
    assert resultado['app/routes/auth.py'] is False


def test_codificacao_utf8_windows(tmp_path):
    preparar(tmp_path)
    instalador().instalar(tmp_path)
    assert "Diário do projeto ágil" in (tmp_path / "docs/DIARIO_DESENVOLVIMENTO.md").read_text(encoding="utf-8")
