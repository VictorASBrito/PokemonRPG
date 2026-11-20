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
