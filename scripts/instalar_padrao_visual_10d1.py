"""Etapa 10D.1: padrao global de cabecalhos e navegacao do catalogo.

Uso:
    python scripts/instalar_padrao_visual_10d1.py --verificar
    python scripts/instalar_padrao_visual_10d1.py

Sem acesso ao banco. Altera somente templates/base.html, com preflight,
backup local e operacao idempotente. Desenvolvido para a main @ a7198a1.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MARCADOR = 'ANKAR_PADRAO_VISUAL_10D1'
BASE_REL = Path('templates/base.html')
PONTO_CSS = "    <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/visual-global-10c5.css', v='10c5-1') }}\">"
PONTO_MENU = '    </header>\n\n    <main class="conteudo" id="conteudo-principal" tabindex="-1">'

CSS_EXTRA = '''    {# ANKAR_PADRAO_VISUAL_10D1: menu contextual e hierarquia consistente. #}
    <link rel="stylesheet" href="{{ url_for('static', filename='css/padrao-visual-10d1.css', v='10d1-1') }}">'''

MENU_CATALOGO = '''    {# Navegacao contextual da administracao; as rotas e permissoes sao as existentes. #}
    {% set ui10d_endpoint = request.endpoint or '' %}
    {% if ui10d_endpoint.startswith('catalogo_admin.') %}
    <nav class="ui10d-menu-contexto" aria-label="Seções do catálogo">
        <span class="ui10d-menu-contexto-titulo">Catálogo</span>
        <div class="ui10d-menu-contexto-links">
            <a href="{{ url_for('catalogo_admin.dashboard') }}"{% if ui10d_endpoint == 'catalogo_admin.dashboard' %} aria-current="page"{% endif %}>Visão geral</a>
            <a href="{{ url_for('catalogo_admin.pokemons') }}"{% if 'pokemon' in ui10d_endpoint %} aria-current="page"{% endif %}>Pokémon</a>
            <a href="{{ url_for('catalogo_admin.golpes') }}"{% if 'golpe' in ui10d_endpoint or 'vinculo' in ui10d_endpoint %} aria-current="page"{% endif %}>Golpes</a>
            <a href="{{ url_for('catalogo_admin.itens') }}"{% if 'item' in ui10d_endpoint %} aria-current="page"{% endif %}>Itens</a>
        </div>
    </nav>
    {% endif %}
'''


def _trocar_unico(conteudo: str, antigo: str, novo: str, descricao: str) -> str:
    if conteudo.count(antigo) != 1:
        raise RuntimeError(
            f"Ancora inesperada em {descricao}: {conteudo.count(antigo)} ocorrencia(s). "
            "Nao houve alteracao. Confira a versao do projeto."
        )
    return conteudo.replace(antigo, novo, 1)


def preparar(raiz: Path = RAIZ) -> dict[Path, str]:
    raiz = Path(raiz)
    base = raiz / BASE_REL
    texto = base.read_text(encoding='utf-8')
    if MARCADOR in texto:
        # Não tentar reinstalar parcialmente sobre um template alterado.
        if texto.count(MARCADOR) != 1 or 'ui10d-menu-contexto' not in texto:
            raise RuntimeError('Instalacao 10D.1 parcial. Revise templates/base.html.')
        return {}
    if 'ANKAR_VISUAL_RESPONSIVO_10C5' not in texto:
        raise RuntimeError('A Etapa 10C.5 nao foi encontrada no template base.')
    texto = _trocar_unico(texto, PONTO_CSS, PONTO_CSS+'\n'+CSS_EXTRA, str(BASE_REL))
    texto = _trocar_unico(
        texto,
        PONTO_MENU,
        '    </header>\n\n'+MENU_CATALOGO+'\n    <main class="conteudo" id="conteudo-principal" tabindex="-1">',
        str(BASE_REL),
    )
    return {base: texto}


def instalar(raiz: Path = RAIZ, verificar: bool = False) -> list[str]:
    raiz = Path(raiz)
    alteracoes = preparar(raiz)
    resultado = [p.relative_to(raiz).as_posix() for p in alteracoes]
    if verificar or not alteracoes:
        return resultado
    # Todos os planos validados antes de gravar o primeiro arquivo.
    pasta_backup = raiz / 'relatorios' / 'backups_ui_10d1' / datetime.now().strftime('%Y%m%d-%H%M%S')
    for arquivo, novo in alteracoes.items():
        destino = pasta_backup / arquivo.relative_to(raiz)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(arquivo.read_bytes())
        arquivo.write_text(novo, encoding='utf-8')
    print('Backup local:', pasta_backup)
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verificar', action='store_true', help='Verifica sem gravar nada.')
    args = parser.parse_args()
    try:
        encontrados = instalar(verificar=args.verificar)
    except (RuntimeError, OSError) as exc:
        parser.error(str(exc))
    if encontrados:
        print(('Pronto para instalar' if args.verificar else 'Atualizado')+': '+', '.join(encontrados))
    else:
        print('Padrao 10D.1 ja instalado. Nenhuma alteracao.')


if __name__ == '__main__':
    main()
