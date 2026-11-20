# Planejamento 10E — Espécies, evoluções e transformações

**Status: desenho técnico; não implementado automaticamente.**

## Estrutura verificada (main, 20/11/2026)
- `EspeciePokemon`: código, nome, número nacional, geração e estado.
- `FormaPokemon`: espécie dona, tipo de forma (normal, regional,
  mega, alternativa, personalizada), atributos, tipos, imagens.
- `EvolucaoPokemon`: relação dirigida origem → destino,
  `tipo_requisito`, `requisitos` JSON e observações. Ainda não é
  consumida pelas páginas de Pokémon.
- `Pokemon`: instância do jogador com `forma_pokemon_id`, PV, Shiny,
  natureza, item, golpes, status. **Não possui nível individual**:
  `calcular_pokemon()` usa `Personagem.nivel`.

## 10E.1 — Ordenação (atual)
Consultar por sequência original importada (1.064 formas) e preparar
auditoria dos números nacionais. Não renumerar dados de campanha no escuro.

## 10E.2 — Integridade do Catálogo e relações

**10E.2.1 — Auditoria de vínculos e numeração:** implementada como comando
`flask --app app.py catalogo auditar-pokedex` em branch própria.
O serviço é somente leitura, compara números e espécie de cada forma com
a fonte, diferencia Nidoran♀/♂ e reporta quantidade de Pokémon ativos
impactados. Consulte `docs/ETAPA_10E2_1_AUDITORIA_POKEDEX.md`.
**O saneamento dos vínculos encontrados ainda não foi executado.**

**Próximo incremento 10E.2.2:** após analisar o relatório da instalação
real, criar o painel administrativo de relações. Evolução permanente,
troca de forma reversível e Mega devem ser categorias de vínculo distintas;
não inferir mudanças regionais automáticas nem quebrar a regra do nível
compartilhado por personagem.

1. Auditar espécies, formas alternativas e número nacional; definir
   normalização distinta para Nidoran♀/Nidoran♂ e variantes.
2. Criar na edição de forma um painel **Relações**:
   - pré-evolução / evolução;
   - forma base e alternativa, como Morpeko;
   - Mega Evolução e retorno à forma base;
   - variante regional (linhagem própria), sem permitir trocar
     livremente de região.
3. Validar ciclos indevidos, duplicações, categorias compatíveis,
   integridade de FKs e regras obrigatórias.
4. Exibir árvore de evolução e variantes relacionadas no Catálogo.
5. Relações customizadas podem apontar a formas do catálogo oficiais
   ou criadas pelo mestre, por IDs estáveis.

## 10E.3 — Evolução de Pokémon pertencente a jogador
1. Um serviço de elegibilidade consulta evoluções de `EvolucaoPokemon`
   e requisitos por tipo: nível, item, troca, amizade, condições especiais
   e autorização narrativa do mestre.
2. O botão **Evoluir** aparece **apenas quando requisitos registrados
   forem atendidos**; casos sem regra explícita não devem ser habilitados.
3. Evolução **permanente** atualiza `Pokemon.forma_pokemon_id`, com log
   anterior/depois, revisão de tipo, atributos, PV e golpes, preservando
   identidade/nível/XP conforme regras definidas.
4. Suportar destinos alternativos (ex.: dois ramos de evolução).

## 10E.4 — Mudança de formas e Mega Evolução
1. Mudança de forma reversível (Morpeko como referência do Bartz):
   opções de mudança explícitas, controladas por mestre ou jogador
   conforme permissões e requisitos; manter identidade.
2. Mega Evolução: transição temporária e retorno à forma de origem,
   com regras de item/recurso/condição que o mestre definir.
3. Guardar forma anterior e estado de transformação ativa para
   revertê-la com segurança mesmo se personagem sair do Campo.
4. Regras de cálculo devem recalcular os atributos com a forma nova,
   sem perder bônus, natureza, identidade, histórico ou equipamentos.
5. Forma regional: variante/linhagem vinculada; **não é transformação
   genérica livre**. Preservar origem regional e relações evolutivas.

## 10E.5 — UX e regressões
- Controles nas páginas do Pokémon e do mestre; confirmação das ações.
- Testes completos de elegibilidade, evolução, reversão de Mega,
  status, PV, forma customizada, captura e Campo.
- Migration com backup, atualização de modelos existentes e auditoria
  de todos os Pokémon dos jogadores.

