# Etapa 11A — Acervo visual e expansão incremental de itens

## Fontes e diagnóstico

- Manual PKMRPG Playtest v2.5, capítulo 16 (pp. 57–67, numeração impressa; os TMs seguem a lista do RPG, não a numeração de outras gerações).
- Manifesto histórico `app/data/itens_padronizados_10c3.json`: 48 registros propostos, 21 arquivos de imagem distintos associados a 24 registros. Não é uma consulta ao banco atual.
- Pasta `static/img/inventory/itens/`: 37 PNGs, 16 sem associação nesse manifesto. O primeiro lote cobre 11 desses 16. Conferir com o mestre `chaveiro_quebrado.png`, `disfarce.png`, `keystone.png`, `livro.png`, `livro2.png`; não identificar objetos narrativos apenas pelo nome do arquivo.
- PokéAPI Sprites: https://github.com/PokeAPI/sprites/tree/master/sprites/items — índice de 2258 PNGs na raiz, commit c0542f7c51215d9672439012838c99f520596cbd. Não confundir arquivos (incluindo variantes) com itens jogáveis. Acervo complementar: https://play.pokemonshowdown.com/sprites/itemicons/. Sprites de franquia de terceiros têm direitos próprios; verificar condições de uso/distribuição; o índice não contém os binários.

## Acervo

O índice `app/data/acervo_icones_itens_11a.json` é pesquisável sem rede. Baixar somente o necessário, mediante decisão do mantenedor, em pasta própria `static/img/inventory/acervo-pokeapi/`, preservando arte local de Ankar. Não fazer hotlink em jogo.

```powershell
python scripts/acervo_icones_itens_11a.py
python scripts/acervo_icones_itens_11a.py --buscar stone
python scripts/acervo_icones_itens_11a.py --baixar-lote
```

O último comando precisa de rede, baixa apenas cinco arquivos PNG da versão fixada, valida assinatura/tamanho e não sobrescreve arquivos existentes. Os ícones ainda não foram baixados para o repositório.

## Lote 11A (16 itens candidatos)

| Grupo | Itens | Implementação |
|---|---|---|
| Cura de PV | Super Poção (60), Hiper Poção (120), Max Poção (100%), Água Especial (30), Refri (50), Limonada (80), Leite Moomoo (100) | Recuperação limitada ao PV máximo, alvo próprio e consumo transacional via módulo existente |
| Status | Cura Total | Remove as sete condições descritas no manual por seus UUIDs efetivos; não usar efeito Todos indiscriminadamente |
| Evolução | Água, Trovão, Folha, Lua, Brilhante, Crepúsculo, Alvorada, Gelo | Códigos canônicos do serviço de materiais; consumo por evolução autorizada, jamais no botão genérico da Bag |

Preços e ícones estão em `app/data/novos_itens_11a.json`. A importação não inventa preços de itens sem mercado, nem altera os do catálogo presente. Fogo e Sol já constam do manifesto histórico: conferir a simulação/auditoria antes de alterar os registros existentes. A regra própria da campanha para Mega é permissão de treinador, sem exigência de pedras; não reintroduzir essa exigência. Amizade e demais regras do manual devem ser reconciliadas com o fluxo vigente, não impostas por este lote.

## Implantação no ambiente local

O PostgreSQL não foi acessado pelo assistente. O catálogo é global (não exclusivo da campanha). Antes de gravar, faça backup do PostgreSQL e revise a simulação. A CLI não altera schema, não deleta, não reativa nem atualiza itens existentes e não distribui unidades. Se identificar código/nome/alias já cadastrado, mostra os dados atuais para revisão. Ambiguidade, categoria inativa, arquivo ausente ou status ausente bloqueia o lote inteiro. Operação transacional e idempotente, com histórico por criação.

```powershell
python scripts/ampliar_catalogo_itens_11a.py
```

Após revisar o relatório e baixar os cinco ícones necessários:

```powershell
python scripts/ampliar_catalogo_itens_11a.py --aplicar --confirmar ADICIONAR-ITENS-11A
flask --app app.py catalogo auditar-itens --todos
flask --app app.py inventario verificar
```

Pode limitar a simulação/aplicação com `--somente super-pocao hiper-pocao max-pocao`. Esta versão insere faltantes; atualizações de itens antigos exigem revisão separada. Não executar o script destrutivo de reconstrução 10C.3. Nenhuma migration necessária.

## Etapas seguintes

| Etapa | Escopo | Dependência |
|---|---|---|
| 11B | Revisão de preços, ícones, nomes e efeitos dos itens já presentes, com relatório do banco real | Exportação/simulação + decisão de conflitos |
| 11C | Captura: bolas e bônus de captura; consumo vinculado à tentativa | Fluxo de captura transacional e regras de Ankar |
| 11D | Bagas, alimentos, remédios/Revive e modificadores | Status e combate, PP se utilizado na campanha, regras de desmaio e limites por Pokémon |
| 11E | Materiais especiais, fósseis e formas alternativas; Megas como referências sem exigência de pedra | Regras já vigentes de evolução/transformação e revisão de ressurreição |
| 11F | TMs 00–99 do manual, ensino de golpes, compatibilidade | Catálogo de golpes e autorização de aprendizado |
| 11G | Geral, pesca, exploração, incubadoras, itens narrativos | Regras de sessão, cronômetro/comando do mestre; arte personalizada |

Os itens sem motor de execução devem ser rotulados como manuais ou pendentes; jamais marcar como utilizável automaticamente e consumir sem efeito. Manter as cinco bolsas do jogo e distinguir classificação por categoria no catálogo de agrupamento visual da Bag.

## Testes

O workflow `.github/workflows/test-catalogo-itens-11a.yml` exercita o importador e regressões existentes em SQLite. Teste de lote completo usa arquivos PNG de fixture no diretório temporário, não a rede; não confirma download dos sprites externos. Teste guarda o material genérico, verifica que o motor terapêutico realmente recupera PV/remove status e que aplicar novamente não duplica registros. Playwright existente é relevante para confirmar Bag e catálogo, sem usar dados reais.

**Status:** implementação inicial pronta para PR; validação CI pendente. Não declarar catálogo completo nem dados de produção importados.
