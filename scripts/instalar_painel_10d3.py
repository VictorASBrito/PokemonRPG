"""Etapa 10D.3 — substitui apenas o template do Painel do Mestre (commit bfc6d9c).

Use --verificar primeiro. Não modifica banco, serviços, rotas ou permissões.
O CSS é fornecido separadamente no ZIP, em static/css/.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil

MARCADORES_ORIGEM = (
    'ANKAR_10D2_CENTRAL_MESTRE',
    'painel-jogador-atributos-expansivel',
    'data-cura-10d2',
    'painel-mestre-jogadores',
)
MARCADOR_DESTINO = 'ANKAR_10D3_CARDS_VERTICAIS'
REL_DESTINO = Path('templates/mestre/dashboard.html')
REL_MODELO = Path('patch_10d3/dashboard.html')
REL_CSS = Path('static/css/painel-mestre-10d3.css')


class InstalacaoIncompativel(RuntimeError):
    pass


def instalar(raiz: Path, *, verificar: bool = False) -> list[str]:
    raiz = Path(raiz)
    destino = raiz / REL_DESTINO
    modelo = raiz / REL_MODELO
    css = raiz / REL_CSS
    for arquivo in (destino, modelo, css):
        if not arquivo.is_file():
            raise InstalacaoIncompativel(f'Arquivo obrigatório não encontrado: {arquivo.relative_to(raiz).as_posix()}')

    atual = destino.read_text(encoding='utf-8')
    novo = modelo.read_text(encoding='utf-8')
    if MARCADOR_DESTINO in atual:
        return []
    ausentes = [nome for nome in MARCADORES_ORIGEM if nome not in atual]
    if ausentes:
        raise InstalacaoIncompativel(
            'O template não corresponde à Etapa 10D.2 do último commit. '
            'Atualize seu repositório ou confira alterações locais antes de instalar: '
            + ', '.join(ausentes)
        )
    if MARCADOR_DESTINO not in novo or 'painel-mestre-10d3.css' not in novo:
        raise InstalacaoIncompativel('O template novo parece incompleto.')
    if verificar:
        return [REL_DESTINO.as_posix()]

    pasta = raiz / 'relatorios' / 'backups_ui_10d3' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    copia = pasta / REL_DESTINO
    copia.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(destino, copia)
    # Escrita por substituição para evitar arquivos pela metade.
    temporario = destino.with_suffix('.10d3.tmp')
    temporario.write_text(novo, encoding='utf-8')
    temporario.replace(destino)
    return [REL_DESTINO.as_posix()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verificar', action='store_true', help='Valida sem alterar o template')
    args = parser.parse_args()
    raiz = Path(__file__).resolve().parents[1]
    try:
        arquivos = instalar(raiz, verificar=args.verificar)
    except InstalacaoIncompativel as erro:
        parser.error(str(erro))
    if not arquivos:
        print('10D.3 já está instalada. Nenhuma alteração necessária.')
    elif args.verificar:
        print('Pré-validação OK: ' + ', '.join(arquivos))
    else:
        print('Template atualizado: ' + ', '.join(arquivos))
        print('Backup salvo em relatorios/backups_ui_10d3/. Reinicie o Flask e use Ctrl+F5.')


if __name__ == '__main__':
    main()
