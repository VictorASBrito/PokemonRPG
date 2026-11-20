# 10D.4.4 — Fichas permanentes dos NPCs de Ankar

## O que muda
- Cada NPC fixo tem cadastro semelhante ao dos jogadores, mas **não tem conta/login** e não ocupa uma ficha de jogador.
- Novo NPC: **Catálogo → NPCs → Novo NPC fixo**. Campos: nome, nível, classe/papel, origem, imagem, atributos da ficha e notas narrativas privadas.
- Atributos são gerados a partir de `carregar_regras_personagem` da campanha. Saúde define os PV máximos pela mesma regra `pv_por_ponto_saude` usada nos jogadores.
- O mestre pode editar notas e atributos, aumentar/reduzir PV do treinador, adicionar/remover Pokémon e ajustar PV de cada integrante.
- O nível do NPC é aplicado a toda equipe; modelos preexistentes usam provisoriamente o nível do primeiro Pokémon até a primeira edição, sem perder atributos antigos.
- Cards de NPCs fixos no Catálogo reutilizam o layout vertical do painel de jogadores: avatar, nível/classe/origem, Vida, Status e seis posições em grade 2×3. Retirados login, permissões, inventário, dinheiro e Box.
- Anotações visíveis apenas para mestre; resumos nos cards e texto integral nas fichas.
- Gerador Manual/Aleatório da 10D.4.3 preservado. Quando gera um NPC fixo, agora inicializa atributos da ficha e PV. Atualizar a equipe pelo gerador mantém notas/classe do NPC salvo.
- Ao instanciar no Campo, cria-se cópia independente do modelo. Danos do Campo não modificam notas ou PV do catálogo.

## Migration
`a14d4e4044a1` depende de `f41c0de520d4`. Adiciona campos opcionais a `npcs_catalogo`, preservando NPCs existentes.

## Instalação
1. Revisar PR e CI.
2. Fazer backup completo do PostgreSQL.
3. Após o merge: `git checkout main`; `git pull --ff-only origin main`.
4. `flask --app app.py db current`; `flask --app app.py db heads`; confirmar sequência.
5. Após backup e cadeia conferida: `flask --app app.py db upgrade`.
6. `python -m pytest -q tests/test_fichas_npcs_10d4_4.py tests/test_migration_ficha_npcs.py tests/test_npcs_10d4_3.py tests/test_npcs_ankar_10d4.py tests/test_campo_npcs_10d4.py`.
7. Testar catálogo em desktop/celular, criação/edição, notas, níveis, equipe e PV do treinador/Pokémon com login de mestre; conferir que jogador não consegue abrir páginas de NPC.

## Limites
Não implementa IA, turnos nem integração automática dos PV de uma cópia do Campo com o modelo permanente. O propósito é dar ao mestre o controle da ficha narrativa sem alterar a dos jogadores.
