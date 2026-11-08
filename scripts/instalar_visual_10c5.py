"""Etapa 10C.5 — refinamento visual global/mobile e correção do inventário.

Uso: python scripts/instalar_visual_10c5.py [--verificar]
Não conecta ao banco, não altera rotas, permissões, sessões, modelos ou dados.
Faz pré-validação e salva cópias locais dos templates antes de modificar.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "ANKAR_VISUAL_RESPONSIVO_10C5"
BASE = Path("templates/base.html")
INVENTARIO = Path("templates/jogador/inventario.html")


def unico(texto: str, anterior: str, novo: str, nome: str) -> str:
    ocorrencias = texto.count(anterior)
    if ocorrencias != 1:
        raise RuntimeError(f"{nome}: esperado um único ponto de inserção, encontrados {ocorrencias}.")
    return texto.replace(anterior, novo, 1)


def adaptar_base(original: str) -> str:
    if MARKER in original:
        return original
    s = original
    css_atual = '''    <link rel="stylesheet" href="{{ url_for('static', filename='css/avisos-toast-10c4-1.css', v='10c4-1') }}">'''
    css_novo = css_atual + '''
    {# ANKAR_VISUAL_RESPONSIVO_10C5: último acabamento global, após os estilos existentes. #}
    <link rel="stylesheet" href="{{ url_for('static', filename='css/visual-global-10c5.css', v='10c5-1') }}">'''
    s = unico(s, css_atual, css_novo, str(BASE))
    nav_atual = '''            <nav class="navegacao-principal" aria-label="Navegação principal">'''
    nav_novo = '''            <button class="ui-mobile-nav-toggle" type="button"
                    data-ui-nav-toggle aria-controls="ui-navegacao-principal" aria-expanded="false"
                    aria-label="Abrir menu de navegação">
                <span class="ui-menu-icone" aria-hidden="true">☰</span><span>Menu</span>
            </button>
            <nav id="ui-navegacao-principal" class="navegacao-principal"
                 data-ui-navegacao aria-label="Navegação principal">'''
    s = unico(s, nav_atual, nav_novo, str(BASE))
    js_atual = '''    <script src="{{ url_for('static', filename='js/avisos-toast-10c4-1.js', v='10c4-2') }}" defer></script>'''
    js_novo = js_atual + '''
    <script src="{{ url_for('static', filename='js/visual-navegacao-10c5.js', v='10c5-1') }}" defer></script>'''
    s = unico(s, js_atual, js_novo, str(BASE))
    return s


def adaptar_inventario(original: str) -> str:
    marker = "ANKAR_VISUAL_MOCHILA_10C5"
    if marker in original:
        return original
    atual = '''<link rel="stylesheet" href="{{ url_for('static', filename='css/inventario-uso-10c4.css', v='10c4-2') }}">'''
    novo = atual + '''
{# ANKAR_VISUAL_MOCHILA_10C5: layout fluido, autocomplete e mobile/tablet. #}
<link rel="stylesheet" href="{{ url_for('static', filename='css/visual-inventario-10c5.css', v='10c5-1') }}">'''
    return unico(original, atual, novo, str(INVENTARIO))


def preparar(raiz: Path = ROOT) -> dict[Path, tuple[str, str]]:
    raiz = Path(raiz)
    fontes = {BASE: adaptar_base, INVENTARIO: adaptar_inventario}
    planos = {}
    for relativo, funcao in fontes.items():
        caminho = raiz / relativo
        anterior = caminho.read_text(encoding="utf-8")
        posterior = funcao(anterior)
        if posterior != anterior:
            planos[caminho] = (anterior, posterior)
    for nome in [
        "static/css/visual-global-10c5.css",
        "static/css/visual-inventario-10c5.css",
        "static/js/visual-navegacao-10c5.js",
    ]:
        if not (raiz / nome).is_file():
            raise RuntimeError(f"Arquivo do pacote não encontrado: {nome}")
    return planos


def instalar(raiz: Path = ROOT, *, verificar: bool = False) -> list[str]:
    raiz = Path(raiz)
    planos = preparar(raiz)  # Nenhuma gravação caso alguma âncora não exista.
    if verificar or not planos:
        return [p.relative_to(raiz).as_posix() for p in planos]
    data = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = raiz / "relatorios" / "backups_ui_10c5" / data
    for path, (anterior, _) in planos.items():
        destino = backup / path.relative_to(raiz)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(anterior, encoding="utf-8")
    aplicados = []
    try:
        for path, (_, posterior) in planos.items():
            temporario = path.with_name(path.name + ".10c5.tmp")
            temporario.write_text(posterior, encoding="utf-8")
            temporario.replace(path)
            aplicados.append(path)
    except Exception:
        for path in aplicados:
            path.write_text(planos[path][0], encoding="utf-8")
        raise
    return [p.relative_to(raiz).as_posix() for p in planos]


def main():
    parser = argparse.ArgumentParser(description="Atualiza visual responsivo do Pokémon RPG (sem modificar o PostgreSQL).")
    parser.add_argument("--verificar", action="store_true", help="Mostra os arquivos a alterar, sem gravar.")
    args = parser.parse_args()
    alterados = instalar(verificar=args.verificar)
    if not alterados:
        print("Visual 10C.5 já instalado. Nenhuma alteração.")
    else:
        print(("Seriam alterados:" if args.verificar else "Arquivos atualizados:") + "\n- " + "\n- ".join(alterados))
        if not args.verificar:
            print("Backup local em relatorios/backups_ui_10c5/. Reinicie o Flask e force recarga no navegador.")


if __name__ == "__main__":
    main()
