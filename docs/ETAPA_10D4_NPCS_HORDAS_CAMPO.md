# Etapa 10D.4 — NPCs e hordas no Campo compartilhado

Base GitHub: `25b5c764b1060029f9a5300c537917cce4a234dc` (`main`).

## Escopo

Esta etapa mantém o Campo existente (16 times, polling a cada seis segundos, permissões de cada jogador) e adiciona adversários **independentes das fichas**. A criação, o ajuste de PV, a remoção e a movimentação são exclusivos do mestre; jogadores veem NPCs e hordas, mas não os modificam.

- **Treinador NPC:** grupo nomeado do tipo `npc`; é possível acrescentar outras espécies depois da criação.
- **Horda:** grupo nomeado do tipo `horda`; pode ter várias cópias de uma espécie, ou espécies adicionais.
- **Cadastro:** nome, tipo, forma oficial do catálogo, nível de 1 a 100, quantidade de 1 a 12 por operação e time de 1 a 16.
- **Limites:** até 40 grupos na campanha, até 80 Pokémon adversários, até 24 por grupo.
- **PV:** calculado do PV base da forma pelo progresso de nível configurado na campanha. Pokémon NPC não recebem ajustes da natureza, estilo de treinador ou bônus manuais; essas regras específicas ficam para sprint futura.
- **Persistência:** duas tabelas novas, `grupos_npc_campo` e `pokemons_npc_campo`.
- **Integridade:** operações serializadas por lock da campanha no PostgreSQL e registradas em `historico_alteracoes`. Exclusão de grupo só remove seus próprios adversários.
- **Limpar Campo:** retira as posições dos Pokémon dos jogadores **e** os adversários temporários. Não exclui Pokémon de fichas, Boxes ou Capturáveis. Confirmação na interface.
- **Sincronização:** os jogadores enxergam os mesmos grupos na atualização HTML existente de `/campo/estado` (seis segundos).
- **Visual:** jogadores enxergam nomes, imagens, tipos, níveis e PV; controles de mestre não aparecem para jogadores.

Não há combate automático, iniciativa, ataques, IA, captura automática nem atribuição de NPCs às Boxes.

## Arquivos

- `app/models/db/campo_npc.py` e exportação em `app/models/db/__init__.py`
- `app/services/campo_npc_service.py` e integração com `campo_service.py`
- `app/routes/combates.py` com rotas exclusivas do mestre e CSRF
- `templates/campo/painel.html`, `templates/campo/_times.html`
- `static/css/campo-npcs-10d4.css` e atualização no `static/js/campo.js`
- `migrations/versions/c84f2b1a7d90_npcs_hordas_campo.py`
- `tests/test_campo_npcs_10d4.py` e workflow de testes em Pull Request

## Como validar e instalar (após aprovação do Pull Request)

1. Revise o diff e o resultado do CI. Nenhuma migration foi aplicada automaticamente.
2. Faça **backup completo do PostgreSQL** e mantenha os jogadores desconectados durante a atualização.
3. Confirme o Git local limpo, entre na branch `main` e atualize com `git pull --ff-only origin main` depois do merge.
4. Execute `flask --app app.py db current` e `flask --app app.py db heads`. A nova revisão é `c84f2b1a7d90`, dependente da revisão `7a1f20d9c405`. Verifique a cadeia antes de continuar.
5. Com backup e revisão confirmados, execute `flask --app app.py db upgrade`.
6. Execute `python -m pytest -q tests/test_campo_npcs_10d4.py tests/test_campo_compartilhado.py`.
7. Reinicie o Flask, pressione Ctrl+F5 e abra `/campo` em duas sessões: mestre e jogador.
8. Crie uma horda no Time 2 e um treinador NPC no Time 3; confirme visibilidade para jogadores e ausência dos controles administrativos para eles.
9. Ajuste PV, mova grupos e retire um membro até eliminar o último. Confira o comportamento de `Limpar campo` e confirme que as Boxes não foram alteradas.

## Observações

- A autorização é verificada no servidor, não apenas pela ocultação dos botões.
- O seletor visual de espécies fica em painel fixo fora do fragmento do Campo atualizado por polling.
- A ação de limpar remove os adversários mesmo quando o campo dos jogadores está vazio.
- A migration altera somente o esquema do banco; não importa, modifica ou redistribui Pokémon já existentes.
- Para reverter a migration é necessário eliminar os registros temporários destas duas tabelas. Não execute downgrade em produção sem backup.
