# 10D.4.6 — Painel do NPC visualmente alinhado ao Painel do jogador

## Problema e causa
A implementação 10D.4.5 reutilizou o CSS do Painel do jogador, cujo modo expandido de desktop distribui uma altura fixa entre os dois cartões de atributos/informações, golpes 2x2 e faixa de rodapé. O NPC acrescentava **dois painéis gigantes** dentro da mesma grade (`npc-painel-edicao` e `npc-painel-controles`); o CSS do jogador ainda aplicava `overflow:hidden` a essa região, escondendo os golpes e recortando os botões. O cabeçalho próprio dos NPCs também consumia espaço de tela que o jogador não usava.

## Layout corrigido
- Reutiliza a estrutura do jogador **sem sobrescrever a grade expandida**: identidade e atributos na lateral esquerda; retrato grande à esquerda do card selecionado; informações, atributos atuais, golpes 2x2 e rodapé à direita; demais Pokémon na lateral direita.
- Retira o cabeçalho extra; mantém links **Todos os NPCs** e **Editar ficha** na coluna lateral do treinador.
- O ajuste de PV do treinador vira um botão **Ajustar PV**, que abre diálogo.
- No rodapé de cada Pokémon: **Recolher**, **Editar Pokémon** (formulário em diálogo), **Gerenciar** (PV, reordenar, retirar da equipe).
- Adição de Pokémon ocorre por botão nos espaços vazios ou na lateral; abre diálogo com o mesmo autocomplete do catálogo.
- Retirar Pokémon abre segunda confirmação com Cancelar/Confirmar; Escape e clique no fundo fecham modais sem recolher o Pokémon expandido.
- Opções exibidas de gênero, Natureza, Shiny, golpe e nome preservam as mesmas rotas e verificações do mestre, incluindo CSRF e campanha.
- Modais responsivos, com rolagem própria quando necessário e sem imagens ou campos escapando do contêiner.

## Mudanças
`templates/mestre/catalogo/npc_painel.html`: marcação de card idêntica em ordem de layout ao jogador; formulários posicionados fora da grade; modais para gerenciamento.
`static/css/npc-painel.css`: CSS do NPC não muda a grade compartilhada; estiliza apenas atalhos e modais.
`static/js/npc-painel.js`: abre, fecha, retorna foco, suspende o Escape global e confirma retirada, sem `window.confirm`.
`tests/test_painel_npcs_10d4_5.py`: garante que card expandido não inclua formulários e que os modais funcionem, além dos testes persistentes do módulo.

**Sem migração, sem mudanças em dados do PostgreSQL e sem alterar o Campo.** Após integrar, validar visualmente NPC com seis Pokémon em desktop, tablet e celular, e testar teclado, abertura/fechamento, guardar edição e seleção de golpes.
