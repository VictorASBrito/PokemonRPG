"""Etapa 10C.4.1: substitui alertas flash globais por toasts temporarios.

Altera exclusivamente templates/base.html; nunca acessa banco de dados.
Exige ancora unica, faz copia .bak-10c4-1 e pode ser executado novamente.
"""
from __future__ import annotations

import argparse
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MARCADOR = "AVISOS_TOAST_10C4_1"

ANTIGO_FLASH = '''    <main class="conteudo" id="conteudo-principal" tabindex="-1">
        {% with mensagens = get_flashed_messages(with_categories=true) %}
            {% for categoria, mensagem in mensagens %}
                <div class="alerta alerta-{{ categoria }}" role="alert">{{ mensagem }}</div>
            {% endfor %}
        {% endwith %}

        {% block conteudo %}{% endblock %}
    </main>'''

NOVO_FLASH = '''    <main class="conteudo" id="conteudo-principal" tabindex="-1">
        {% block conteudo %}{% endblock %}
    </main>

    {# AVISOS_TOAST_10C4_1: mensagens globais sem ocupar espaco do conteudo. #}
    <section class="avisos-toast" data-avisos-toast aria-label="Avisos do sistema">
        {% with mensagens = get_flashed_messages(with_categories=true) %}
            {% for categoria, mensagem in mensagens %}
                {% set tipo = categoria if categoria in ('sucesso', 'erro', 'aviso', 'info') else 'info' %}
                <div class="aviso-toast aviso-toast--{{ tipo }}" role="{{ 'alert' if tipo == 'erro' else 'status' }}" data-aviso-toast data-tempo-ms="1500">
                    <span class="aviso-toast-icone" aria-hidden="true"></span>
                    <span class="aviso-toast-mensagem">{{ mensagem }}</span>
                    <button type="button" class="aviso-toast-fechar" data-aviso-toast-fechar aria-label="Fechar aviso">&times;</button>
                </div>
            {% endfor %}
        {% endwith %}
    </section>'''

CSS_ANTIGO = '''    <link rel="stylesheet" href="{{ url_for('static', filename='css/pokemon-hd.css', v='etapa-09') }}">'''
CSS_NOVO = CSS_ANTIGO + '''
    <link rel="stylesheet" href="{{ url_for('static', filename='css/avisos-toast-10c4-1.css', v='10c4-1') }}">'''
JS_ANTIGO = '''    <script src="{{ url_for('static', filename='js/tema.js') }}"></script>'''
JS_NOVO = JS_ANTIGO + '''
    <script src="{{ url_for('static', filename='js/avisos-toast-10c4-1.js', v='10c4-1') }}" defer></script>'''


def trocar_unico(texto: str, antigo: str, novo: str, nome: str) -> str:
    n = texto.count(antigo)
    if n != 1:
        raise RuntimeError(f"{nome}: ancora ausente ou repetida ({n}). Nenhuma alteracao aplicada.")
    return texto.replace(antigo, novo, 1)


def preparar(conteudo: str) -> str | None:
    """Retorna novo texto ou None (quando ja instalado). Nao escreve arquivo."""
    if MARCADOR in conteudo:
        esperado = (
            "data-aviso-toast", "data-tempo-ms=\"1500\"",
            "avisos-toast-10c4-1.css", "avisos-toast-10c4-1.js",
        )
        if not all(s in conteudo for s in esperado):
            raise RuntimeError("Instalacao anterior incompleta. Revise templates/base.html.")
        return None
    # Preflight: nenhuma escrita se qualquer uma das tres ancoras falhar.
    novo = trocar_unico(conteudo, ANTIGO_FLASH, NOVO_FLASH, "flash no base.html")
    novo = trocar_unico(novo, CSS_ANTIGO, CSS_NOVO, "link CSS no base.html")
    novo = trocar_unico(novo, JS_ANTIGO, JS_NOVO, "link JS no base.html")
    return novo


def instalar(raiz: Path = RAIZ) -> bool:
    raiz = Path(raiz)
    for recurso in (
        "static/css/avisos-toast-10c4-1.css",
        "static/js/avisos-toast-10c4-1.js",
    ):
        if not (raiz / recurso).is_file():
            raise RuntimeError(f"Arquivo do pacote nao encontrado: {recurso}")
    caminho = raiz / "templates/base.html"
    texto = caminho.read_text(encoding="utf-8")
    resultado = preparar(texto)
    if resultado is None:
        return False
    backup = caminho.with_name("base.html.bak-10c4-1")
    if backup.exists():
        raise RuntimeError("Ja existe base.html.bak-10c4-1 sem instalacao concluida; revise manualmente.")
    backup.write_text(texto, encoding="utf-8")
    tmp = caminho.with_name("base.html.tmp-10c4-1")
    try:
        tmp.write_text(resultado, encoding="utf-8")
        tmp.replace(caminho)
    finally:
        tmp.unlink(missing_ok=True)
    return True


def main() -> None:
    p = argparse.ArgumentParser(description="Instala os toasts globais da Etapa 10C.4.1")
    p.add_argument("--raiz", type=Path, default=RAIZ)
    args = p.parse_args()
    mudou = instalar(args.raiz)
    print("Avisos globais atualizados (10C.4.1)." if mudou else "Etapa 10C.4.1 ja instalada; nenhuma mudanca.")
    print("Sem migrations e sem qualquer acesso ao PostgreSQL.")


if __name__ == "__main__":
    main()
