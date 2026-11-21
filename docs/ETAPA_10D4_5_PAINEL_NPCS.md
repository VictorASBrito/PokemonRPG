# 10D.4.5 — Painel individual para NPCs fixos

## Objetivo
Fornecer ao mestre um painel de NPC com a mesma linguagem visual e interação expandida do painel dos jogadores. NPCs **não** passam a ser usuários, personagens com conta, ou Pokémon dos jogadores.

## Navegação
- `Catálogo → NPCs → Painel NPC` em cada card, ou `Ficha NPC → Abrir Painel NPC`.
- URL de mestre: `/mestre/catalogo/npcs/<modelo_id>/painel`.
- Layout responsivo reutiliza `dashboard.css`, o comportamento de selecionar/recolher `dashboard-pokemon.js`, os selos de tipo e o autocomplete do catálogo.

## Conteúdo
- Coluna lateral: imagem, nome, classe, nível, vida do NPC, atributos e anotações narrativas privadas.
- Equipe até seis: imagens, Shiny, tipo, nível compartilhado, vida e lista dos golpes salvos.
- Ao selecionar um Pokémon, aparecem seus atributos base e progressão, informação de Natureza/gênero, quatro espaços de golpes e comandos de edição.
- O mestre pode editar apelido, forma do catálogo (não permite Mega como forma permanente), Natureza, gênero, Shiny e os quatro golpes pelo mesmo catálogo de golpes utilizado pelos jogadores.
- Ações rápidas: dano/cura, mover posição, retirar Pokémon mediante confirmação em modal. Campos vazios permitem adicionar Pokémon pela busca visual.
- Dado de NPC continua guardado no JSON da `NPCModelo.equipe` e alterações são registradas no histórico. O índice exibido corresponde à posição real do JSON, mesmo quando um registro legado está inconsistente.

## Regras preservadas
- Modificadores de Natureza, bônus Shiny e progressão são lidos das regras atuais da campanha para os atributos exibidos.
- O nível do Pokémon acompanha o NPC; não ganha nível próprio.
- O painel não gerencia inventário, dinheiro, Box, captura, login, autoria de jogador ou combate ao vivo.
- O Campo continua em pausa; instâncias do Campo continuam independentes do modelo NPC persistido.
- Rotas GET/POST exigem mestre; CSRF, campanha e índice do membro são validados no servidor.
- Alterar a forma pelo mestre mantém o dano sofrido e não altera os Pokémon dos jogadores. As mudanças da equipe do NPC não afetam o Campo nem os modelos de outros NPCs.

## Banco / publicação
- Sem migration: são usados apenas campos de `NPCModelo` já presentes, com novos campos JSON opcionais para os golpes editados (`golpes`), que modelos antigos podem não possuir.
- Nenhuma alteração automática de dados de produção.
- Testes: `tests/test_painel_npcs_10d4_5.py` e a suíte legada `test_fichas_npcs_10d4_4.py` integrada ao workflow `test-fichas-npcs.yml`.
- Após integrar e publicar, validar NPC com equipe de seis, PV, Natureza, golpes, reorganização e telas mobile.

## Limitação planejada
O NPC ainda não utiliza instâncias do tipo `Pokemon` dos jogadores. Futuras ações de evolução/Mega e mecânica de combate devem usar serviços próprios para modelos NPC, com autorização do mestre e identidade do Pokémon preservada, sem permitir ações cruzadas entre jogadores e NPCs.
