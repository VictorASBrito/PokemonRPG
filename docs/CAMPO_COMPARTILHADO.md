# Painel compartilhado de Pokémon — Etapa 07

## Objetivo e decisões da campanha

Esta funcionalidade permite posicionar Pokémon existentes das **equipes dos treinadores** em até **16 times numerados**. Jogadores enxergam os mesmos grupos, podendo distribuir os Pokémon de adversários em times diferentes ou concentrar aliados no mesmo time. **Não automatiza** dano, iniciativa, turnos, PP ou chance de captura.

A mecânica de tentativa de captura **não será implementada**, por decisão do responsável pela campanha: as tentativas acontecem de maneira narrativa na mesa; o mestre decide a atribuição pela interface de capturáveis já concluída.

## Fluxo e permissões

- Página compartilhada `/campo` para contas logadas mestre, administrador, jogador e tester, com menu `Campo`.
- Jogador: seleciona exclusivamente um Pokémon ativo da **própria equipe** e um time (1–16); pode reposicioná-lo e retirá-lo. Não manipula Pokémon alheios.
- Mestre/Admin: pode posicionar, mover e retirar os Pokémon das equipes de todos os jogadores, e **limpar campo** (sem excluir os Pokémon das fichas).
- Cada Pokémon ocupa no máximo **um** time; repetir a seleção apenas troca o time. Não há limite fixo de Pokémon por time, além do limite de equipe já existente por personagem.
- A página atualiza automaticamente as posições a cada 6 segundos consultando `/campo/estado` (HTML parcial). Falha na conexão não altera o banco.
- Transferir um Pokémon para a Box ou removê-lo da ficha elimina automaticamente sua posição de batalha na mesma transação.
- Exibe nome/apelido, sprite, espécie, treinador, tipos e marcador Shiny. HP e ações detalhadas poderão entrar em uma próxima fase.

## Modelo e integridade

A migration `7a1f20d9c405` cria `pokemons_em_campo`, referenciando `campanhas` e `pokemons`, com `time_numero` entre 1 e 16, e chave única por `pokemon_id`. As mudanças de posicionamento registram `historico_alteracoes`. As operações do campo são transacionais; seleção de campanha usa lock de linha em PostgreSQL para serializar as ações do campo.

Arquivos principais: `app/models/db/pokemon_battlefield.py`, `app/services/campo_service.py`, `app/routes/combates.py`, `templates/campo/`, `static/css/campo.css`, `static/js/campo.js`, `tests/test_campo_compartilhado.py`. A sincronização de equipe/Box também envolve `app/services/pokemon_db_service.py`.

## Instalação e testes

1. Fazer backup do PostgreSQL e copiar apenas os arquivos do pacote incremental para a pasta atual `PokemonRPG`.
2. Aplicar migration: `flask --app app.py db upgrade`.
3. Verificar revisão: `flask --app app.py db current` (deve exibir `7a1f20d9c405`).
4. Executar: `python -m pytest -q tests/test_campo_compartilhado.py`.
5. Validar manualmente com dois navegadores/contas: colocar em Time 1 e Time 2, conferir atualização sem reload, formar aliados no mesmo time, remover/alterar time e mover para Box.

A migration **não** altera `pokemons`, inventário, fichas ou encontros capturáveis existentes.

## Limites atuais e próximas decisões

- Pokémon aptos a entrar em campo são **somente os da equipe** de personagens cadastrados; Pokémon criados como NPC independentes precisam de uma extensão futura.
- O painel separa times e exibe sprites; ainda **não** executa regras de combate, dano, iniciativa ou condições de vitória. Ações de combate poderão ser adicionadas depois sem alterar a decisão narrativa sobre capturas.
