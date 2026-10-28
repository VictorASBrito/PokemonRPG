"""Registro aditivo/idempotente da revisão de Atlas, sem tocar código ou DB."""
from pathlib import Path

MARCADOR = '<!-- ATLAS_ANKAR_V10A4 -->'
REGISTRO = '''\n\n<!-- ATLAS_ANKAR_V10A4 -->
### 2026-10-28 — Etapa 10A.4: Atlas compacto e geração de capturáveis
- Mapa inteiro visível à esquerda com filtros e seleção à direita no desktop; responsivo em mobile/tablet, sem alteração nas demais páginas.
- Descrição narrativa abreviada na ficha, com conteúdo integral expansível em parágrafos; habitats, acessos e d100 preservados.
- Tabelas de Pokémon em cards com artes do catálogo. `x` indica sem encontro e não gera Pokémon.
- Com autorização de mestre e confirmação, o card escolhe treinador e delega ao serviço `criar_capturavel_campo` atual (natureza, sexo, Shiny, limite 15, histórico).
- Criada rota POST do atlas com CSRF e validação da entrada original, sem mutation de planilhas.
- Sem migration. Testes Python/Flask e revisão final no navegador do usuário pendentes de execução local.
- Próximo passo: validar navegação e geração real de um encontro; depois analisar espécies sem correspondência entre planilha e catálogo.
'''


def registrar(raiz: Path) -> list[str]:
    escritos = []
    for nome in ('CONTINUIDADE_PROJETO.md', 'DIARIO_DESENVOLVIMENTO.md'):
        destino = raiz / 'docs' / nome
        if not destino.is_file():
            continue
        atual = destino.read_text(encoding='utf-8')
        if MARCADOR not in atual:
            destino.write_text(atual.rstrip() + REGISTRO + '\n', encoding='utf-8')
            escritos.append(str(destino.relative_to(raiz)))
    return escritos


if __name__ == '__main__':
    print('Documentos atualizados:', registrar(Path(__file__).resolve().parents[1]))
