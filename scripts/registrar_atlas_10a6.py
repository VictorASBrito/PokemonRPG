"""Atualiza aditivamente os documentos de continuidade do PokémonRPG."""
from __future__ import annotations
from pathlib import Path
MARCA='<!-- ATLAS_ANKAR_V10A6 -->'
ENTRADA='''
<!-- ATLAS_ANKAR_V10A6 -->
### Etapa 10A.6 — Formas Pokémon e busca contextual por encontros (28/10/2026)
- 33 nomes pendentes de Ankar mapeados para 44 opções de forma verificadas em `data/catalogo/pokemons.json`, por código do cadastro; ativação condicionada à existência no PostgreSQL.
- Regionalismos Alola/Galar e estilos Oricorio agora resolvidos pelo serviço do Atlas. Nomes com várias formas (Basculin, Burmy, Eiscue, Indeedee, Minior, Morpeko, Pumpkaboo, Wishiwashi) exigem seleção explícita ao gerar; POST valida a correspondência sem confiar no navegador.
- `Shellos (A)` e `Shellos (R)` mantidos como entradas diferentes no Atlas, mas ambos usam provisoriamente o `shellos` genérico por falta de duas formas próprias no catálogo. Confirmar letras dos Oricorio com mestre.
- Pesquisa abaixo do mapa identifica rotas/cidades/POIs por nome de Pokémon da planilha ou forma do catálogo, e exibe a zona/terreno dos encontros nos resultados.
- Interface 10A.5 do mapa fixo, filtros e coordenadas preservada. Nenhum XLSX/JSON legado ou dado PostgreSQL modificado; nenhuma migration.
- Testes isolados executados em preparação: 22 aprovados; integração Flask/DB e verificação de formas ativas precisam ser rodadas localmente com `tests/test_ankar_10a6_flask.py` e `scripts/diagnosticar_formas_ankar.py`.
- Referência técnica: `docs/ATLAS_ANKAR_10A6.md`.
'''

def registrar(raiz: Path) -> list[str]:
    atualizados=[]
    for nome in ('CONTINUIDADE_PROJETO.md','DIARIO_DESENVOLVIMENTO.md'):
        caminho=Path(raiz)/'docs'/nome
        if not caminho.is_file(): continue
        original=caminho.read_text(encoding='utf-8')
        if MARCA in original: continue
        caminho.write_text(original.rstrip()+'\n\n'+ENTRADA.lstrip(),encoding='utf-8')
        atualizados.append(str(caminho))
    return atualizados

if __name__=='__main__':
    print('Documentação atualizada:',registrar(Path(__file__).resolve().parents[1]))
