# Etapa 10D.2 — Central única do Mestre (Ankar)

**Base:** commit `0a157b721d3a299783091583a105696fd6a77eb2` (“Repaginação visual 2”) na branch `main`.

## Mudanças

- Remove do topo os quatro cartões de métricas; mantém título, campanha, busca, filtros e ordenação manual.
- Unifica **Painel** e **Jogadores**: os controles de nível, papel de acesso e ativação ficam dentro de **Gerenciar nível e acesso** em cada card. O endereço antigo `/mestre/jogadores` permanece válido e exibe o painel unificado; o link duplicado é removido da navegação superior.
- Avatar por sprite validada em `data/entrada_personagens.json`; usa a Pokébola `static/img/pokebola.png` como fallback. A sprite é **apenas apresentação**, não autoriza acesso.
- Ações Ficha, Equipe, Inventário, Box e Prévia continuam com as URLs existentes; **Box não é mais vermelho**, pois não é ação destrutiva.
- Cards de treinadores mais compactos. Atributos ficam num bloco expansível. Nickname e espécie ocupam linhas estáveis nos cards Pokémon, sem cortes.
- Ajuste de PV por valor digitado (1–9999) e botões **−** / **+**, usando os mesmos endpoints anteriores do mestre. O servidor continua aplicando limites existentes: Pokémon de 0 ao máximo, treinador segundo sua regra atual (pode ter PV negativo).
- **Curar Pokémon** em um treinador e **Curar todos os Pokémon** em todos os treinadores: cobre equipe **e Box**, restaura PV máximos após remover condições, grava histórico e faz commit ao final.
- Curas exigem mestre, CSRF de sessão e marcador de confirmação; interface pede confirmação humana antes de enviar. Evita nova distribuição de itens, não gasta itens, e não altera PV do treinador, PP ou outros recursos.
- Fluxo da cura global inclui personagens ativos de contas jogador ou tester na campanha ativa (inclusive contas de acesso desativado), nunca Pokémon de outra campanha.
- Avisos AJAX usam o sistema de toast de 1,5s. Após a cura o navegador recarrega os dados, exibindo o toast de confirmação armazenado pelo Flask.

## Conteúdo do pacote

- `app/services/cura_mestre_10d2.py` — serviço administrativo transacional.
- `static/css/painel-mestre-10d2.css` — aparência e responsividade isoladas no painel.
- `scripts/instalar_painel_mestre_10d2.py` — instalador incremental, pré-validação, backup e idempotência.
- `tests/test_painel_mestre_10d2.py` — 6 testes isolados.
- `tests/test_painel_mestre_10d2_flask.py` — testes de integração usando o SQLite temporário das fixtures.

## Instalação

1. Confira que o `git log -1 --oneline` aponta para o commit-base ou variante compatível e que suas mudanças locais estão salvas.
2. Extraia o ZIP na raiz do projeto, preservando subpastas. O ZIP não inclui arquivos `app/routes/mestre.py` nem `templates/mestre/dashboard.html` completos: o instalador os modifica por âncoras verificadas.
3. Execute `python scripts/instalar_painel_mestre_10d2.py --verificar`; aborta se o layout local não for compatível, sem escrever nada.
4. Execute `python scripts/instalar_painel_mestre_10d2.py`; backups em `relatorios/backups_ui_10d2/`.
5. Execute `python -m pytest -q tests/test_painel_mestre_10d2.py tests/test_painel_mestre_10d2_flask.py tests/test_painel_mestre.py` e, depois, toda a suíte do repositório.
6. Reinicie Flask e faça `Ctrl+F5`. Teste com um Pokémon na Box, outro na equipe, condições, PV baixos e alvos de outra campanha.

**Importante:** a instalação não toca no PostgreSQL. Clicar em qualquer botão de cura **altera os PV e condições dos Pokémon reais** após a confirmação. Teste curas primeiro em banco de desenvolvimento/backup.

## Pendências conhecidas

- Concluir revisão real no navegador de desktop/tablet/mobile com dados de 11 treinadores, nickname longo, equipes vazias e tema claro.
- Revisar controles de status do treinador (não fazem parte da cura Pokémon).
- Consolidar CSS compartilhado das demais telas da etapa 10D, sem misturar com este patch.
- As rotas legadas de ajuste rápido de PV continuam com o contrato `delta` usado anteriormente; futuramente revisar CSRF e concorrência de alterações rápidas sem quebrar clientes existentes.
