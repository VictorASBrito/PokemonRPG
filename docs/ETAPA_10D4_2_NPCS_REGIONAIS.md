# Etapa 10D.4.2 — NPCs fixos, temporários, hordas e gerador regional de Ankar

## Base
Main no commit `d85099560b6d69b6390fe44dbf85986e536b7151` (10D.4 já integrada).
Esta etapa estende o Campo existente sem alterar Pokémon de jogadores.

## Comportamento
- Tela `/mestre/npcs`, exclusiva do mestre, acessível pelo menu **NPCs** e pelo Campo.
- Fixo: equipe-modelo permanente de 1–6 Pokémon, exibida em cards com sprites; reutilização cria instância independente no Campo. Pode atualizar equipe a partir de nova prévia ou arquivar modelo sem afetar encontros ativos.
- Temporário: equipe regional de 1–6 Pokémon criada diretamente em um dos 16 times.
- Horda: mesmo gerador, 1–6 Pokémon com repetições permitidas. O mestre escolhe o treinador encontrador antes do sorteio, para aplicar os números Shiny já usados pelo sistema da campanha.
- Seleção: localidade > zona > terreno (somente opções existentes no `app/data/catalogo_ankar_visual.json`). Respeita intervalos d100 válidos. Roll ambíguo, vazio, reconstruído ou espécie sem vínculo único no catálogo é rejeitado e informado na prévia. Não converte `captura` (%) em peso de encontro.
- Prévia: nível fixo ou faixa 1–100, natureza e sexo sorteados, rolagem d100, Shiny e botão de re-sortear membro individual antes de salvar.
- Capturáveis: apenas integrantes de hordas podem ser encaminhados, sob confirmação do mestre e limite de 15 ativos. Transfere natureza, gênero e Shiny originais sem novo sorteio; impede reenvio mesmo após remover o registro capturável. O Pokémon continua visível no Campo com marcador de disponibilização. Limpar Campo preserva capturáveis.
- Hordas criadas antes desta etapa podem ter natureza/gênero vazios porque os campos não existiam: a transferência não inventa dados legados.
- O gerador não automatiza golpes, IA, iniciativa, captura ou turnos.

## Banco de dados
Migration `e31a6cf520d4` dependente de `c84f2b1a7d90`. Cria `npcs_catalogo`, adiciona vínculos opcionais às instâncias em Campo e os campos de natureza, gênero e estado de captura aos Pokémon NPC. Não altera dados existentes.

## Instalação depois do Pull Request aprovado
1. Verifique os resultados dos testes do GitHub Actions e revise as alterações.
2. Faça backup completo do PostgreSQL; mantenha a campanha pausada durante o upgrade.
3. `git checkout main` e `git pull --ff-only origin main` após o merge.
4. `flask --app app.py db current` e `flask --app app.py db heads`. Revise a cadeia; não aplique upgrade com divergências.
5. `flask --app app.py db upgrade`.
6. `python -m pytest -q tests/test_gerador_npcs_ankar.py tests/test_npcs_ankar_10d4.py tests/test_migration_npcs_regional.py tests/test_campo_npcs_10d4.py tests/test_campo_compartilhado.py`.
7. Reinicie Flask e abra `/mestre/npcs`. Gere NPC fixo e instancie-o no Time 2. Gere horda no Time 3, selecione o treinador encontrador e envie integrante a Capturáveis. Confira preservação de natureza/gênero/Shiny e bloqueio de duplicata.
8. Abra o Campo em outra sessão como jogador e confirme apenas visualização.

## Segurança
Operações mutáveis exigem mestre, CSRF e validação de campanha no banco. Dados de modelo no catálogo são armazenados por campanha, e somente podem instanciar Pokémon cujas formas seguem ativas. Instâncias não afetam os modelos fixos. Não execute downgrade sem backup: ele elimina o catálogo permanente.
