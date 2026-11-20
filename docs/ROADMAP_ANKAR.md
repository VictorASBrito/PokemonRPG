# Roadmap de Ankar — situação verificada em 20/11/2026

> Fonte de verdade do histórico técnico: commits da branch main e documentação
> das etapas em docs/. A existência do código não substitui teste visual/local
> nem homologação no PostgreSQL da campanha.

## Concluído e integrado à main
- **10D.2:** Central do Mestre, PV de treinadores/Pokémon e cura.
- **10D.3:** cards verticais compactos de jogadores, equipe 2×3.
- **10D.4:** adversários NPC e hordas nos 16 times do Campo.
- **10D.4.2:** catálogo de NPCs fixos, gerador regional 1–6 e integração horda → Capturáveis.
- **10D.4.3:** modos Manual/Aleatório, nível único, localidade opcional e novos Capturáveis espelhados como hordas.
- **10D.4.4:** ficha de NPC fixo, Vida, Status, equipe e anotações privadas. PR #4 integrado em `be684c5`.

## Em correção — prioridade imediata
- **10D.4.5:** distinguir geração concluída de auditoria das tabelas
  `d100`. Exibir métricas consolidadas em painel expansível, com o total
  de tabelas consultadas/aptas, sem sugerir falha de uma equipe válida.
- **Política de formas múltiplas:** definir resolução explícita para
  Basculin, Burmy, Eiscue, Indeedee, Minior, Morpeko, Pumpkaboo e
  Wishiwashi. Não presumir forma base nem atribuir arbitrariamente uma
  forma de combate/regional; validar com regras da campanha.
- **Auditoria do Atlas:** revisar 136 linhas marcadas como reconstruídas,
  dois registros inválidos e faixas sobrepostas. As 6.519 faces sem
  intervalo são a soma de lacunas entre 352 tabelas, não uma falha em uma
  única rota; verificar por tabela antes de propor ajustes de probabilidades.

## Pendente para planejamento / implementação
- **Homologação real:** executar migrations e validação visual em
  PostgreSQL com backup e dados da campanha, incluindo dispositivos móveis.
- **NPCs e hordas — polimento:** revisar fichas, status narrativos e
  condições, identidade dos integrantes e reutilização no Campo.
- **Capturáveis:** testar e refinar fluxo de geração visual, vínculo
  com hordas, atribuição de Pokémon e tratamento de limites.
- **Catálogo de Itens:** retomar auditoria e edição/criação de itens
  e consistência dos dados, conforme solicitado anteriormente.
- **10D.5 — combate:** turnos, iniciativa, condições de status, ações
  dos adversários e controle do mestre (não implementado).
- **Integrações futuras:** evitar automatizar IA/captura sem desenho
  e aprovação das regras do RPG.

## Decisões vigentes
- A geração Aleatória percorre as localidades de Ankar, com filtros
  opcionais de rota, cidade, zona e terreno.
- O modo Manual seleciona espécies do catálogo; equipes têm de 1 a 6
  Pokémon, todos no nível do treinador ou horda.
- Modelos NPC fixos possuem ficha e notas privadas, separados de Usuário.
- O modelo permanente e a instância colocada em Campo têm estados
  independentes.
- Capturáveis recém-gerados originam representações de horda, com
  vínculo único e identidade preservada.

## Próxima revisão de projeto
Prioridade 1: validar o aviso e a UX. Prioridade 2: decidir as oito
regras de formas alternativas. Prioridade 3: auditoria localizada
das tabelas de encontros. Depois, concluir testes de Campo/Capturáveis
e definir escopo de 10D.5.