## Decisão de regra ainda necessária
A campanha atual define **nível do Pokémon igual ao do treinador**.
Para um botão "Evoluir ao atingir o nível X" há duas possibilidades:
(A) continuar usando o nível do treinador como condição, ou
(B) introduzir nível individual por Pokémon, o que exige mudar
`Pokemon`, cálculos, equipe, Box, NPCs/hordas e telas de captura.
**Não implementar essa parte antes de decidir qual regra vale.**

**10E.2.1.2 — Saneamento controlado (em branch):** o relatório real
apontou 897 números NULL, Nidoran♂ ausente e forma `nidoran-2`
vinculada à espécie feminina. Implementados plano de simulação com
assinatura SHA-256, bloqueios para divergências, comando
`flask --app app.py catalogo sanear-pokedex`, aplicação sob backup
explicitamente confirmado, histórico e rollback. O importador agora
distingue Nidoran♂/♀. **Nenhuma correção foi aplicada no PostgreSQL
real.** Consultar `docs/ETAPA_10E2_1_2_SANEAMENTO_POKEDEX.md`.
O editor de relações 10E.2.2 depende da revisão pós-saneamento.


## Entrega 10E.2.2 — Editor administrativo de relações (2026-11-20)

**Implementação preparada em branch:** `feature/10e2-2-editor-relacoes-pokemon`.
Utiliza a tabela `EvolucaoPokemon` já existente. A interface do mestre
cadastra relações de evolução permanente, Mega temporária, forma alternativa
e parentesco regional, distinguindo metadados e impedindo ciclos permanentes.
Seis evoluções de iniciais foram conferidas com PokéAPI e Pokémon Database,
com Charmander → Charmeleon também confirmado no manual PKMRPG v2.5
(cap. 9, p. 44). Consulte `docs/ETAPA_10E2_2_RELACOES_POKEMON.md`.

**Limite da entrega:** não altera fichas nem cria comandos de evolução
para jogadores. Não reintroduz amizade/XP individuais. A árvore completa
e importações assistidas de outras cadeias ficam para 10E.2.3.


## 10E.2.3 — Árvore evolutiva e propostas revisadas (20/11/2026)

Foi preparada a etapa `feature/10e2-3-arvore-evolutiva`:
visualização de famílias completas com ramos, convergências,
pré-evoluções e requisitos das relações permanentes. Mega,
alternativas e linhagens regionais ficam visualmente separadas.
O catálogo apresenta 12 novas propostas revisadas além das seis da
10E.2.2: cinco Eeveelutions por pedra, Pikachu e Vulpix padrão
aprováveis uma a uma; Espeon, Umbreon, Sylveon e dois estágios de
Porygon pendentes de regra da campanha. Ver
`docs/ETAPA_10E2_3_ARVORE_EVOLUTIVA.md`.

As exigências de amizade do manual (inclusive materiais de evolução)
foram preservadas como **alerta editorial**: a campanha Ankar
não possui amizade numérica, então a elegibilidade real precisa de
uma regra do mestre na 10E.3. Nada é importado em massa ou aplicado
a Pokémon de jogadores nesta etapa. Sem migration.


## 10E.2.4 — Geração integral das relações da Pokédex (20/11/2026)

Nova decisão do mestre: **todas as evoluções simples por nível ou
pedra** são cadastradas em lote e usadas pela árvore evolutiva;
amizade, troca, itens específicos e condições complexas devem ser
**liberadas pelo mestre para cada Pokémon** na campanha.

A versão de 898 espécies da PokéAPI contém **430 relações**:
297 exclusivamente por nível, 43 por pedras comuns e 90
casos que exigem liberação narrativa. Inclui a origem exata de
linhagens regionais de Galar para evitar associação à forma errada.
O manual PKMRPG 2.5 exige amizade máxima 100 para materiais, mas
Ankar não usa amizade numérica; a regra explícita atual autoriza
pedras comuns como caminhos regulares. Itens especiais ainda são
restritos. Árvores são pré-configuradas, mas Pokémon capturados
**não evoluem automaticamente**.

O serviço `importacao_evolucoes_service.py` e a tela do mestre
`Catálogo → Gerar árvores evolutivas` carregam as 430 relações
de modo aditivo e idempotente após simulação, backup verificado e
confirmação, sem reescrever vínculos preexistentes. Dados estão em
`data/referencias/pokedex_evolucoes_898_10e2_4.json`; mais
detalhes em `docs/ETAPA_10E2_4_GERACAO_COMPLETA_EVOLUCOES.md`.

**10E.3:** próxima etapa precisa de autorização transacional
por Pokémon para evoluções especiais, escolha do jogador,
consumo correto de pedra e recálculo dos atributos. Não confundir
sinalização no catálogo com autorização individual já implementada.
