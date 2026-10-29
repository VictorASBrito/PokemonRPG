"""Etapa 10B.3: múltiplas fichas por URL no mesmo navegador.

Uso: python scripts/instalar_fichas_por_url.py
Não altera banco, senha, sprites, dados de slots nem templates de jogadores.
"""
from __future__ import annotations

import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA = "FICHAS_POR_URL_10B3"


def _salvar(caminho: Path, antes: str, depois: str) -> bool:
    if antes == depois:
        return False
    copia = caminho.with_name(caminho.name + ".antes_10b3.bak")
    if not copia.exists():
        shutil.copy2(caminho, copia)
    caminho.write_text(depois, encoding="utf-8", newline="\n")
    return True


def _trocar_exatamente(texto: str, antes: str, depois: str, *, arquivo: str) -> str:
    if antes not in texto:
        raise RuntimeError(f"Âncora não encontrada em {arquivo}. Projeto diferente do esperado; nenhuma gravação foi feita.")
    return texto.replace(antes, depois, 1)


def instalar(raiz: Path = RAIZ) -> dict[str, bool]:
    raiz = Path(raiz)
    caminhos = {
        "app": raiz / "app" / "__init__.py",
        "entrada": raiz / "app" / "routes" / "entrada_personagens.py",
        "base": raiz / "templates" / "base.html",
    }
    for nome, arquivo in caminhos.items():
        if not arquivo.is_file():
            raise RuntimeError(f"Arquivo esperado ausente: {arquivo} ({nome}). Instale antes a Etapa 10B.2.")
    antes = {chave: caminho.read_text(encoding="utf-8") for chave, caminho in caminhos.items()}
    depois = dict(antes)

    if "instalar_fichas_por_url(app)" not in depois["app"]:
        trecho = "    Config(raiz).aplicar(app)"
        novo = (trecho + "\n"
                "    # FICHAS_POR_URL_10B3: URL e cookies independentes por jogador.\n"
                "    from app.services.fichas_url_service import instalar_fichas_por_url\n"
                "    instalar_fichas_por_url(app)")
        depois["app"] = _trocar_exatamente(depois["app"], trecho, novo, arquivo="app/__init__.py")
    if "from app.routes.fichas_url import fichas_url_bp" not in depois["app"]:
        ancora = "    from app.routes.entrada_personagens import entrada_personagens_bp"
        depois["app"] = _trocar_exatamente(
            depois["app"], ancora, ancora + "\n    from app.routes.fichas_url import fichas_url_bp", arquivo="app/__init__.py"
        )
    if "app.register_blueprint(fichas_url_bp)" not in depois["app"]:
        ancora = "    app.register_blueprint(entrada_personagens_bp)"
        depois["app"] = _trocar_exatamente(
            depois["app"], ancora, ancora + "\n    app.register_blueprint(fichas_url_bp)", arquivo="app/__init__.py"
        )

    if "# FICHAS_POR_URL_10B3: a seleção" not in depois["entrada"]:
        src = depois["entrada"]
        marco = "@entrada_personagens_bp.post(\"/login/personagem/<int:numero>\")"
        if marco not in src:
            raise RuntimeError("Rota entrar_com_personagem não encontrada. Nenhuma gravação foi feita.")
        inicio, corpo = src.split(marco, 1)
        inicio_antigo = '''    if session.get("usuario_id"):
        return redirect(url_for("inicio"))

'''
        corpo = _trocar_exatamente(corpo, inicio_antigo, "", arquivo="app/routes/entrada_personagens.py")
        fim = '''    usuario, personagem, campanha = autenticado
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
        novo = '''    # FICHAS_POR_URL_10B3: a seleção não substitui a sessão de outra aba.
    from app.services.fichas_url_service import url_ficha_de_login, url_selecao
    usuario, _, _ = autenticado
    try:
        destino = url_ficha_de_login(usuario.login)
    except ValueError:
        flash("Este login não pode ser usado como URL de personagem.", "erro")
        return redirect(url_selecao()), 303
    return redirect(destino), 303'''
        corpo = _trocar_exatamente(corpo, fim, novo, arquivo="app/routes/entrada_personagens.py")
        depois["entrada"] = inicio + marco + corpo

    # A 10B.3.1 não altera auth.py: logout de ficha é resolvido pelo
    # before_request do módulo fichas_url_service, sem depender de texto
    # ou ordem de implementação da rota tradicional do Mestre.

    if "{# FICHAS_POR_URL_10B3:" not in depois["base"]:
        src = depois["base"]
        antigo = '''<div class="usuario-topo">'''
        novo = '''<div class="usuario-topo">
                {# FICHAS_POR_URL_10B3: seletor independente da sessão principal. #}
                {% if request.environ.get('ANKAR_FICHA_LOGIN') %}
                    <a class="botao botao-secundario botao-link" href="{{ request.environ.get('ANKAR_SCRIPT_ROOT_ORIGINAL', '') }}/selecionar">Trocar personagem</a>
                {% endif %}'''
        src = _trocar_exatamente(src, antigo, novo, arquivo="templates/base.html")
        # Nas URLs por personagem, Trocar personagem substitui Sair para não
        # acumular botões no cabeçalho do celular. O Sair normal é preservado.
        # O botão Sair pode ser diferente conforme ajustes locais do tema;
        # mantê-lo é seguro, pois a rota resolve o logout no contexto da URL.
        # Ocultá-lo aqui é apenas cosmético e nunca deve bloquear a instalação.
        import re
        padrao = re.compile(
            r"(<form\b[^>]*\baction=\"\{\{\s*url_for\(['\"]auth\.logout['\"]\)\s*\}\}\"[^>]*>.*?</form>)",
            re.DOTALL,
        )
        encontrados = list(padrao.finditer(src))
        if len(encontrados) == 1:
            form_logout = encontrados[0].group(1)
            src = src.replace(form_logout, "{% if not request.environ.get('ANKAR_FICHA_LOGIN') %}" + form_logout + "{% endif %}", 1)
        depois["base"] = src

    # As verificações acima são concluídas antes de qualquer gravação.
    saida = {}
    for chave, caminho in caminhos.items():
        saida[caminho.relative_to(raiz).as_posix()] = _salvar(caminho, antes[chave], depois[chave])

    adicao = (
        "\n\n<!-- FICHAS_POR_URL_10B3 -->\n"
        "### 2026-10-28 — Etapa 10B.3: Fichas independentes por URL\n"
        "- Cada personagem configurado possui URL estável `/p/<login>/`, por exemplo `/p/lucas/jogador/dashboard`.\n"
        "- WSGI ajusta SCRIPT_NAME/PATH_INFO: `url_for` preserva contexto em links, formulários e arquivos estáticos.\n"
        "- Cookies Flask separados por jogador (nome e caminho) preservam o login de Mestre e outras abas.\n"
        "- Cada requisição revalida conta, personagem e campanha no PostgreSQL; apenas nove contas jogador configuradas.\n"
        "- Autorização limitada aos endpoints do jogador. Acesso administrativo permanece fora de `/p/<login>/`.\n"
        "- GET `/selecionar` mostra a escolha mesmo que haja login Mestre em outra aba.\n"
        "- Acesso por URL é sem senha, inclusive para ações de jogador: compartilhar links concede acesso à ficha.\n"
        "- Sem migrations, sem mudanças em senhas, dados da campanha ou sprites.\n"
        "- Testes: `python -m pytest -q tests/test_fichas_por_url_10b3.py tests/test_fichas_por_url_10b3_flask.py`.\n"
        "- 10B.3.1: instalador independe da implementação do logout em auth.py, paths de teste normalizados no Windows.\n"
    )
    for nome in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        arquivo = raiz / "docs" / nome
        if arquivo.exists():
            valor = arquivo.read_text(encoding="utf-8")
            saida[arquivo.relative_to(raiz).as_posix()] = _salvar(arquivo, valor, valor if "<!-- FICHAS_POR_URL_10B3 -->" in valor else valor + adicao)
    return saida


if __name__ == "__main__":
    print("Etapa 10B.3 instalada:", instalar())
