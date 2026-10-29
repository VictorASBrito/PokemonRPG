"""Corrige o POST 405 do slot Mestre no Pokémon RPG (Etapa 10B.3.2).

Aplicar: python scripts/corrigir_login_mestre_10b3_2.py
Não altera PostgreSQL, data/, senhas nem as URLs individuais dos jogadores.
Valida todos os trechos antes de gravar; backups .antes_10b3_2.bak.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA = "<!-- LOGIN_MESTRE_10B3_2 -->"
ACAO_LOGIN = "{{ url_for('auth.login') }}"


def _formulario_login(texto: str) -> str:
    """A rota GET /login/coringa só exibe a tela; POST deve ser em /login."""
    tags = list(re.finditer(r"<form\b[^>]*>", texto, flags=re.I | re.S))
    posts = [m for m in tags if re.search(r"\bmethod\s*=\s*(['\"])post\1", m.group(), flags=re.I)]
    if len(posts) != 1:
        raise RuntimeError("Esperado exatamente um formulário POST em templates/login.html; revise manualmente.")
    m = posts[0]
    tag = m.group()
    acao = re.search(r"\baction\s*=\s*(['\"])(.*?)\1", tag, flags=re.I | re.S)
    if acao:
        destino = acao.group(2).strip()
        if destino == ACAO_LOGIN or destino in ('{{ url_for("auth.login") }}', '/login'):
            return texto
        if destino not in ("/login/coringa", '{{ url_for("entrada_personagens.coringa") }}', "{{ url_for('entrada_personagens.coringa') }}"):
            raise RuntimeError("Formulário já possui destino personalizado; preservado para revisão manual.")
        tag_nova = tag[:acao.start()] + f'action="{ACAO_LOGIN}"' + tag[acao.end():]
    else:
        tag_nova = tag[:-1].rstrip() + f' action="{ACAO_LOGIN}">'
    return texto[:m.start()] + tag_nova + texto[m.end():]


def _bloco_funcao(texto: str, nome: str) -> tuple[int, int]:
    encontro = re.search(rf"(?m)^def\s+{re.escape(nome)}\s*\([^\n]*\)\s*(?:->[^:\n]+)?\s*:\s*$", texto)
    if encontro is None:
        raise RuntimeError(f"Função {nome}() não encontrada. Revisar versão local.")
    fim = re.search(r"(?m)^(?:@\S|def\s+\w+\s*\(|class\s+\w+\b)", texto[encontro.end():])
    return encontro.start(), (encontro.end() + fim.start()) if fim else len(texto)


def _liberar_get_coringa(texto: str) -> str:
    inicio, fim = _bloco_funcao(texto, "coringa")
    bloco = texto[inicio:fim]
    if 'render_template("login.html")' not in bloco and "render_template('login.html')" not in bloco:
        raise RuntimeError("coringa() não renderiza o login tradicional; revisão manual necessária.")
    padrao = re.compile(
        r"(?m)^    if session\.get\(['\"]usuario_id['\"]\):\s*\n"
        r"        return redirect\(url_for\(['\"]inicio['\"]\)\)\s*\n"
    )
    revisado, n = padrao.subn("", bloco, count=1)
    if n == 0 and re.search(r"(?m)^    if\s+.*session\.get\(['\"]usuario_id['\"]\)", bloco):
        raise RuntimeError("coringa() tem guarda de sessão customizada. Revisão manual necessária.")
    return texto[:inicio] + revisado + texto[fim:]


def _permitir_troca_tradicional(texto: str) -> str:
    inicio, fim = _bloco_funcao(texto, "login")
    bloco = texto[inicio:fim]
    if 'autenticar_usuario(' not in bloco:
        raise RuntimeError("login() não corresponde ao fluxo tradicional conhecido; revisão manual necessária.")
    padrao_ok = r"(?m)^    if request\.method == ['\"]GET['\"] and session\.get\(['\"]usuario_id['\"]\):"
    if re.search(padrao_ok, bloco):
        return texto
    padrao = re.compile(r"(?m)^(    )if session\.get\((['\"])usuario_id\2\):")
    novo, quantidade = padrao.subn(r'\1if request.method == "GET" and session.get("usuario_id"):', bloco, count=1)
    if quantidade != 1:
        raise RuntimeError("Guarda inicial de login() não identificada; nenhuma alteração foi feita.")
    return texto[:inicio] + novo + texto[fim:]


def _salvar(arquivo: Path, antes: str, depois: str) -> bool:
    if antes == depois:
        return False
    backup = arquivo.with_name(arquivo.name + ".antes_10b3_2.bak")
    if not backup.exists():
        shutil.copy2(arquivo, backup)
    arquivo.write_text(depois, encoding="utf-8", newline="\n")
    return True


def instalar(raiz: Path = RAIZ) -> dict[str, bool]:
    raiz = Path(raiz)
    arquivos = {
        "templates/login.html": raiz / "templates/login.html",
        "app/routes/entrada_personagens.py": raiz / "app/routes/entrada_personagens.py",
        "app/routes/auth.py": raiz / "app/routes/auth.py",
    }
    for nome, arquivo in arquivos.items():
        if not arquivo.is_file():
            raise RuntimeError(f"Arquivo necessário ausente: {nome}. Não foi feita nenhuma alteração.")
    antes = {nome: arquivo.read_text(encoding="utf-8") for nome, arquivo in arquivos.items()}
    # Pré-validar tudo antes de escrever qualquer arquivo.
    depois = {
        "templates/login.html": _formulario_login(antes["templates/login.html"]),
        "app/routes/entrada_personagens.py": _liberar_get_coringa(antes["app/routes/entrada_personagens.py"]),
        "app/routes/auth.py": _permitir_troca_tradicional(antes["app/routes/auth.py"]),
    }
    historico = (
        "\n\n" + MARCA + "\n"
        "### 2026-10-28 — Etapa 10B.3.2: acesso Mestre, Teste e Victor\n"
        "- Corrigido `templates/login.html`: POST explicitamente para `auth.login`, não `/login/coringa` (GET).\n"
        "- `entrada_personagens.coringa` pode exibir o formulário mesmo com sessão administrativa ativa.\n"
        "- `auth.login` só redireciona sessão existente em GET; em POST valida normalmente a nova senha e substitui sessão após sucesso.\n"
        "- A correção preserva as nove fichas por URL, as contas e o PostgreSQL; sem migrations.\n"
        "- Verificação: testes `tests/test_login_mestre_10b3_2.py` e `tests/test_login_mestre_10b3_2_flask.py`.\n"
    )
    for nome in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        rel = "docs/" + nome
        arq = raiz / rel
        if arq.exists():
            arquivos[rel] = arq
            atual = arq.read_text(encoding="utf-8")
            antes[rel] = atual
            depois[rel] = atual if MARCA in atual else atual + historico
    return {nome: _salvar(arquivo, antes[nome], depois[nome]) for nome, arquivo in arquivos.items()}


if __name__ == "__main__":
    print("Etapa 10B.3.2 aplicada:", instalar())
