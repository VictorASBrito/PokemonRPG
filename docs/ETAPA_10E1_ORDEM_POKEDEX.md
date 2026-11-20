# 10E.1 — Ordenação da Pokédex no Catálogo e nos seletores

## Origem do erro
O Catálogo Administrativo já ordenava por `EspeciePokemon.numero`. Porém,
a importação antiga (`app/services/importacao/catalogo_importer.py`)
criou espécies oficiais com `numero=None`, fazendo todas as espécies
serem ordenadas alfabeticamente. Por isso o primeiro card era Abomasnow.

A fonte original `data/catalogo/pokemons.json` contém 1.064 **formas**
em `ordem_catalogo` sequencial: Bulbasaur 1, Ivysaur 2, Venusaur 3,
Venusaur Mega 4, Charmander 5 etc. São 898 **nomes de espécies**
distintos até Calyrex; **esses 1.064 números não são números nacionais**
e não podem ser atribuídos diretamente a `EspeciePokemon.numero`.

## Correção implementada
- Usar `FormaPokemon.configuracoes["ordem_catalogo"]` como ordenação
  prioritária na listagem do Catálogo, no seletor de formas e no autocomplete.
- Espécies/novas formas sem sequência importada ficam depois dos registros
  de origem, desempate por número nacional quando cadastrado, nome e UUID.
- A ordenação é SQL, anterior à paginação: páginas 1, 2 etc. mantêm sequência.
- Nenhum Pokémon, forma, número da espécie ou outra tabela é renumerado;
  nenhuma migration é necessária.
- Testes SQLite/Flask validam que Bulbasaur vem antes de Charmander e
  que uma forma "Abomasnow" sem índice não rouba a primeira posição.

## Auditoria de base antes de evoluções
- Avaliar o preenchimento definitivo do número **nacional** dos 898
  nomes da origem, sem confundir Mega/regional com espécie nova.
- Resolver importação de Nidoran♀ e Nidoran♂: a rotina de normalização
  `slug` pode reduzir os dois nomes ao mesmo código de espécie, portanto
  este caso deve ser auditado e corrigido com verificação de integridade.
- As novas espécies customizadas de Ankar precisam de número regional
  explícito ou regra de ordenação definida, sem repetir número nacional.
- O modelo `EvolucaoPokemon` já existe, mas ainda não controla botões
  de evolução/transições. Detalhes em `docs/PLANO_EVOLUCOES_E_FORMAS.md`.
