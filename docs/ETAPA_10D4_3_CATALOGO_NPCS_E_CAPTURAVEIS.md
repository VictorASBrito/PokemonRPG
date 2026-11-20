# Etapa 10D.4.3 — Catálogo de NPCs, modo Manual/Aleatório e espelho Capturáveis

Base: `e51b7110e3171a4b325720d6ab473cd3653fa79b`, main.

## Entregas
1. Catálogo de NPCs fixos transferido para `/mestre/catalogo/npcs` e para navegação do Catálogo. A tela `/mestre/npcs` permanece como gerador, com link para o catálogo.
2. Gerador oferece **Manual** e **Aleatório** explicitamente. Manual requer exatamente 1–6 formas escolhidas pelo autocomplete, respeitando a opção de repetições. Aleatório considera toda a região de Ankar por padrão, com filtro opcional de localidade, zona e terreno. Tabelas são escolhidas uniformemente dentre as utilizáveis e cada sorteio conserva o d100, sem substituir ou reinterpretar faixas problemáticas.
3. Único nível de 1 a 100 por NPC/horda; todos os 1–6 Pokémon recebem o mesmo nível, inclusive nos re-sorteios.
4. Toda criação de Capturável pelo mestre ou pelo Atlas registra, na mesma transação, um Pokémon NPC na **Horda dos Capturáveis** do Time 16 do Campo. Natureza, gênero, espécie e Shiny são copiados, sem novo sorteio. Nível da representação = nível atual do personagem que encontrou o Pokémon, limitado a 1–100. O espelho organiza hordas automáticas separadas por nível, inicialmente no Time 16. Pokémon adicionados posteriormente a qualquer grupo precisam respeitar o nível dos integrantes já presentes.
5. A horda espelhada mantém vínculo único ao Capturável e mostra "Disponibilizado para captura", impedindo envio redundante. Ao remover/atribuir o Capturável, o espelho é retirado do Campo. Limpar o Campo não apaga Capturáveis; se o espelho já tiver sido removido, a atribuição/removal posterior continua normalmente.
6. A criação de Capturável é atômica com o espelho; se os limites atuais do Campo (40 grupos, 80 Pokémon, 24 por grupo) forem atingidos, ambas falham sem gravar registro parcial.
7. NPCs temporários e fixos continuam independentes das fichas dos jogadores, com cópias de Campo.

## Migration
`f41c0de520d4` depende de `e31a6cf520d4`; adiciona vínculo opcional e único `pokemons_npc_campo.capturavel_id` para `pokemons_capturaveis`. Não converte capturáveis antigos automaticamente; os novos gerados após o upgrade passam a ser sincronizados.

## Instalação após revisão e aprovação
1. Fazer backup do PostgreSQL e revisar CI e diff do PR.
2. Atualizar `main` no ambiente local após merge, com `git pull --ff-only origin main`.
3. Conferir `flask --app app.py db current` e `flask --app app.py db heads`. **Não executar upgrade diante de divergência de revisão**.
4. Aplicar `flask --app app.py db upgrade`; reiniciar Flask.
5. Testar `/mestre/catalogo/npcs`, `/mestre/npcs`, `/mestre/capturaveis` e `/campo`. Verificar criação manual, geração global e regional, nível idêntico, espelhamento automático, captura e limpeza.
6. Rodar os testes no workflow e/ou `python -m pytest -q tests/test_npcs_10d4_3.py tests/test_capturaveis_campo.py tests/test_capturaveis_atribuicao.py`.

O upgrade não foi aplicado ao banco local. Nenhuma migration é executada pelo CI.
