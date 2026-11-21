# 10D.4.7 — Mega Evolução e modos no Painel dos NPCs

## Escopo
- **Painel NPC sem subnavegação contextual do Catálogo:** mantém apenas o cabeçalho principal com o acesso às áreas gerais. As outras páginas do Catálogo conservam a barra para navegação.
- **Ações na própria imagem, à direita**, com o mesmo padrão visual do jogador:
  - Mega única: **Mega Evoluir** e imagem local `static/img/inventory/itens/keystone.png`.
  - Uma forma alternativa: **nome da forma** e sua imagem.
  - Várias formas/Megas: botão que abre a lista de imagens e nomes, com opções inválidas desabilitadas.
  - Forma temporária ativa: ação **Reverter forma**, inclusive quando ainda há outros destinos.
  - Os formulários de edição e gerenciamento dos NPCs continuam em modais; golpes e atributos não perdem espaço.
- Uma confirmação em modal centralizado antes do POST, usando `dashboard-pokemon.js` e proteção CSRF. Cancelar/Esc não altera o Pokémon.

## Regras e dados
- Mega, outras formas temporárias e destinos consultam **`listar_formas_por_base`**, função compartilhada com os jogadores; prioridades são as relações do mestre em `EvolucaoPokemon` e o fallback legado verificado.
- **Somente mestre** pode transformar Pokémon NPC pela rota `/mestre/catalogo/npcs/<id>/equipe/<indice>/transformar`. O NPC não ganha conta de jogador, inventário, Pedra Chave ou personagem próprio.
- **Uma Mega ativa por treinador NPC**; Mega não requer Campo nem pedras. Alterar outra forma com Mega ativa exige reversão primeiro.
- Pokémon com PV zero não ativa forma; desmaio durante Mega desfaz o overlay automaticamente.
- `NPCModelo.equipe` preserva `forma_id` permanente e usa os campos JSON opcionais `forma_temporaria_id` e `tipo_transformacao`. A edição de forma-base remove overlay antigo; editar atributos sem trocar a espécie mantém a transformação.
- A foto, tipos, atributos e PV máximo do card vêm da **forma visualmente ativa** (respeitando Shiny e Natureza); a transformação preserva o dano existente, não recalcula progresso ou nível do jogador.
- Auditoria histórica no modelo do NPC, separada do Histórico de Pokémon de jogador. Sem migration e sem alterações automáticas dos dados reais.

## Arquivos
`templates/base.html` — oculta subnav somente no Painel NPC.
`app/services/transformacoes_service.py` — extrai listagem por forma-base para reutilização sem modificar as regras dos jogadores.
`app/services/npc_ficha_service.py` — ações, PV dinâmico, persistência e reversão.
`app/routes/catalogo_admin.py` — rota protegida para as transformações.
`templates/mestre/catalogo/_acoes_retrato_npc.html` — botões e lista de ícones no retrato.
`templates/mestre/catalogo/npc_painel.html` — integra controles e modal.
`tests/test_painel_npcs_10d4_5.py` — Castform, Mega personalizada, exclusividade, KO e segurança.
