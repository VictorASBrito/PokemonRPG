"""Teste puro: middleware e instalador, sem dependências Flask/SQLAlchemy."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _arquivo(nome: str, caminho: Path):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_url_ficha_reescreve_caminho_e_preserva_script_root():
    mod = _arquivo("url_middleware", ROOT / "app/services/fichas_url_middleware.py")
    recebido = {}

    def app(env, start):
        recebido.update(env)
        start("200 OK", [])
        return [b"ok"]

    middleware = mod.FichasURLMiddleware(app)
    assert b"".join(middleware({"SCRIPT_NAME": "/pokemon", "PATH_INFO": "/p/mari/jogador/ficha"}, lambda *_: None)) == b"ok"
    assert recebido["ANKAR_FICHA_LOGIN"] == "mari"
    assert recebido["ANKAR_SCRIPT_ROOT_ORIGINAL"] == "/pokemon"
    assert recebido["SCRIPT_NAME"] == "/pokemon/p/mari"
    assert recebido["PATH_INFO"] == "/jogador/ficha"


def test_url_ficha_raiz_e_rotas_externas():
    mod = _arquivo("url_middleware2", ROOT / "app/services/fichas_url_middleware.py")
    visto = []

    def app(env, start):
        visto.append(dict(env))
        return [b"ok"]

    middleware = mod.FichasURLMiddleware(app)
    middleware({"PATH_INFO": "/p/jao"}, lambda *_: None)
    middleware({"PATH_INFO": "/mestre/dashboard"}, lambda *_: None)
    assert visto[0]["PATH_INFO"] == "/"
    assert visto[0]["SCRIPT_NAME"] == "/p/jao"
    assert visto[1]["PATH_INFO"] == "/mestre/dashboard"
    assert "ANKAR_FICHA_LOGIN" not in visto[1]


def test_login_invalido_nao_entra_no_middleware():
    mod = _arquivo("url_middleware3", ROOT / "app/services/fichas_url_middleware.py")
    visto = {}

    def app(env, start):
        visto.update(env)
        return []

    mod.FichasURLMiddleware(app)({"PATH_INFO": "/p/../mestre/dashboard"}, lambda *_: None)
    assert "ANKAR_FICHA_LOGIN" not in visto


def _preparar(tmp: Path):
    for pasta in ("app/routes", "templates", "docs", "scripts"):
        (tmp / pasta).mkdir(parents=True, exist_ok=True)
    (tmp / "app/__init__.py").write_text(
        '    Config(raiz).aplicar(app)\n'
        '    from app.routes.entrada_personagens import entrada_personagens_bp\n'
        '    app.register_blueprint(entrada_personagens_bp)\n', encoding="utf-8"
    )
    original = (ROOT.parent / "ankar_login_patch" / "app/routes/entrada_personagens.py")
    # Pacote antigo disponível no ambiente de criação; alternativa de fixture fixa.
    if original.exists():
        texto = original.read_text(encoding="utf-8")
    else:
        texto = '''@entrada_personagens_bp.post("/login/personagem/<int:numero>")
def entrar_com_personagem(numero):
    if session.get("usuario_id"):
        return redirect(url_for("inicio"))

    esperado = "x"
    autenticado = True
    usuario, personagem, campanha = autenticado
    # Repete os mesmos campos da sessão existente, sem promover privilégios.
    session.clear()
    session["usuario_id"] = str(usuario.id)
    session["nome"] = usuario.nome
    session["perfil"] = "jogador"
    session["perfil_conta"] = "jogador"
    session["campanha_id"] = str(campanha.id)
    session["personagem_id"] = str(personagem.id)
    session["entrada_visual"] = True
    # Não ignora autorização de perfil em app.routes.auth.perfil_obrigatorio.
    return redirect(url_for("jogadores.dashboard")), 303'''
    (tmp / "app/routes/entrada_personagens.py").write_text(texto, encoding="utf-8")
    (tmp / "app/routes/auth.py").write_text('''def logout():
    session.clear()
    flash("Sessão encerrada.", "sucesso")
    return redirect(url_for("auth.login"))
''', encoding="utf-8")
    (tmp / "templates/base.html").write_text('<div class="usuario-topo">\n                    <form action="{{ url_for(\'auth.logout\') }}" method="post">\n                        <button class="botao botao-secundario" type="submit">Sair</button>\n                    </form>\n', encoding="utf-8")
    for x in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        (tmp / "docs" / x).write_text("HISTÓRICO\n", encoding="utf-8")


def test_instalador_idempotente_e_preserva_conteudo(tmp_path):
    _preparar(tmp_path)
    mod = _arquivo("instalar_10b3", ROOT / "scripts/instalar_fichas_por_url.py")
    resultado = mod.instalar(tmp_path)
    assert resultado["app/__init__.py"]
    caminhos = [tmp_path / "app/__init__.py", tmp_path / "app/routes/auth.py", tmp_path / "app/routes/entrada_personagens.py", tmp_path / "templates/base.html"]
    depois = [p.read_text(encoding="utf-8") for p in caminhos]
    assert "HISTÓRICO" in (tmp_path / "docs/DIARIO_DESENVOLVIMENTO.md").read_text(encoding="utf-8")
    outra = mod.instalar(tmp_path)
    assert not any(outra.values())
    assert depois == [p.read_text(encoding="utf-8") for p in caminhos]
    assert (tmp_path / "app/__init__.py.antes_10b3.bak").is_file()
    assert not (tmp_path / "app/routes/auth.py.antes_10b3.bak").exists()
    assert (tmp_path / "app/routes/auth.py").read_text(encoding="utf-8").startswith("def logout")


def test_instalador_rejeita_versao_inesperada_sem_modificar(tmp_path):
    _preparar(tmp_path)
    (tmp_path / "app/routes/entrada_personagens.py").write_text("def login(): pass\n", encoding="utf-8")
    mod = _arquivo("instalar_10b3b", ROOT / "scripts/instalar_fichas_por_url.py")
    antigo = (tmp_path / "app/__init__.py").read_text(encoding="utf-8")
    with pytest.raises(RuntimeError):
        mod.instalar(tmp_path)
    assert (tmp_path / "app/__init__.py").read_text(encoding="utf-8") == antigo


def test_listar_urls_dos_slots_sem_acessar_banco(tmp_path):
    import json
    mod = _arquivo("links_10b3", ROOT / "scripts/listar_links_fichas.py")
    config = tmp_path / "entrada_personagens.json"
    config.write_text(json.dumps({"habilitado": True, "slots": [
        {"login": f"usuario{i}"} for i in range(1, 10)
    ]}), encoding="utf-8")
    links = mod.gerar_links(config, "https://meu-servidor")
    assert len(links) == 9
    assert links[0] == "1. @usuario1: https://meu-servidor/p/usuario1/"


def test_instalador_aceita_auth_localmente_modificado(tmp_path):
    _preparar(tmp_path)
    auth = tmp_path / "app/routes/auth.py"
    customizado = "# Minha personalização do logout\n\ndef logout():\n    session.clear()\n    return redirect('/selecionar')\n"
    auth.write_text(customizado, encoding="utf-8")
    mod = _arquivo("instalar_custom_auth", ROOT / "scripts/instalar_fichas_por_url.py")
    resultado = mod.instalar(tmp_path)
    assert resultado["app/__init__.py"]
    assert auth.read_text(encoding="utf-8") == customizado
    assert mod.instalar(tmp_path)["app/__init__.py"] is False


def test_instalador_preserva_auth_se_o_logout_tiver_diferencas_de_espacamento(tmp_path):
    _preparar(tmp_path)
    auth = tmp_path / "app/routes/auth.py"
    auth.write_text("@auth_bp.post('/logout')\ndef logout(): return ('ok', 200)\n", encoding="utf-8")
    mod = _arquivo("instalar_custom_auth2", ROOT / "scripts/instalar_fichas_por_url.py")
    mod.instalar(tmp_path)
    assert auth.read_text(encoding="utf-8") == "@auth_bp.post('/logout')\ndef logout(): return ('ok', 200)\n"

