"""Acrescenta histórico da revisão do mapa do Atlas sem alterar linhas existentes."""
from __future__ import annotations
from pathlib import Path
MARCA = '<!-- ATLAS_ANKAR_V10A5 -->'
ENTRADA = '''
<!-- ATLAS_ANKAR_V10A5 -->
### Etapa 10A.5 — Mapa estático e revisão dos 119 pontos (28/10/2026)
- Removidos zoom e seletor redundante "Localizar no mapa"; mantida a lista de locais e o retorno `?local=<slug>#ankar-mapa`.
- Acrescentado filtro Todos (119 pontos), além de Rotas (73), Cidades (26) e Pontos de Interesse (20). Todos é o padrão.
- Revisadas manualmente as 119 coordenadas sobre o `Mapa.jpg`, preservando a identidade de cada local e o JSON de conteúdo.
- Marcadores visuais e áreas de seleção ficaram mais discretos; não se acrescentam números sobre os existentes.
- Mapa sem barra de rolagem interna nem pseudo-tooltips que causavam transbordamento ao passar o mouse.
- Somente leitura; sem migration, sem escrita no PostgreSQL, sem modificações no fluxo de capturáveis ou nas planilhas originais.
- Testar visualmente no navegador local desktop/tablet/celular, especialmente posições de números e locais muito próximos.
'''

def registrar(raiz: Path) -> list[str]:
    modificados=[]
    for nome in ('CONTINUIDADE_PROJETO.md','DIARIO_DESENVOLVIMENTO.md'):
        arquivo=Path(raiz)/'docs'/nome
        if not arquivo.is_file():
            continue
        original=arquivo.read_text(encoding='utf-8')
        if MARCA in original: continue
        arquivo.write_text(original.rstrip()+'\n\n'+ENTRADA.lstrip(),encoding='utf-8')
        modificados.append(str(arquivo))
    return modificados
if __name__=='__main__':
    raiz=Path(__file__).resolve().parents[1]
    print('Documentação atualizada:',registrar(raiz))
