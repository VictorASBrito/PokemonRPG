"""Acrescenta entrada idempotente aos documentos históricos existentes."""
from __future__ import annotations
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCADOR = '<!-- ITENS_ANKAR_10C1_2026_10_28 -->'
TEXTO = f'''\n\n{MARCADOR}
### Etapa 10C.1 — revisão de Catálogo e Inventários (28/10/2026)
- Criado diagnóstico **somente leitura** do catálogo e dos inventários atuais com CSV de itens, quantidades, possíveis duplicatas e status de imagens: `scripts/revisar_itens_ankar_10c1.py`.
- Fonte histórica `app/seed/fichas_jogadores_ankar.json`: 109 linhas, 455 unidades, 77 grafias distintas (NÃO é o estado atual do PostgreSQL).
- Imagens são associadas a `Item.imagem_url` uma única vez; os inventários reutilizam o cadastro. Não foram criadas imagens artificiais ou itens sem especificação.
- Normalizações são apenas sugestões para revisão; não fundir códigos, inventários nem equipamentos automaticamente.
- Etapa seguinte: revisar relatórios do PostgreSQL, aprovar grafias/categorias/imagens e especificar as distribuições por login e quantidade.
- Testes puros em `tests/test_revisao_itens_10c1.py`; sem migrations e sem escrita no PostgreSQL.
'''


def registrar(raiz=RAIZ):
    alterados=[]
    for nome in ('CONTINUIDADE_PROJETO.md', 'DIARIO_DESENVOLVIMENTO.md'):
        arq=Path(raiz)/'docs'/nome
        if not arq.exists():
            continue
        original=arq.read_text(encoding='utf-8')
        if MARCADOR not in original:
            with arq.open('a',encoding='utf-8',newline='') as fp:
                fp.write(TEXTO)
            alterados.append(arq.relative_to(raiz).as_posix())
    ignore=Path(raiz)/'.gitignore'
    if ignore.exists():
        txt=ignore.read_text(encoding='utf-8')
        regra='relatorios/revisao_itens_ankar*/'
        if regra not in txt:
            with ignore.open('a',encoding='utf-8',newline='') as fp:
                fp.write('\n# Relatórios privados de inventário (10C.1)\n'+regra+'\n')
            alterados.append('.gitignore')
    return alterados


if __name__=='__main__':
    print('Documentos atualizados:', registrar())
