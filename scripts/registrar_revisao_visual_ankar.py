"""Registra a etapa 10A.3 no histórico existente sem reescrever o passado."""
from pathlib import Path

MARCA = '<!-- ANKAR_10A3_REVISAO_VISUAL -->'
CONTINUIDADE = '''
<!-- ANKAR_10A3_REVISAO_VISUAL -->
### Etapa 10A.3 — Mapa interativo e revisão visual (28/10/2026)
- Integração **somente leitura** do `Mapa.jpg` original em `/regiao/ankar`: 119 marcadores manuais, 73 rotas, 26 cidades e 20 POIs vinculados aos slugs existentes.
- Filtros de pontos, zoom, toque, identificação e links de detalhe; acesso exclusivo do mestre, como na etapa 10A.2.
- CSS do Atlas harmonizado com as variáveis do design system; estilos globais e telas de jogador permanecem inalterados.
- Mapa em `static/img/ankar-mapa.jpg` e posições em `app/data/mapa_ankar_pontos.json`. Não representa caminhos calculados.
- Seis testes de mapa e verificações Chromium isoladas em 390/820/1440 px passaram. Validação integrada do Flask e do site real pendente no ambiente do mestre.
- Sem migration, acesso a PostgreSQL, alteração de planilha ou de contas.
- Detalhes: `docs/REVISAO_VISUAL_ANKAR_10A3.md`.
'''
DIARIO = '''
<!-- ANKAR_10A3_REVISAO_VISUAL -->
### 2026-10-28 — Etapa 10A.3: mapa interativo e revisão visual
- **Status:** IMPLEMENTAÇÃO INCREMENTAL, TESTES ISOLADOS PASSARAM; VALIDAÇÃO FLASK/LOCAL PENDENTE.
- **Objetivo:** aproveitar o mapa original sem reformular a experiência dos jogadores em mobile/tablet/desktop.
- **Arquivos:** JSON com 119 marcadores, JPG original, serviço/rota Atlas, índice/detalhe, CSS/JS Atlas, testes e documentação.
- **Preservação:** nenhuma tela do jogador, CSS global, banco, `.env`, uploads ou planilha original modificados. Sem migrations.
- **Validações locais:** 6 testes pytest, sintaxe Node, compilação Python e interações Chromium nas larguras 390/820/1440 px. Sem testes integrados Flask neste ambiente.
- **Próxima ação:** testar no servidor real do mestre, ajustar eventuais coordenadas e revisar capturas das telas existentes antes de mudanças globais.
'''


def registrar(raiz: Path) -> list[str]:
    atualizados = []
    for nome, bloco in [('CONTINUIDADE_PROJETO.md', CONTINUIDADE), ('DIARIO_DESENVOLVIMENTO.md', DIARIO)]:
        destino = raiz / 'docs' / nome
        if not destino.is_file():
            continue
        original = destino.read_text(encoding='utf-8')
        if MARCA in original:
            continue
        destino.write_text(original.rstrip() + '\n\n' + bloco.strip() + '\n', encoding='utf-8')
        atualizados.append(str(destino.relative_to(raiz)))
    return atualizados


if __name__ == '__main__':
    raiz = Path(__file__).resolve().parent.parent
    print('Documentos atualizados:', registrar(raiz))
