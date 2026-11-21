# 10E.4.2 — Ações na imagem e Campo em pausa

**Decisão do mestre:** evoluções e mudanças de forma são ações do Pokémon, não do Campo.
A implementação 10E.4.1 permanece no histórico; esta etapa substitui a apresentação das ações e a antiga dependência do Campo.

## Visual do Painel do jogador
- O retrato grande do Pokémon expandido possui **somente dois pontos de ação**: evolução elegível à esquerda (ícone vermelho) e formas/Mega/reversão à direita (ícone azul ou Keystone).
- **Uma ação válida:** clique no próprio símbolo envia o formulário com confirmação. **Várias opções:** clique abre um seletor sobre a imagem, com sprite e nome de cada destino.
- A ação de Mega usa o PNG local do inventário `static/img/inventory/itens/keystone.png` em vez de arte gerada; a imagem principal continua vinda do catálogo.
- **Não há faixa de botões abaixo dos golpes.** Menus são acessíveis por teclado e fecham por clique externo ou Escape; POST mantém CSRF, confirma e reabre o Pokémon no Painel.
- Evolução aparece só se `consultar_evolucoes_pokemon` aprovar os requisitos e não existir forma temporária ativa. A autorização narrativa e o consumo de materiais continuam no serviço.

## Independência das ações
- Mega: jogador/tester dono, treinador autorizado pelo mestre, Pokémon consciente, forma válida, **uma Mega ativa por treinador**. A autorização fica no menu `⋮` do treinador no Painel do Mestre. Sem pedras nem requisito de Campo.
- Forma alternativa: dono muda livremente entre alternativas válidas; reversão manual.
- Evolução permanente: requisitos/itens/liberação individual, fora da forma temporária. **Não depende de participação no Campo.**
- Recolher ou limpar a exibição do Campo não reverte Mega. Revogação do mestre, desmaio ou opção Reverter continuam revertendo.
- Não foram alterados esquema, nível compartilhado, inventário, dados de Pokémon ou a relação de propriedade.

## Campo temporariamente desativado
- `CAMPO_ATIVO=False` por padrão, configurável em `POKEMON_RPG_CAMPO_ATIVO=1` para uma futura exibição.
- Link Campo oculto da navegação. A URL `/campo` mostra aviso de pausa. Atualização de estado e rotas antigas de Campo recebem HTTP 503 enquanto pausado.
- Com `CAMPO_ATIVO=True`, a interface preparada é **somente leitura**: times, Pokémon, sprites, status de forma e NPCs/hordas sem controles.
- `CAMPO_OPERACOES_ATIVAS=False` (fixo por padrão) bloqueia requisições POST do Campo mesmo se a visualização estiver ligada. Apenas a suíte histórica de testes o habilita explicitamente para validar compatibilidade.
- Serviços, tabelas, formações antigas e endpoints são preservados para uma futura revisão do módulo. Nenhum registro é limpo automaticamente ao pausar a interface.

## Realocação funcional
- **Mestre → Painel → ⋮ do treinador:** autorizar/revogar Mega.
- **Jogador → Painel → retrato expandido:** evoluir, Mega Evoluir, mudar e reverter forma.
- **Catálogo → NPCs / Gerador:** geração, revisão, fichas e edição de NPCs fixos. Envio de modelos para o Campo foi temporariamente bloqueado.
- **Capturáveis:** criação, visualização e atribuição de encontros. Inclui agora a lista de integrantes de hordas geradas, com opção de encaminhar captura e escolher o encontrador, sem abrir Campo. Identidade, Natureza, gênero, Shiny e controle contra duplicação são preservados no serviço original.
- **Campo futuro:** apenas demonstrativo dos Pokémon em combate; posicionamento, ajustes de PV durante batalha, movimentação dos grupos e outras ações estritamente de combate serão planejados em etapa dedicada.

## Arquivos principais
- `templates/jogador/_acoes_retrato.html`, `templates/jogador/dashboard.html`, `static/css/dashboard.css` e `static/js/dashboard-pokemon.js`: interface do retrato.
- `app/services/painel_acoes_pokemon_service.py`, `transformacoes_service.py`, `evolucao_efetiva_service.py` e `campo_service.py`: regras independentes do Campo.
- `app/config.py`, `app/routes/combates.py`, `templates/base.html`, `templates/campo/`: suspensão e visualização.
- `app/routes/npcs.py`, `templates/mestre/npcs_catalogo.html`, `templates/mestre/catalogo/npcs.html`: gerenciamento de NPCs sem envio ao Campo.
- `app/services/hordas_captura_service.py`, `app/routes/capturas.py`, `templates/capturas/mestre.html` e `static/css/capturaveis.css`: transferência das hordas.
- Testes em `tests/test_campo_pausado_10e4_2.py`, `test_hordas_capturaveis_10e4_2.py` e regressões existentes.

## Homologação antes da sessão
1. Abrir Blaziken com permissão Mega e sem Campo: Keystone à **direita** ativa Mega com confirmação.
2. Morpeko satisfeito: botão azul à direita troca para Faminto. Depois, Reverter volta à origem.
3. Charmander elegível: ícone vermelho à **esquerda** evolui, com consumo de pedra somente se exigida.
4. Charizard: clique no Keystone à direita abre as duas Megaformas.
5. Sem permissão Mega: Keystone abre explicação, sem executar POST.
6. Mestre: botão Mega no menu `⋮`; Capturáveis permite encaminhar integrantes de hordas; geração e fichas de NPCs continuam acessíveis.
7. Campo desapareceu do menu, `/campo` informa pausa e POSTs antigos não modificam dados.
8. Fichas individuais `/p/<login>`, tester, Shiny, prévia mestre e CSS em celular permanecem corretos.

**Sem migration.** Não altera o PostgreSQL real até merge e deploy pelo mestre.
