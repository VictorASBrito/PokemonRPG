# 10E.2.4 — Geração de todas as árvores evolutivas e liberação do mestre

**Escopo:** 898 espécies oficiais, 430 relações de evolução por espécie na
fonte PokéAPI consultada em 20/11/2026. A árvore usa exclusivamente o
PostgreSQL depois da importação; **não** consulta a API em cada página.

## Resultado do cruzamento

| Categoria | Relações |
|---|---:|
| Exclusivamente por nível, sem outras condições | **297** |
| Uso de uma pedra evolutiva comum, sem outra condição | **43** |
| Total de relações simples, cadastradas sem revisão individual | **340** |
| Amizade, troca, item específico, horário, gênero, movimento, local, clima, outra condição | **90** |
| **Total** | **430** |

A fonte está em
`data/referencias/pokedex_evolucoes_898_10e2_4.json`, um arquivo
estático versionado com origem, destino, números nacionais,
requisito, ponteiro para a PokéAPI e classificação. Gerada dos CSVs
públicos do repositório **PokeAPI/pokeapi**:
`data/v2/csv/pokemon_species.csv`,
`pokemon_evolution.csv` e `items.csv`.
Revisão pontual com [Pokémon Database](https://pokemondb.net/evolution)
e com o livro `pkmrpg-playtest-2_5.pdf`.

**Importante:** o projeto Ankar contempla as **898 espécies até Calyrex**
e não deve criar Pokémon das gerações posteriores ao importar dados.
Cada forma de origem/destino é o código **exato** do catálogo existente,
incluindo a distinção Nidoran♀ (`nidoran`) / Nidoran♂ (`nidoran-2`).

### Política conservadora de automatização

- **Nível automático** só quando a PokéAPI indica `level-up` com
  nível mínimo definido e **nenhum requisito adicional**.
  A futura evolução efetiva continuará opcional e usará o nível
  **compartilhado com o treinador**, nunca experiência individual.
- **Pedras automáticas** somente quando a PokéAPI usa uma entre
  Water, Fire, Thunder, Leaf, Moon, Sun, Shiny, Dusk, Dawn e Ice Stone
  sem condições extras. O registro da relação **não consome** uma pedra,
  não altera Box, nem executa a evolução.
- **Reservadas ao mestre, por Pokémon individualmente:** amizade,
  troca, itens específicos (como Up-Grade, Dubious Disc, Protector),
  locais, tempo do dia, gênero, estatísticas, movimento conhecido,
  clima, condições de combate e uso de pedra com restrição adicional.
  A evolução pela Pedra da Alvorada de Kirlia macho e Snorunt fêmea,
  por exemplo, exige liberação do mestre: a pedra sozinha não basta.
- **Eevee → Umbreon, Espeon e Sylveon** são necessariamente
  reservadas ao mestre: **não** são nível automático e
  **não** são uma pedra comum sem condição.
- Linhagens regionais não são trocadas livremente. A origem correta
  é especificada no dado: `meowth-galar` → `perrserker`,
  `corsola-galar` → `cursola`,
  `mr-mime-galar` → `mr-rime` são evoluções simples por nível.
  `linoone-galar` → `obstagoon` exige noite,
  `farfetch-d-galar` → `sirfetch-d` exige condição de combate,
  `yamask-galar` → `runerigus` exige requisito de dano/local:
  permanecem reservadas.
- `spewpa` → `vivillon` foi preservada no nível 12, embora
  suas formas de padrão regional possuam IDs específicos na fonte.

**Divergência com o livro:** no capítulo 16, p. impressa 59, o manual
PKMRPG 2.5 exige amizade máxima 100 para utilizar qualquer material
evolutivo. A campanha Ankar **retirou a amizade numérica**. A
solicitação atual do mestre estabelece que o uso de pedras **comuns**
pode seguir a regra regular, sem liberação narrativa individual.
Requisitos de itens especiais continuam na área exclusiva do mestre.
Essa decisão da campanha prevalece sobre o requisito de amizade do
livro, mas não define consumo automático de itens nesta etapa.

## Como gerar as árvores

A importação é **aditiva**, idempotente e intencionalmente não é
executada na inicialização da aplicação ou na abertura da Pokédex.

### Pela interface

Entre como **mestre → Catálogo Pokémon → Gerar árvores evolutivas**.
A primeira página mostra **simulação**, totais, relações existentes
preservadas, conflitos e assinatura. Para aplicar, faça primeiro backup
restaurável do PostgreSQL, assinale essa confirmação e informe
`GERAR-ARVORES-ANKAR`.

### Pelo PowerShell do servidor

**1. Simular (não grava dados):**

```powershell
flask --app app.py catalogo gerar-arvores-pokemon
```

**2. Fazer e verificar backup do PostgreSQL fora do repositório.**
O JSON de auditoria não é backup. Nenhum backup é criado
automaticamente pelo comando.

**3. Aplicar com a assinatura SHA256 exibida no passo 1:**

```powershell
flask --app app.py catalogo gerar-arvores-pokemon --aplicar --plano SUA_ASSINATURA --backup-confirmado --confirmar GERAR-ARVORES-ANKAR
```

**4. Conferir e abrir as árvores:**

```powershell
flask --app app.py catalogo gerar-arvores-pokemon
```

Uma nova simulação deve mostrar zero vínculos pendentes. Abra
**Pokémon → Eevee → Relações → Ver árvore da família**. Todas as oito
Eeveelutions devem aparecer, com avisos de liberação individual em
Umbreon, Espeon e Sylveon. A importação pode mostrar menos de 430
novas relações se o mestre já criou algumas; **nenhuma delas será
sobrescrita, reativada ou apagada**. Se houver uma forma ausente ou
um ciclo inesperado, o processo bloqueia sem commit.

## Segurança

- Importação é explicitamente confirmada, com assinatura do plano,
  verificação humana de backup e transação única; registra
  `HistoricoAlteracao` para cada relação nova.
- O GET da interface e o comando sem `--aplicar` são de leitura.
  O formulário usa proteção de token; os endpoints são do mestre.
- O cadastro automático e a árvore **não modificam**
  `Pokemon.forma_pokemon_id`, IV, natureza, Shiny, golpes, itens,
  PV, posição na Box ou nível compartilhado do personagem.
- `EvolucaoPokemon.requisitos` identifica
  `requer_liberacao_mestre=True` e `liberacao_individual=True`.
  Um verificador conservador também trata relações antigas de
  amizade, troca, itens especiais e nível com condição como
  **restritas**, mesmo sem essas chaves.
- O editor de 10E.2.2 preserva as flags de restrição das relações
  importadas. O diagrama 10E.2.3 mostra explicitamente as relações
  que dependem do mestre, sem escondê-las.

**Atenção sobre o escopo:** ainda não foi implementada a UI/registro
transacional de autorização para um Pokémon **específico** nem a ação
que o evolui. Isso pertence à **10E.3**. Não confundir
`aprovado_mestre` (registro de catálogo) com autorização individual
para o Pokémon do jogador.

## Testes e roteiro

```powershell
python -m pytest -q tests/test_importacao_evolucoes_10e2_4.py tests/test_arvore_evolutiva_10e2_3.py tests/test_evolucoes_admin_10e2_2.py tests/test_catalogo_admin.py tests/test_auditoria_pokedex_10e2_1.py tests/test_ordenacao_pokedex_10e1.py
```

CI: `.github/workflows/test-importacao-evolucoes-10e2-4.yml`.

**Próximo:** 10E.3, evolução efetiva por decisão do treinador,
verificação de nível/pedra, consumo transacional de item,
autorização do mestre **por instância de Pokémon** para os
90 arcos especiais, histórico e recálculo sem quebrar as fichas.
