"""Instala a entrada circular sem substituir arquivos existentes do projeto.

Uso: python scripts/instalar_entrada_personagens.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

MARCADOR = "ENTRADA_PERSONAGENS_10B1"
RAIZ = Path(__file__).resolve().parent.parent


def _atualizar(arquivo: Path, atual: str, novo: str) -> bool:
    if atual == novo:
        return False
    backup = arquivo.with_name(arquivo.name + ".antes_10b1.bak")
    if not backup.exists():
        shutil.copy2(arquivo, backup)
    arquivo.write_text(novo, encoding="utf-8", newline="\n")
    return True


def instalar(raiz: Path = RAIZ) -> dict:
    raiz = Path(raiz)
    app = raiz / "app" / "__init__.py"
    auth = raiz / "app" / "routes" / "auth.py"
    base = raiz / "templates" / "base.html"
    arquivos = [app, auth, base]
    for arquivo in arquivos:
        if not arquivo.is_file():
            raise RuntimeError(f"Arquivo existente necessário não encontrado: {arquivo}")
    textos = {arquivo: arquivo.read_text(encoding="utf-8") for arquivo in arquivos}
    a, b, c = (textos[p] for p in arquivos)

    if "from app.routes.entrada_personagens import entrada_personagens_bp" not in a:
        ancora = "    from app.routes.auth import auth_bp"
        if ancora not in a:
            raise RuntimeError("Não foi possível localizar o import do auth_bp.")
        a = a.replace(ancora, ancora + "\n    from app.routes.entrada_personagens import entrada_personagens_bp", 1)
    if "app.register_blueprint(entrada_personagens_bp)" not in a:
        ancora = "    app.register_blueprint(auth_bp)"
        if ancora not in a:
            raise RuntimeError("Não foi possível localizar registro do auth_bp.")
        a = a.replace(ancora, ancora + "\n    app.register_blueprint(entrada_personagens_bp)", 1)

    if MARCADOR not in b:
        ancora = '    return render_template("login.html")'
        posicao = b.rfind(ancora)
        if posicao == -1:
            raise RuntimeError("O GET original de /login mudou. Revisar manualmente antes de instalar.")
        novo = '''    # ENTRADA_PERSONAGENS_10B1: GET visual; POST de usuário/senha preservado.
    from app.services.entrada_personagens_service import listar_slots_visuais, slots_vazios
    try:
        slots = listar_slots_visuais(campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao listar personagens na entrada visual.")
        slots = slots_vazios()
    return render_template(
        "entrada_personagens.html",
        slots=slots,
        entrada_csrf=session.setdefault("entrada_personagens_csrf", secrets.token_urlsafe(32)),
    )'''
        b = b[:posicao] + novo + b[posicao + len(ancora):]
    # O botão Senha só deixa de ser exibido em sessões criadas por seleção direta.
    ancora = '''<a class="botao botao-secundario botao-link" href="{{ url_for('auth.trocar_senha') }}">Senha</a>'''
    if "session.get('entrada_visual')" not in c:
        if ancora not in c:
            raise RuntimeError("Não foi possível localizar o atalho 'Senha' no template base.")
        c = c.replace(ancora, "{% if not session.get('entrada_visual') %}" + ancora + "{% endif %}", 1)

    retorno = {}
    for arquivo, conteudo in ((app, a), (auth, b), (base, c)):
        retorno[str(arquivo.relative_to(raiz))] = _atualizar(arquivo, textos[arquivo], conteudo)
    for nome in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        arquivo = raiz / "docs" / nome
        if not arquivo.exists():
            continue
        texto = arquivo.read_text(encoding="utf-8")
        marca = "<!-- ENTRADA_PERSONAGENS_10B1 -->"
        if marca not in texto:
            adicao = ("\n\n" + marca + "\n### 2026-10-28 — Etapa 10B.1: Seleção visual de personagens\n"
                      "- Tela de entrada com nove slots em círculo e acesso coringa tradicional.\n"
                      "- Login visual restrito a nove contas `jogador` explicitamente configuradas em `data/entrada_personagens.json`; mestre, administrador e tester nunca são aceitos.\n"
                      "- Rotas: GET `/login`, GET `/login/coringa`, POST `/login/personagem/<numero>`.\n"
                      "- Sessões existentes e login tradicional preservados; CSRF na seleção direta.\n"
                      "- Configurar contas com `scripts/configurar_entrada_personagens.py`, documentado em `docs/ENTRADA_VISUAL_ANKAR.md`.\n"
                      "- Risco aceito: entrada sem senha permite que qualquer visitante escolha um personagem visível; exigir controle de acesso externo caso o site seja público.\n"
                      "- Nenhuma migration ou importação no PostgreSQL.\n")
            _atualizar(arquivo, texto, texto + adicao)
    return retorno


if __name__ == "__main__":
    print("Entrada visual:", instalar())
