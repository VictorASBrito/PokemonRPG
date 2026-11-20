# Pokémon RPG — Diário de desenvolvimento e transferência entre chats

Este arquivo registra **eventos verificáveis**, decisões e pendências. Não substitui commits Git, migrações, backups ou testes. Sua finalidade é impedir perda de contexto quando uma conversa atinge o limite.

## Como registrar cada etapa

Copie este modelo ao concluir uma mudança:

```markdown
### AAAA-MM-DD — Título da etapa
- **Objetivo:** ...
- **Status:** CONCLUÍDO E TESTADO | DOCUMENTADO (NÃO TESTADO) | PARCIAL | BLOQUEADO
- **Branch/commit:** ...
- **Arquivos modificados:** ...
- **Esquema/migrations:** ... (ou nenhuma)
- **Decisões tomadas:** ...
- **Testes executados e resultados:** comando → passou/falhou/não executado
- **Riscos/pendências:** ...
- **Próxima ação:** ...
```

## Histórico recente

### 2026-10-23 — Etapa 06: atribuição do encontro à Box
- **Objetivo:** concluir fluxo de encontro → visualização → atribuição manual pelo mestre.
- **Status:** IMPLEMENTADO; TESTES FLASK/POSGRESQL PENDENTES.
- **Código:** `app/services/capturaveis_service.py` — serviço transacional `atribuir_capturavel_box`, com verificação de Box cheia, mesmo gênero, natureza, forma e Shiny, PV pelo nível do destinatário, histórico e reordenação em duas fases; helper de reordenação compartilhado com remoção. `app/routes/capturas.py` — nova rota POST protegida e token; `templates/capturas/mestre.html` — seletor do destinatário em cada card; `static/css/capturaveis.css` — estilos do formulário.
- **Testes novos:** `tests/test_capturaveis_atribuicao.py`: transferência, preservação de dados, histórico, dupla atribuição, Box cheia, destino inválido e usuário desativado, destinatário diferente de quem encontrou, remoção no meio, sequência de slots, acesso de jogador e token CSRF. Nenhum teste marcado como passado sem execução.
- **Documentação:** `docs/CAPTURAVEIS.md`, `docs/CONTINUIDADE_PROJETO.md` e `docs/DIARIO_DESENVOLVIMENTO.md`.
- **Migrations:** nenhuma; reutiliza a tabela `pokemons_capturaveis` existente.
- **Validação neste ambiente:** compilação dos arquivos Python alterados e parse Jinja de `templates/capturas/mestre.html` passaram. Testes Flask integrados não executados porque as dependências Flask e Flask-SQLAlchemy não estão instaladas aqui.
- **Próxima ação:** executar `python -m pytest -q tests/test_capturaveis_campo.py tests/test_capturaveis_atribuicao.py` e validar uma atribuição real para a Box; depois avançar para captura opcional ou batalha.

### 2026-10-23 — Correção de remoção/reordenação de capturáveis (Etapa 05.3)
- **Motivo:** a remoção com vários Pokémon no campo produziu `psycopg.errors.UniqueViolation` na constraint `campanha_ordem_capturavel` (ex.: posição 9).
- **Causa:** o código atribuía posições consecutivas aos sobreviventes num único flush, enquanto posições antigas ainda estavam ocupadas. A constraint UNIQUE é imediata; a ordem dos UPDATEs não é garantida.
- **Alteração:** ao remover, todos os capturáveis ativos sobreviventes têm sua posição definida como `NULL` e a remoção é registrada em um primeiro `flush`; em um segundo passo, as posições `1..N` são atribuídas e gravadas, tudo na mesma transação. A criação e a remoção também bloqueiam a linha da campanha (`SELECT ... FOR UPDATE`) no PostgreSQL para serializar alterações de uma mesma campanha.
- **Testes adicionados:** remoção do quinto entre dez com preservação da ordem e inclusão posterior; remoção do primeiro e do último entre quatro; conferência dos registros do histórico e das posições.
- **Arquivos:** `app/services/capturaveis_service.py`, `tests/test_capturaveis_campo.py`, `docs/CONTINUIDADE_PROJETO.md` e `docs/DIARIO_DESENVOLVIMENTO.md`.
- **Migrations:** nenhuma; schema já permite `ordem = NULL` e possui constraint UNIQUE por campanha e posição.
- **Validação local:** sintaxe Python e teste isolado de duas fases com constraint UNIQUE no SQLite; testes Flask completos dependem do ambiente do usuário.
- **Próxima ação:** executar `python -m pytest -q tests/test_capturaveis_campo.py`, remover capturável em posição intermediária na interface e confirmar que a lista fica sequencial sem perda de dados.


### 2026-10-23 — Correção do histórico de capturáveis (Etapa 05.1)
- **Motivo:** usuário executou `python -m pytest -q tests/test_capturaveis_campo.py`: `2 failed, 1 passed in 3.93s`. Falhas na criação e remoção por `TypeError: 'entidade_id' is an invalid keyword argument for HistoricoAlteracao`.
- **Causa:** `app/services/capturaveis_service.py` usava campos de auditoria inexistentes (`entidade_id`, `detalhes`). O modelo real em `app/models/db/audit.py` usa `registro_id`, `dados_anteriores`, `dados_novos`.
- **Alteração:** ambos os pontos de auditoria de capturáveis passam a usar os campos reais, com instantâneos de criação (`dados_novos`) e remoção (`dados_anteriores`). Acrescentadas asserções de histórico no teste existente para prevenir regressão.
- **Arquivos atualizados:** `app/services/capturaveis_service.py`, `tests/test_capturaveis_campo.py`, `docs/DIARIO_DESENVOLVIMENTO.md`, `docs/CONTINUIDADE_PROJETO.md`.
- **Banco de dados:** nenhuma migration e nenhuma alteração direta nos dados; mantém a migration `6f355a4d5b2e` da Etapa 05.
- **Validação:** `python -m py_compile` passou; testes Flask/SQLAlchemy não executados neste ambiente porque o módulo Flask não está disponível. Os testes da nova versão precisam ser rodados pelo usuário.
- **Próxima ação:** aplicar pacote incremental, executar `python -m pytest -q tests/test_capturaveis_campo.py`; conferir inclusão, visualização e remoção de capturáveis em navegador.

### 2026-10-23 — Auditoria de integridade do catálogo de itens (somente leitura)
- **Objetivo:** preparar o diagnóstico de dados reais antes de corrigir itens em massa.
- **Status:** FERRAMENTA IMPLEMENTADA E TESTADA ISOLADAMENTE; EXECUÇÃO NO POSTGRESQL REAL PENDENTE.
- **Base:** ZIP atualizado enviado pelo usuário após confirmação de `9 passed in 10.86s` nos testes da etapa anterior.
- **Arquivos modificados:** `app/commands/catalogo.py`, `app/services/auditoria_itens_service.py` (novo), `tests/test_auditoria_itens.py` (novo), `docs/CONTINUIDADE_PROJETO.md`, `docs/DIARIO_DESENVOLVIMENTO.md`, `docs/ITENS_INVENTARIO.md`, `docs/AGENTS.md`.
- **Migrations:** nenhuma; nenhum registro de produção alterado.
- **Decisões:** comando `flask --app app.py catalogo auditar-itens` estritamente de leitura; severidades **ERRO** e **AVISO**; reporte de totais por categoria, códigos equivalentes, possíveis nomes repetidos, preços, JSON de efeitos e vínculos internos; sem normalizar dados do usuário ou restaurar regras desativadas de Ankar.
- **Testes executados:** 8 cenários isolados em Python para o serviço de auditoria (passaram); compilação de sintaxe Python (passou). **Testes de integração pytest ainda NÃO executados neste ambiente**, devido à ausência das dependências Flask/SQLAlchemy e impossibilidade de instalação. Foram adicionados 6 cenários automatizados para execução na máquina do usuário.
- **Próxima ação:** rodar `python -m pytest -q tests/test_itens_inventario.py tests/test_auditoria_itens.py`, depois `flask --app app.py catalogo auditar-itens --todos` e `flask --app app.py inventario verificar`. Analisar os resultados antes de qualquer edição de registros. Comparação completa com itens do manual v2.5/Ankar continua pendente.

### 2026-10-23 — Confirmação dos testes da correção do cadastro de itens
- **Status:** VALIDAÇÃO DE TESTES CONFIRMADA PELO USUÁRIO (`9 passed in 10.86s`).
- **Fonte:** mensagem do usuário após receber a correção. Esta execução não ocorreu no ambiente de análise e não comprova, por si só, a interface manual ou os dados de produção.
- **Próxima ação:** iniciar auditoria de itens, mantendo íntegro o banco existente.

## Histórico recuperado

### 2026-10-23 — Validação de criação e edição de itens (correção incremental)
- **Objetivo:** iniciar a revisão do catálogo de itens, com foco em validação confiável e manutenção do estado do formulário ao corrigir erros.
- **Status:** PARCIAL — CÓDIGO IMPLEMENTADO; TESTES DE INTEGRAÇÃO BLOQUEADOS.
- **Base:** ZIP atualizado enviado pelo usuário com a documentação reunida em `docs/`.
- **Arquivos modificados:** `app/services/item_admin_service.py`, `app/routes/catalogo_admin.py`, `tests/test_itens_inventario.py`, `docs/CONTINUIDADE_PROJETO.md`, `docs/DIARIO_DESENVOLVIMENTO.md`, `docs/ITENS_INVENTARIO.md`, `docs/AGENTS.md`.
- **Esquema/migrations:** nenhuma alteração.
- **Alterações:** (1) preço inválido/decimal deixa de ser silenciosamente transformado em zero; preço máximo do formulário passa a ser verificado no servidor; (2) remoção de todos os efeitos é preservada no formulário de edição mesmo quando outro campo falha na validação.
- **Testes executados:** 7 casos isolados da função de preço (passaram); `python -m compileall` dos arquivos Python modificados (passou); `node --check static/js/itens-admin.js` (passou); tentativa `pytest -q tests/test_itens_inventario.py -x` (bloqueada por ausência de `flask`); tentativa de instalar dependências (bloqueada por indisponibilidade de rede).
- **Testes acrescentados, não executados:** regressão de preços inválidos e manutenção da remoção de efeitos após falha de validação.
- **Banco/produção:** nenhum banco real foi conectado ou alterado; sem confirmação de execução no navegador.
- **Próxima ação:** instalar dependências na máquina de desenvolvimento, executar os testes de integração e validar manualmente criação/edição/upload; obter erro real do usuário se persistir; então iniciar auditoria do catálogo PostgreSQL.

### 2026-10-23 — Introdução da documentação de continuidade
- **Objetivo:** reconstruir contexto técnico a partir do código fornecido e do resumo de conversa anterior; manter um prompt mestre dentro do repositório.
- **Status:** CONCLUÍDO (DOCUMENTAÇÃO); FUNCIONALIDADES NOVAS NÃO IMPLEMENTADAS.
- **Branch/commit de origem:** `feature/att-frontend` / `9517d8a` (ZIP fornecido pelo usuário).
- **Arquivos introduzidos:** `AGENTS.md`, `docs/CONTINUIDADE_PROJETO.md`, `docs/DIARIO_DESENVOLVIMENTO.md`.
- **Esquema/migrations:** nenhuma alteração.
- **Principais descobertas:** Flask/PostgreSQL/Jinja; nível compartilhado; cadastro de itens existente; geração e combate reservados; quatro perfis de acesso; Box única com 100 vagas.
- **Validação:** leitura estática da estrutura, documentação, rotas, serviços, modelos e migrations. Tentativa de coletar testes bloqueada porque Flask não está instalado no ambiente de inspeção. Não houve acesso ao banco real.
- **Proteção de dados:** o pacote de aplicação recomendado contém somente os novos documentos; não inclui `.env`, Git, backups ou uploads de usuário.
- **Pendências:** identificar/reproduzir eventual problema real no cadastro de itens; auditar dados existentes; planejar geração visual/atribuição; implementar painel compartilhado até 16 times.
- **Próxima ação:** examinar o defeito específico do formulário de cadastro de itens na instalação atual, com os dados e erros observados pelo usuário, antes de editar lógica existente.

### 2026-10-23 — Últimas mudanças preexistentes identificadas no repositório
- **Status:** HISTÓRICO RECUPERADO, NÃO VALIDADO EM EXECUÇÃO.
- **Commits recentes:** `9517d8a` — ajustes de inventário; `13ad161` — atualização na mochila; `7ab5a6e` — ajustes na tela de movimentos; `8d6438b` — seletores visuais e catálogos; `0bbe90b` — permissões de usuário.
- **Atenção:** a árvore de trabalho do ZIP inclui uma alteração local não commitada em arquivo JSON de jogador; não descartar ou sobrescrever.
- **Última documentação visual associada:** `ALINHAMENTO_INVENTARIO_UI2.md`.

## Quadro de trabalho atual

| Área | Estado | Próxima providência |
|---|---|---|
| Autenticação, ficha, Pokémon, equipe, Box, inventário | Implementado no código; produção não verificada nesta revisão | Evitar regressões |
| Criar item no catálogo | Código existe; defeito alegado ainda não reproduzido | Diagnóstico e correção pontual |
| Auditoria do catálogo de itens | Planejado | Validar dados após correção do cadastro |
| Gerador visual com natureza/sexo e atribuição pelo mestre | Planejado; serviço placeholder | Planejar integração ao modelo Pokémon e à Box |
| Campo compartilhado com até 16 times | Planejado; rota/serviço placeholder | Projetar arena e sincronização |
| Atualização de documentação a cada etapa | Procedimento estabelecido | Revisar ao terminar cada implementação |

### 2026-10-23 — Identificação e reparo controlado de naturezas cadastradas como itens
- **Objetivo:** responder aos avisos da auditoria sem editar ou reclassificar indiscriminadamente o inventário já consistente.
- **Status:** IMPLEMENTADO NO CÓDIGO; TESTES PUROS PASSARAM; REPARO NO POSTGRESQL DEPENDE DE SIMULAÇÃO E AUTORIZAÇÃO EXPLÍCITA DO MESTRE.
- **Resultado informado pelo usuário:** `inventario verificar`: 110 registros, 456 unidades, 48 itens equipados; consistência confirmada. Auditoria de itens: avisos `importado-ficha-*` sem categoria, sem erros informados na saída enviada.
- **Causa encontrada:** 49 campos `item` preenchidos no arquivo JSON congelado das fichas são idênticos às naturezas dos Pokémon; há 21 naturezas distintas representadas nesses campos. São dados de origem, não consulta direta ao banco.
- **Arquivos alterados:** `app/commands/planilhas_jogadores.py`, `app/commands/catalogo.py`, novo `app/services/reparo_natureza_importada.py`, novo `tests/test_reparo_natureza_importada.py`, `docs/ITENS_INVENTARIO.md`, `docs/DIARIO_DESENVOLVIMENTO.md`, `docs/CONTINUIDADE_PROJETO.md`.
- **Migrações:** nenhuma. **Dados do PostgreSQL:** nenhum acesso e nenhuma alteração no ambiente de preparação.
- **Comportamento:** importador ignora valores de item iguais à natureza; novo comando `catalogo revisar-naturezas-importadas` apenas simula por padrão. `--aplicar` exige critérios conservadores e desvincula exclusivamente `Pokemon.item_equipado_id` suspeito da campanha Ankar, com histórico; nunca apaga ou classifica itens.
- **Testes:** 3 testes de regras puras passaram em execução isolada; `compileall` passou. Testes Flask/SQLite e PostgreSQL ainda não rodaram no ambiente de preparação (Flask ausente). Repetir testes na máquina do mestre.
- **Pendências:** revisar o resultado da simulação antes de `--aplicar`, registrar contagem de vínculos ajustados, validar novamente o inventário e categorizar itens genuínos após avaliação. A auditoria continuará exibindo avisos dos itens legados sem categoria.
- **Próxima ação:** solicitar saída de `flask --app app.py catalogo revisar-naturezas-importadas` e resultados de testes; só então avaliar a aplicação opcional e planejar categorização não destrutiva dos restantes.


## Atualização — Capturáveis em campo

- Implementada a primeira versão do módulo de capturáveis em campo.
- O mestre pode registrar até 15 Pokémon capturáveis por campanha.
- Cada registro guarda a forma do Pokémon e qual personagem o encontrou.
- A tela do jogador exibe nome, sprite e tipos dos Pokémon disponíveis.
- A tela do mestre permite adicionar e remover capturáveis, preparando a futura etapa de atribuição/captura.


### 2026-10-23 — Correção 05.2: identificador do seletor de Pokémon capturáveis
- **Problema relatado na tela do mestre:** ao selecionar espécie no autocomplete, o servidor retornava "Selecione uma espécie válida no catálogo." mesmo após a migração e a correção do histórico.
- **Causa confirmada no código:** o endpoint `/api/catalogo/formas` fornecia apenas `valor` (nome da forma); o seletor compartilhado gravava `valor` no input oculto `forma_id`; o serviço esperava UUID, portanto rejeitava nomes como `Bulbasaur`.
- **Correção:** o autocomplete passa a incluir `id` com UUID da forma, preservando `valor` como nome para não quebrar outros formulários. O JavaScript utiliza `id` no campo oculto dos Pokémon, e continua utilizando `valor` para itens. No backend, o serviço reconhece o formato legado somente quando `forma_id` e `forma_nome` coincidem e a forma existe no catálogo.
- **Arquivos alterados:** `app/services/pokemon_db_service.py`, `app/services/capturaveis_service.py`, `static/js/autocomplete-catalogo.js`, `templates/capturas/mestre.html`, `tests/test_capturaveis_campo.py`, documentação.
- **Verificações no ambiente de preparação:** sintaxe Python e JS; testes integrados Flask pendentes de execução no ambiente local do usuário.
- **Banco:** nenhuma migration nova; nenhuma atualização direta de dados.
- **Próxima validação:** `python -m pytest -q tests/test_capturaveis_campo.py tests/test_seletores_visuais.py`, seguido de adição real pelo mestre e visualização no jogador.

### 2026-10-23 — Confirmação em uso real da correção 05.3

- **Status:** CONFIRMADO PELO USUÁRIO como funcionando corretamente após a correção do fluxo de remoção/reordenação dos capturáveis.
- **Evidência:** mensagem “Ótimo, está funcionando corretamente agora”, posterior à entrega 05.3; a tela de capturáveis já exibia Pokémon antes do reparo.
- **Mudanças nesta atualização:** somente documentação de continuidade; nenhum código, migration ou banco alterado neste chat.
- **Testes:** o usuário não compartilhou nesta mensagem a nova saída do pytest; não registrar contagem ou execução adicional.
- **Resultado consolidado:** seleção de espécie, exibição de capturáveis e remoção/reordenação considerados funcionais pelo mestre no ambiente local.
- **Próxima etapa:** transferência controlada de capturável para a Box de jogador por ação do mestre, com preservação da natureza/sexo já sorteados e proteção contra dupla atribuição.

## Etapa 07 — Painel compartilhado de batalha (23/10/2026)

Implementada a primeira versão do **campo compartilhado com até 16 times**. Jogadores colocam ou movem Pokémon da própria equipe; mestre administra todos, pode retirar Pokémon ou limpar a formação. Os times são compartilhados entre navegadores e atualizados por polling a cada 6 segundos. Cada Pokémon ocupa um único time; os registros são persistidos em `pokemons_em_campo`, com auditoria e validação de permissões no servidor. Enviar Pokémon à Box ou excluí-lo da ficha remove sua participação no campo. Arquivos de implementação, instalação, testes e limites: `docs/CAMPO_COMPARTILHADO.md`.

**Decisão expressa do usuário:** não implementar mecânica automática de tentativa de captura. A tentativa é narrativa entre os jogadores, e a atribuição efetiva é administrada pelo mestre.

**Validação:** sintaxe e integridade dos arquivos verificadas; testes integrados a executar no ambiente local. Nova migration `7a1f20d9c405` deve ser aplicada após backup. Próxima etapa opcional: evolução da interface de combate (HP, ações/turnos) e suporte a oponentes NPC independentes, conforme prioridade do usuário.

## 2026-10-25 — Etapa 08: Shiny automático e carrossel de captura

- **Nova regra em `capturaveis_service.py`:** o Shiny do encontro é sorteado em 1d100 na criação, comparando o resultado com `personagem.numeros_shiny` do encontrador (números de 1 a 100, não Pokédex). Campo `shiny` já existente é atualizado. O histórico da criação passa a conter o número sorteado e o resultado. A atribuição à Box preserva o resultado sem novo sorteio. A captura permanece narrativa/manual.
- **Mestre:** UI de capturáveis mais legível, com resumo, prévia do catálogo, filtros por nome/treinador/Shiny, cards reorganizados e destaque de Shiny. Mantidos os fluxos de adicionar, atribuir e remover.
- **Jogadores:** vitrine em carrossel com sprite grande, tipos, selo Shiny, setas, miniaturas, seletor direto e foco inicial nos Pokémon que a conta logada encontrou. Sem encontro próprio, inicia em todos. Progressive enhancement quando JS indisponível.
- **Testes adicionados:** `tests/test_capturaveis_shiny_carrossel.py` para regra, persistência, transferência e marcação HTML; `tests/test_capturaveis_ui.js` para lógica do carrossel. Os **2 testes JavaScript** executados localmente passaram. A suíte Flask/pytest permanece **pendente no ambiente do usuário** porque Flask e Flask-Migrate não estão disponíveis neste ambiente.
- **Sem migration**, sem alteração de estrutura do banco, sem alteração de Pokémon existentes, sem `.env` ou dados pessoais no pacote. Atualizada a documentação `CAPTURAVEIS.md` e o documento mestre.
- **Validação pendente:** executar a suíte Python, criar encontros reais com rolagens Shiny, verificar transferência à Box, testar troca de treinador no carrossel e conferir visual claro/escuro e mobile.


### Etapa 09 — Ajuste de qualidade de imagens Pokémon (implementação preparada)

- Identificada regra `image-rendering: pixelated` no carrossel, miniaturas, cards do mestre e Campo. Correção via CSS específico carregado por último.
- Preparado comando de sincronização HD opcional com execução somente mediante `--aplicar`; usa arquivos HOME de 512 px ou official-artwork 475 px, quando disponíveis, com verificação de PNG e preservação de URLs personalizadas.
- Adicionados testes automáticos para filtros de fonte, tamanho mínimo e simulação/aplicação sem rede.
- Pendente: testes integrados no ambiente do usuário e validação dos downloads reais no PostgreSQL e no navegador.

### 2026-10-25 — Etapa 09.1: Recuperação das imagens HD pendentes

- Recebido relatório real com **953 formas atualizadas e 110 não atualizadas**. O trecho explícito mostra 90 falhas (88 HTTP 404, 1 timeout, 1 resposta grande); as 20 não detalhadas estão no começo do catálogo, provavelmente Arceus e Aegislash.
- Criada tradução controlada dos códigos de formas para a PokéAPI, consulta adicional de `pokemon-form`, tentativa de HOME e official-artwork, retry de falhas transitórias, limite de JSON ampliado e atualização independente das URLs normal/Shiny.
- Criado `midia pokemon-hd-pendentes` e relatório JSON no diretório de HD para localizar exatamente o que ainda falta depois da execução.
- Atualizadas a documentação e a suíte de testes; sem migration, sem alterações diretas no PostgreSQL. O novo download precisa ser validado na máquina do usuário.


### Etapa 09.2 — Recuperação de oito artes finais (25/10/2026)
O mestre informou oito pendências após a rotina 09.1: `eevee-parceiro` (Shiny), `frillish` (ambas), `jellicent` (ambas), `minior-nucleo` (ambas), `pikachu-parceiro` (Shiny), `pyroar` (ambas), `zacian-heroi` (ambas), `zamazenta-heroi` (ambas). O sincronizador passou a testar fontes WebP 512px além de PNGs, inclui IDs exatos de cinco espécies problemáticas e oferece `--representativas` para opções explicitamente aproximadas de parceiro/núcleo Minior. Nenhuma migration foi criada; nenhuma alteração é aplicada sem `--aplicar`; resultado de integração PostgreSQL/download pendente de validação do usuário. Ver `docs/IMAGENS_POKEMON_HD.md`.


### 2026-10-26 — Correção 09.3: todos os encontros visíveis na abertura
- O mestre relatou que, ao abrir a vitrine dos jogadores, o filtro padrão **Meus encontrados** ocultava os Pokémon dos demais até trocar manualmente para **Todos os Pokémon**.
- Corrigido o JavaScript para iniciar com a lista completa e focar, se disponível, o primeiro Pokémon encontrado pelo próprio personagem. O HTML passa a selecionar **Todos os Pokémon** por padrão, inclusive antes da inicialização do script.
- Acrescentados testes de regressão em Node.js: encontro próprio fora da primeira posição; navegação global desde a abertura; filtro Meus e retorno a Todos; seleção direta de Pokémon de outro treinador; jogador sem encontro próprio. Ajustado teste Flask de marcação HTML.
- Não há migration ou mudanças na lógica de captura. A versão do JavaScript na URL foi alterada para evitar cache de navegador.


<!-- ANKAR-10A-1-1-2026-10-27 -->
### 2026-10-27 — Versão 10, Etapa 10A.1.1: auditoria somente leitura de Ankar
- **Objetivo:** auditar planilhas de rotas, cidades e pontos de interesse, preservando zonas e terrenos, antes de qualquer importação.
- **Status:** IMPLEMENTADO EM ZIP; 10 TESTES UNITÁRIOS PASSARAM; INSTALAÇÃO/INTEGRAÇÃO FLASK PENDENTES DE VALIDAÇÃO PELO MESTRE.
- **Branch/commit-base:** `main` = `feature/att-frontend`, commit `871cfaefbb1b6c59a0b001d1f9fa172d38cb1529` (27/10/2026). GitHub usado apenas para leitura.
- **Arquivos:** `app/services/auditoria_ankar_service.py`, `app/commands/ankar.py`, `app/commands/__init__.py`, `app/__init__.py`, `requirements.txt`, `tests/test_auditoria_ankar.py`, `docs/AUDITORIA_PLANILHAS_ANKAR.md`, `docs/RELATORIO_AUDITORIA_ANKAR_2026-10-27.txt`, `scripts/aplicar_documentacao_10a1.py`, documentação de continuidade/diário (acréscimos preservando conteúdo histórico).
- **Esquema/migrations:** nenhuma. Sem escrita em PostgreSQL, sem modificação de XLSX, sem importação de encontros.
- **Leitura exploratória real:** 120 abas, 352 tabelas, 2.683 entradas, 313 erros e 626 avisos, conforme relatório. `x`, datas Excel, sobreposição d100 e `Random` não interpretados automaticamente.
- **Testes executados:** `PYTHONPATH=... python -m pytest -q tests/test_auditoria_ankar.py` → 10 passaram, 1 ignorado (Flask ausente no ambiente da execução). Compilação Python dos arquivos novos passou. CLI real no aplicativo e PostgreSQL não testados aqui.
- **Riscos/pendências:** validar integração Flask e arquivos reais no computador do mestre; discutir correções da planilha sem sobrescrever originais; decidir semântica de `x` e marcadores ambíguos. O relatório pode apontar lacunas aparentes devido a d100 inválidos.
- **Próxima ação:** instalar ZIP incremental, instalar dependências, executar testes e comando, obter feedback local; somente então prosseguir para armazenamento validado 10A.1.2.


<!-- ATLAS_ANKAR_V10A2 -->
### 2026-10-28 — Etapa 10A.2: Atlas visual de Ankar
- **Objetivo:** disponibilizar rotas, cidades, pontos de interesse, habitats, terrenos, acessos e Pokémon no site antes de implementar funções.
- **Status:** IMPLEMENTADO EM PACOTE INCREMENTAL; VALIDAÇÃO FLASK E NAVEGADOR PENDENTES.
- **Base:** commit `871cfae` (27/10/2026), compatível com a instalação da etapa 10A.1.1.
- **Dados:** 73 rotas, 26 cidades, 20 pontos de interesse; 352 tabelas e 2.683 linhas de encontros extraídas das planilhas fornecidas nesta conversa.
- **Arquivos:** atlas JSON, leitor XLSX, serviço, blueprint, templates, CSS, JS, instalador aditivo, testes e documentação especializada.
- **Decisões:** somente leitura, tela do mestre; sem mecanismos de encontro/captura. Recuperar interpretação visual de datas do Excel sem substituir o original; marcador `x` mantém semântica não confirmada.
- **Migrations:** nenhuma. **PostgreSQL:** nenhuma escrita. **GitHub:** nenhuma alteração.
- **Testes:** registrar aqui o resultado executado localmente após instalar as dependências.
- **Próximo:** validar telas, revisar exceções de dados e planejar a função posterior com o mestre.


<!-- ATLAS_ANKAR_V10A2_1_UTF8 -->
### 2026-10-28 — Etapa 10A.2.1: Ajuste UTF-8 em teste de regressão
- **Objetivo:** corrigir a falha `UnicodeDecodeError: cp1252` em `test_instalador_e_idempotente_e_nao_altera_jogador` no Windows.
- **Status:** PATCH PREPARADO; reexecução Windows pendente.
- **Alterações:** `tests/test_atlas_ankar.py` usa `read_text(encoding='utf-8')`; documentação de correção em `docs/CORRECAO_UTF8_ATLAS_ANKAR_10A2_1.md`.
- **Resultado anterior informado pelo usuário:** `9 passed, 1 failed in 3.01s` antes da correção.
- **Migrations:** nenhuma. **PostgreSQL:** nenhuma alteração. **GitHub:** nenhuma alteração.
- **Próximo:** `python -m pytest -q tests/test_atlas_ankar.py tests/test_atlas_ankar_flask.py` no Windows e conferir navegação visual.

<!-- ANKAR_10A3_REVISAO_VISUAL -->
### 2026-10-28 — Etapa 10A.3: mapa interativo e revisão visual
- **Status:** IMPLEMENTAÇÃO INCREMENTAL, TESTES ISOLADOS PASSARAM; VALIDAÇÃO FLASK/LOCAL PENDENTE.
- **Objetivo:** aproveitar o mapa original sem reformular a experiência dos jogadores em mobile/tablet/desktop.
- **Arquivos:** JSON com 119 marcadores, JPG original, serviço/rota Atlas, índice/detalhe, CSS/JS Atlas, testes e documentação.
- **Preservação:** nenhuma tela do jogador, CSS global, banco, `.env`, uploads ou planilha original modificados. Sem migrations.
- **Validações locais:** 6 testes pytest, sintaxe Node, compilação Python e interações Chromium nas larguras 390/820/1440 px. Sem testes integrados Flask neste ambiente.
- **Próxima ação:** testar no servidor real do mestre, ajustar eventuais coordenadas e revisar capturas das telas existentes antes de mudanças globais.

<!-- ATLAS_ANKAR_V10A4 -->
### 2026-10-28 — Etapa 10A.4: Atlas compacto e geração de capturáveis
- Mapa inteiro visível à esquerda com filtros e seleção à direita no desktop; responsivo em mobile/tablet, sem alteração nas demais páginas.
- Descrição narrativa abreviada na ficha, com conteúdo integral expansível em parágrafos; habitats, acessos e d100 preservados.
- Tabelas de Pokémon em cards com artes do catálogo. `x` indica sem encontro e não gera Pokémon.
- Com autorização de mestre e confirmação, o card escolhe treinador e delega ao serviço `criar_capturavel_campo` atual (natureza, sexo, Shiny, limite 15, histórico).
- Criada rota POST do atlas com CSRF e validação da entrada original, sem mutation de planilhas.
- Sem migration. Testes Python/Flask e revisão final no navegador do usuário pendentes de execução local.
- Próximo passo: validar navegação e geração real de um encontro; depois analisar espécies sem correspondência entre planilha e catálogo.



<!-- ATLAS_ANKAR_V10A4_1 -->
### Etapa 10A.4.1 — Compatibilidade da ficha do Atlas (28/10/2026)
- **Problema:** o teste `test_template_detalhe_aponta_para_mapa_sem_alterar_encontros` da Etapa 10A.3 renderizava `templates/regiao/detalhe.html` diretamente e não passava `formas`. A atualização 10A.4 introduziu `formas.get(...)` e causava `jinja2.exceptions.UndefinedError`, mesmo com o endpoint real fornecendo o contexto.
- **Correção:** valores padrão seguros para as variáveis opcionais `formas`, `encontrados_por`, `descricao_paragrafos` e `atlas_csrf`, apenas quando omitidas ou nulas. A página real permanece inalterada quando a rota fornece esses valores.
- **Arquivos:** `templates/regiao/detalhe.html`, `tests/test_atlas_10a4_1_template.py`, script e documentação desta correção.
- **Escopo:** sem migrations, alteração no PostgreSQL, mudanças nos encontros, imagens, regras de acesso ou planilhas.
- **Validação local do pacote:** testes unitários Jinja sem Flask; reexecutar a suíte Flask completa na máquina da campanha.
- **Próxima ação:** verificar a geração Atlas → Capturáveis com o mestre no ambiente PostgreSQL e revisar a usabilidade da interface.


<!-- ENTRADA_PERSONAGENS_10B1 -->
### 2026-10-28 — Etapa 10B.1: Seleção visual de personagens
- Tela de entrada com nove slots em círculo e acesso coringa tradicional.
- Login visual restrito a nove contas `jogador` explicitamente configuradas em `data/entrada_personagens.json`; mestre, administrador e tester nunca são aceitos.
- Rotas: GET `/login`, GET `/login/coringa`, POST `/login/personagem/<numero>`.
- Sessões existentes e login tradicional preservados; CSRF na seleção direta.
- Configurar contas com `scripts/configurar_entrada_personagens.py`, documentado em `docs/ENTRADA_VISUAL_ANKAR.md`.
- Risco aceito: entrada sem senha permite que qualquer visitante escolha um personagem visível; exigir controle de acesso externo caso o site seja público.
- Nenhuma migration ou importação no PostgreSQL.

<!-- ENTRADA_PERSONAGENS_10B2 -->
### 2026-10-28 — Etapa 10B.2: revisão visual da seleção circular
- **Objetivo:** manter as nove sprites inteiras e círculos iguais; trocar estrela por Pokébola e nome Coringa por Mestre; simplificar textos.
- **Arquivos:** `templates/entrada_personagens.html`, `static/css/entrada-personagens.css`, `tests/test_entrada_10b2_visual.py`, `scripts/registrar_entrada_10b2.py`.
- **Autenticação:** inalterada. Slot Mestre continua encaminhando ao formulário de usuário/senha pela rota existente. Ordem e vínculos atuais dos personagens preservados.
- **Banco/migrations:** nenhuma alteração.
- **Teste local:** verificação da renderização isolada e regressão de estrutura; conferir na instalação real.


<!-- FICHAS_POR_URL_10B3 -->
### 2026-10-28 — Etapa 10B.3: Fichas independentes por URL
- Cada personagem configurado possui URL estável `/p/<login>/`, por exemplo `/p/lucas/jogador/dashboard`.
- WSGI ajusta SCRIPT_NAME/PATH_INFO: `url_for` preserva contexto em links, formulários e arquivos estáticos.
- Cookies Flask separados por jogador (nome e caminho) preservam o login de Mestre e outras abas.
- Cada requisição revalida conta, personagem e campanha no PostgreSQL; apenas nove contas jogador configuradas.
- Autorização limitada aos endpoints do jogador. Acesso administrativo permanece fora de `/p/<login>/`.
- GET `/selecionar` mostra a escolha mesmo que haja login Mestre em outra aba.
- Acesso por URL é sem senha, inclusive para ações de jogador: compartilhar links concede acesso à ficha.
- Sem migrations, sem mudanças em senhas, dados da campanha ou sprites.
- Testes: `python -m pytest -q tests/test_fichas_por_url_10b3.py tests/test_fichas_por_url_10b3_flask.py`.
- 10B.3.1: instalador independe da implementação do logout em auth.py, paths de teste normalizados no Windows.


<!-- LOGIN_MESTRE_10B3_2 -->
### 2026-10-28 — Etapa 10B.3.2: acesso Mestre, Teste e Victor
- Corrigido `templates/login.html`: POST explicitamente para `auth.login`, não `/login/coringa` (GET).
- `entrada_personagens.coringa` pode exibir o formulário mesmo com sessão administrativa ativa.
- `auth.login` só redireciona sessão existente em GET; em POST valida normalmente a nova senha e substitui sessão após sucesso.
- A correção preserva as nove fichas por URL, as contas e o PostgreSQL; sem migrations.
- Verificação: testes `tests/test_login_mestre_10b3_2.py` e `tests/test_login_mestre_10b3_2_flask.py`.


<!-- ITENS_ANKAR_10C1_2026_10_28 -->
### Etapa 10C.1 — revisão de Catálogo e Inventários (28/10/2026)
- Criado diagnóstico **somente leitura** do catálogo e dos inventários atuais com CSV de itens, quantidades, possíveis duplicatas e status de imagens: `scripts/revisar_itens_ankar_10c1.py`.
- Fonte histórica `app/seed/fichas_jogadores_ankar.json`: 109 linhas, 455 unidades, 77 grafias distintas (NÃO é o estado atual do PostgreSQL).
- Imagens são associadas a `Item.imagem_url` uma única vez; os inventários reutilizam o cadastro. Não foram criadas imagens artificiais ou itens sem especificação.
- Normalizações são apenas sugestões para revisão; não fundir códigos, inventários nem equipamentos automaticamente.
- Etapa seguinte: revisar relatórios do PostgreSQL, aprovar grafias/categorias/imagens e especificar as distribuições por login e quantidade.
- Testes puros em `tests/test_revisao_itens_10c1.py`; sem migrations e sem escrita no PostgreSQL.

<!-- ANKAR_10C3_CATALOGO_20261028 -->
### 2026-10-28 — Etapa 10C.3: reconstrução controlada do catálogo de itens
- **Status:** pacote incremental preparado, testes isolados executados, testes Flask/PostgreSQL e aplicação pendentes de execução local e aprovação.
- **Mudanças:** plano de 77 códigos para 48 cadastros, vínculos de inventários, arte de itens do commit Imagens Itens 1, mapa estático e cura funcional (PV/status) com seleção de alvo.
- **Proteções:** simulação padrão, bloqueios contra dados diferentes, conflito de imagens e usuários de outras campanhas, backup JSON antes de aplicar, confirmação explícita; natureza Ingênuo com 1 unidade só pode ser descartada com flag específica.
- **Banco:** não alterado pela entrega; reconstrução destrutiva só com comando explícito após backup PostgreSQL; nenhuma migration.
- **Testes:** executar `python -m pytest -q tests/test_itens_10c3_puro.py tests/test_itens_10c3_flask.py` e testes de regressão reais.
- **Próximo:** revisar simulação, validar imagem de cada item, aplicar conscientemente e testar cura/condições + mapa.

<!-- INVENTARIO_USO_VISUAL_10C4 -->
### Etapa 10C.4 — Uso do item pela linha e escolha visual do Pokémon
- O botão **Usar** fica na linha do item, junto ao nome e quantidade; o painel direito apresenta descrição e transferência.
- Tratamentos de PV destacam Pokémon da equipe feridos; tratamentos de status destacam Pokémon afetados (mesmo com PV cheio). A seleção envia POST ao serviço terapêutico 10C.3, sem afrouxar validações.
- O **Mapa de Ankar** abre no diálogo estático pelo botão Usar e não é consumido.
- Equipar continua disponível em diálogo (equipe/Box), e o ajuste de quantidade fica apenas no gerenciamento do Mestre.
- PENDÊNCIA VISUAL: a área inferior de Adicionar item do Mestre pode aparecer cortada/compactada, especialmente o seletor de catálogo em viewport baixo. Revisar overflow e popup do autocomplete posteriormente.
- Consulte `docs/ETAPA_10C4_INVENTARIO_USO_VISUAL.md` para testes manuais. Sem migrations e sem alteração automática de inventários.

<!-- AVISOS_TOAST_10C4_1 -->
### Etapa 10C.4.1 — Notificacoes flutuantes de confirmacao
- Mensagens `flash()` do Flask (sucesso, erro, aviso e informacao) deixam de ocupar espaco dentro de `.conteudo` e passam a surgir em pequenos toasts na parte superior direita.
- Cada toast desaparece apos 1,5 segundo; passar o mouse ou focar o aviso pausa a contagem e o botao Fechar permite encerramento manual.
- A alteracao vale globalmente para mestre e jogadores (inventario, fichas, catalogos e demais telas que utilizam `templates/base.html`), sem alteracoes no banco.
- Arquivos: `scripts/instalar_avisos_toast_10c4_1.py`, `static/css/avisos-toast-10c4-1.css`, `static/js/avisos-toast-10c4-1.js`.
- Pendencia visual anterior mantida: autocomplete do catalogo/rodape da mochila do mestre pode ser cortado com altura reduzida; precisa de ajuste separado.



### 2026-11-20 — Etapa 10E.1.1: exibição do número nacional nos cartões Pokémon
- **Objetivo:** substituir `#—` pelo número nacional correto junto à categoria da forma no catálogo do Mestre.
- **Status:** IMPLEMENTADO EM BRANCH; testes automatizados do PR pendentes de verificação.
- **Branch:** `feature/10e1-numeros-cartoes-pokedex`, baseada em `main` após merge do PR #8 (10E.1).
- **Arquivos modificados:** serviço novo `app/services/numeracao_pokedex_service.py`; rota `app/routes/catalogo_admin.py`; template `templates/mestre/catalogo/pokemons.html`; regressões `tests/test_ordenacao_pokedex_10e1.py`; docs 10E.1, continuidade e diário.
- **Migrations/banco:** nenhuma. Nenhuma alteração a números de espécie armazenados, Pokémon existentes ou arquivos de dados; numeração apresentada calculada a partir da fonte original, em cache.
- **Decisões:** separar índice de 1.064 formas do número nacional de 898 espécies; Venusaur Mega compartilha #003 com Venusaur; Nidoran♀/#029 e Nidoran♂/#032 diferenciados pelo código original da forma, inclusive se a FK legada estiver incorreta; Pokémon criados pelo mestre respeitam número manual ou exibem `#—`.
- **Testes:** acrescentados testes para cálculo e HTML com banco SQLite de fixture; execução a confirmar via workflow do PR. PostgreSQL real não acessado.
- **Próxima ação:** validar workflow e revisão do PR; prosseguir 10E.2 com auditoria dos vínculos e números persistidos.


### 2026-11-20 — Etapa 10E.2.1: diagnóstico dos números e vínculos oficiais
- **Objetivo:** identificar, sem mutação, divergências entre a fonte da Pokédex, `EspeciePokemon`, `FormaPokemon` e vínculos com Pokémon de jogadores.
- **Status:** IMPLEMENTADO EM BRANCH; testes CI a verificar; auditoria PostgreSQL real ainda não executada.
- **Branch:** `feature/10e2-1-auditoria-pokedex`, criada da `main` após o PR #10.
- **Arquivos modificados:** serviço novo `app/services/auditoria_pokedex_service.py`; comando `app/commands/catalogo.py`; testes `tests/test_auditoria_pokedex_10e2_1.py`; CI `.github/workflows/test-auditoria-pokedex-10e2.yml`; `docs/ETAPA_10E2_1_AUDITORIA_POKEDEX.md`; plano de evoluções; continuidade e diário.
- **Esquema/migrations:** nenhuma. Só SELECT; sem writes/commits, `--aplicar` ou reimportação; sem ação nos registros de Pokémon existentes.
- **Decisão:** referência com números por espécie distinta, e não índice de forma. Detectar Nidoran♀ #029 e Nidoran♂ #032 por nome exato; diferenças nas ligações e números cadastrados são erros, NULL e formas ausentes são avisos. Ankar personalizada sem número é válida; colisões de número regional são avisos.
- **Testes escritos:** referência real, duplicatas na fonte, correção de Mega, Nidoran legado e impacto, número nacional divergente, índice de forma, formas ausentes, personalizadas e CLI texto/JSON sem alterações. CI configurado; resultado será indicado após a execução.
- **Riscos:** a primeira execução no banco histórico pode exibir muitos avisos por `numero=NULL`; isso não justifica mudança automática ou afirmação sobre o estado atual do servidor.
- **Próxima tarefa:** executar `flask --app app.py catalogo auditar-pokedex --json` no ambiente da campanha, revisar relatórios e preparar saneamento controlado antes do editor 10E.2.2.

- **Resultado CI verificado:** workflow `Auditoria da Pokédex - 10E.2.1`, execução 44816417525, job 136565811738: `18 passed in 5.28s` para `tests/test_auditoria_pokedex_10e2_1.py tests/test_ordenacao_pokedex_10e1.py tests/test_catalogo_admin.py` no commit de código/documentação `1413bcd`. Não equivale a um teste no PostgreSQL real de Ankar.

### 2026-11-20 — Etapa 10E.2.1.2: plano de saneamento controlado
- **Objetivo:** resolver a causa dos 2 erros/897 avisos da auditoria real com proteção contra alterações não aprovadas no PostgreSQL.
- **Status:** IMPLEMENTADO EM BRANCH; testes CI e aplicação no banco de campanha pendentes.
- **Branch:** `feature/10e2-1-2-saneamento-controlado` (base `main` após PR #11).
- **Arquivos:** `app/services/importacao/utils.py`, `app/services/importacao/catalogo_importer.py`, `app/services/saneamento_pokedex_service.py`, `app/commands/catalogo.py`, `tests/test_saneamento_pokedex_10e2_1_2.py`, `.github/workflows/test-saneamento-pokedex-10e2.yml`, `docs/ETAPA_10E2_1_2_SANEAMENTO_POKEDEX.md`, plano/continuidade/diário.
- **Dados confirmados no relatório:** fonte 898 espécies e 1.064 formas; PostgreSQL 897 espécies e 1.066 formas; 897 números NULL e ausência de Nidoran♂ como espécie própria; `nidoran-2` pertence erroneamente à fêmea; 2 formas extras intocadas.
- **Proteções:** simulação por padrão, assinatura SHA-256 do estado do catálogo, aplicação só com backup PostgreSQL previamente realizado/verificado e declaração explícita do mestre, bloqueios em alterações inesperadas, log por ajuste, verificação pós-mudança e commit único. Nenhum backup automático.
- **Migrations:** nenhuma; não cria colunas nem altera tabelas. Pokémon capturados não são regravados.
- **Testes:** novos testes do código do importador, simulação, assinatura divergente, bloqueio sem backup, implantação idempotente, histórico de mudanças e preservação de fichas; execução GitHub Actions a confirmar.
- **Próxima tarefa:** revisar PR e CI; mesclar após aprovação; executar simulação local e analisar assinatura; conferir backup antes de qualquer aplicação; após auditoria limpa iniciar editor 10E.2.2.

- **CI verificado no código da entrega:** commit `350ed716`, workflow `Saneamento controlado da Pokédex - 10E.2.1.2` (run 44819074574, job 136574937493), `26 passed in 14.03s`. Inclui importação repetida, simulação com 897 números NULL e duas formas extras, guardas de backup/assinatura, aprovação transacional, verificação posterior, idempotência, preservação de Pokémon e rollback após flush. Demais regressões do Campo, fichas de NPCs, ordenação e auditoria passaram; teste real em PostgreSQL ainda **não foi executado** pelo assistente.

### 2026-11-20 — Correção 10E.2.1.1: stdout Windows cp1252
- **Objetivo:** corrigir o traceback `UnicodeEncodeError` no comando `catalogo auditar-pokedex --json` relatado pelo mestre no PowerShell/Python 3.13 (`Nidoran♂`).
- **Status:** IMPLEMENTADO EM BRANCH; CI pendente de execução/verificação nesta entrada.
- **Branch:** `fix/10e2-1-auditoria-windows-encoding`, a partir da `main` com PR #11 já mesclado.
- **Arquivos:** `app/commands/catalogo.py`, `tests/test_auditoria_pokedex_10e2_1.py`, `docs/ETAPA_10E2_1_AUDITORIA_POKEDEX.md`, continuidade e diário.
- **Comportamento:** `--json` usa JSON ASCII escapado válido (`ensure_ascii=True`); texto usa `_texto_compativel_saida` para substituir somente caracteres incompatíveis com o `stdout` atual, sem perder acentos disponíveis.
- **Migrations:** nenhuma. Apenas serialização e impressão; não consulta adicional nem mutações em PostgreSQL.
- **Validação:** testes novos para `cp1252` e `json.loads`; esperar CI do PR. Ambiente Windows real ainda não foi testado pelo assistente.
- **Próximo:** após merge, repetir `flask --app app.py catalogo auditar-pokedex --json > auditoria-pokedex.json` no Windows e revisar o relatório.
- **Validação CI confirmada:** workflow `Auditoria da Pokédex - 10E.2.1` (execução 44817271422, job 136568715353), commit `25066e0`: `19 passed in 7.17s` para a auditoria e regressões de ordenação/catálogo. O teste simula `cp1252`, porém a execução automatizada foi Linux; ainda conferir manualmente no PowerShell do mestre.


### 2026-11-20 — Etapa 10E.2.2: cadastro e conferência de evoluções
- **Objetivo:** desenvolver o editor mestre de vínculos entre formas e conferir os primeiros requisitos no livro, PokéAPI e Pokémon Database.
- **Status:** IMPLEMENTADO EM BRANCH; CI e homologação PostgreSQL a verificar. Nenhuma evolução de jogador ativada.
- **Branch:** `feature/10e2-2-editor-relacoes-pokemon` criada sobre main após PR #12 e #13 mesclados.
- **Arquivos:** serviço `app/services/evolucoes_admin_service.py`; rotas `app/routes/catalogo_admin.py`; template novo `templates/mestre/catalogo/pokemon_relacoes.html`; links nas páginas `pokemon_form.html` e `pokemons.html`; referências `data/referencias/evolucoes_verificadas_10e2.json`; testes `tests/test_evolucoes_admin_10e2_2.py`; workflow `test-evolucoes-10e2-2.yml`; documentação `docs/ETAPA_10E2_2_RELACOES_POKEMON.md`, plano/continuidade/diário.
- **Fontes externas:** PokéAPI evolution-chain/1 (Bulbasaur), /2 (Charmander), /3 (Squirtle); Pokémon Database /evolution/level. Livro PKMRPG v2.5 cap. 9 p. 44 confirma Charmander nível 16, regras de nível, item, amizade, Mega temporária. Seis pares documentados com verificação cruzada.
- **Decisões:** relações permanentes são grafo acíclico; Mega/alternativa/regional são metadados distintos, sem arestas de retorno automáticas. Regras de Ankar seguem nível compartilhado e sem amizade numérica. O mestre aprova cada sugestão.
- **Segurança/migration:** perfis mestre, validação de IDs/tipos/ciclos/duplicados, histórico na inclusão/edição/desativação; sem migration, sem alteração de PostgreSQL de produção pelo assistente e sem alterações em Pokémon de jogadores.
- **Testes escritos:** autenticação, sugestões com aprovação explícita, histórico, edição, desativação, ciclos, duplicados, categoria de Mega, forma alternativa, vínculo regional, fontes inválidas e preservação de Pokémon. CI em workflow dedicado; resultado a registrar após execução.
- **Próximo:** checar CI, homologar tela no PostgreSQL Ankar e implementar visualização em árvore 10E.2.3 e revisão de outras cadeias de evolução.

- **CI verificado:** workflow `Editor de evoluções e formas - 10E.2.2`, execução 44821837943, job 136584377839, commit `4b8b20a3`: `27 passed in 11.83s` na suíte de relações, catálogo e Pokédex. Também passaram os workflows de NPCs, Campo, fichas, auditoria, ordenação e saneamento nessa revisão. Execução foi em SQLite/Linux; testes manuais no PostgreSQL real e homologação visual ainda pendentes.


### 2026-11-20 — Etapa 10E.2.3: visualização de árvore e novas cadeias revisadas
- **Objetivo:** permitir ao mestre visualizar a família toda, inclusive ramificações, e comparar requisitos de Eevee, pedras e trocas com o livro, PokéAPI e Pokémon Database.
- **Status:** IMPLEMENTADO EM BRANCH, validação GitHub Actions e revisão visual pendentes nesta entrada.
- **Branch:** `feature/10e2-3-arvore-evolutiva`, partindo da main após merge do PR #14.
- **Arquivos:** serviço de árvore `app/services/arvore_evolutiva_service.py`, rota mestre GET em `app/routes/catalogo_admin.py`, template `pokemon_arvore.html`, CSS `arvore-evolutiva.css`, editor `pokemon_relacoes.html`, sugestões `evolucoes_revisadas_10e2_3.json`, modificações em `evolucoes_admin_service.py`, testes `test_arvore_evolutiva_10e2_3.py`, CI dedicado e docs da etapa, plano/continuidade/diário.
- **Regras:** árvore usa só `EvolucaoPokemon` ATIVAS e permanentes; Megas, alternativas e regionais são listadas separadas. Nós ordenados topologicamente, vários pais permitidos, defesa contra ciclos e limite 120. Sem automação de mudança de forma.
- **Fontes externas:** PokéAPI evolution-chain/67 (Eevee), /10 (Pikachu) e documentação v2; PokémonDB stone/trade/pokedex Eevee. PDF fornecido p. impressas 44–45, 59–60. Há divergências relevantes; não preencher requisitos ignorando diferenças.
- **Novas sugestões:** cinco por pedra em Eevee e duas por pedra em Pikachu/Vulpix podem ser aprovadas individualmente com alertas. Espeon, Umbreon, Sylveon, Porygon→Porygon2 e Porygon2→Porygon-Z ficam pendentes de decisão narrativa, bloqueadas mesmo via POST direto.
- **Regra crítica do livro:** materiais exigem amizade máxima, mecânica não suportada em Ankar. A divergência é explicitamente exibida; não se altera o nível do Pokémon nem amizade/XP. Nenhum Pokémon de jogador modificado; sem migration.
- **Testes novos:** estágios e convergências, ciclos legados, relações especiais, sugestões aprováveis/pendentes, permissões e preservação de instância da Box. CI em `test-arvore-evolutiva-10e2-3.yml` a confirmar.
- **Próximo:** validar workflow, revisar PR, integrar e testar navegação no PostgreSQL da campanha; depois 10E.3 serviço de elegibilidade evolutiva sob confirmação do mestre.

- **Validação CI confirmada para código da etapa:** GitHub Actions `Árvore evolutiva e referências revisadas - 10E.2.3`, run 44824602928, job 136593869013, commit `90548b17`: **34 passed in 12.53s** (testes novos, editor 10E.2.2, catálogo, auditoria e ordenação da Pokédex). Também passaram os workflows de auditoria 10E.2.1, saneamento 10E.2.1.2, sequência da Pokédex e Campo na mesma revisão; demais regressões devem ser verificadas por conclusão individual. Testes automatizados executados em SQLite/Linux, não no PostgreSQL real do mestre.


### 2026-11-20 — Etapa 10E.2.4: árvores completas por nível/pedra e mestre
- **Objetivo:** cumprir nova regra do mestre de gerar automaticamente árvores das 898 espécies oficiais; incluir relação especial visual, porém exigir liberação por Pokémon para amizade, troca, itens específicos e condições especiais.
- **Status:** IMPLEMENTADO EM BRANCH; CI e homologação PostgreSQL pendentes de validação.
- **Branch:** `feature/10e2-4-pokedex-evolutiva-completa` criada a partir da main após PR #15 mesclado.
- **Fonte:** PokeAPI/pokeapi csv oficiais (pokemon_species, pokemon_evolution, items), conferência Pokémon Database e manual PKMRPG v2.5 cap. 9 e 16. **430 arcos:** 297 por nível, 43 por pedra simples, 90 bloqueados para liberação individual do mestre. Inclui 7 casos de formas regionais/forma de Vivillon classificados especificamente.
- **Arquivos:** `data/referencias/pokedex_evolucoes_898_10e2_4.json` (fonte versionada), `app/services/importacao_evolucoes_service.py` (prévia, hash, idempotência, aplicação/histórico, guarda de autorização), `app/commands/catalogo.py`, `app/routes/catalogo_admin.py`, `templates/mestre/catalogo/gerar_arvores_pokemon.html`, `templates/mestre/catalogo/pokemons.html`, `app/services/arvore_evolutiva_service.py`, `app/services/evolucoes_admin_service.py`, testes, workflow, docs.
- **Fluxo:** mestre entra no catálogo → Gerar árvores evolutivas, revisa quantidade/simulação/assinatura, confirma backup PostgreSQL real e digita `GERAR-ARVORES-ANKAR`. CLI equivalente com `flask --app app.py catalogo gerar-arvores-pokemon` e aplicação explícita; nenhuma importação em startup.
- **Regra:** cadastro de arcos simples sem autorização por Pokémon; arcos especiais precisam da liberação INDIVIDUAL do mestre na etapa 10E.3; a árvore sinaliza a reserva. Nível é sempre o do personagem. Cadastro da árvore NUNCA evolui Pokémon existentes.
- **Compatibilidade:** não sobrescrever/reativar relações anteriores, proteger requisitos de mestre ao editar, preservar dados dos jogadores e formas regionais, evitar ciclos de grafo, histórico das relações e transação única. Nenhuma migration.
- **Divergência do manual:** qualquer material exigia amizade 100; Ankar não tem amizade numérica. A decisão nova do mestre estabelece pedras comuns como evoluções regulares; itens especiais permanecem narrativos.
- **Testes:** `tests/test_importacao_evolucoes_10e2_4.py` + workflow `test-importacao-evolucoes-10e2-4.yml` cobrindo fonte, 430 registros, bloqueios, nível e pedras, mestre, idempotência, linhas regionais, preservação de Box, rollback e segurança web. Resultados CI pendentes nesta entrada.
- **Próximo:** verificar CI, revisar PR, realizar backup, aplicar importação na instalação e abrir árvore de Eevee; só depois avançar para a evolução individual 10E.3 com autorização por Pokémon.

- **CI verificado:** workflow `Pokédex evolutiva completa - 10E.2.4`, execução 44827192410, job 136602661588, commit `fd2eadca`: `42 passed in 23.37s`. Inclui teste de geração de 430 relações, 340 regulares, 90 bloqueadas, 430 históricos, preservação de Pokémon dos jogadores, idempotência, simulação, assinatura/backup, validação CSRF e rollback, além das regressões 10E.2.1–3 e catálogo. Rodou em SQLite/Linux; **não** equivale a teste PostgreSQL real. Os demais workflows (NPCs/Campo/Pokédex) devem ser conferidos no commit final após docs.


### 2026-11-20 — Etapa 10E.2.5: complementação evolutiva regional
- **Motivação:** mestre relatou ausência de árvores da maioria das formas regionais depois de executar 10E.2.4. Main atual já tinha PR #16 incorporado; auditoria direta dos códigos originais conferiu 38 formas (18 Alola, 18 Galar, 2 Darmanitan Galar), das quais apenas seis de Galar apareciam em alguma aresta.
- **Achado técnico:** primeira fonte só armazenava arcos por espécie. PokeAPI `pokemon_evolution.csv` diferencia variantes usando IDs de forma e `region_id`; essas arestas ficaram ausentes. Revisão via Pokémon Database confirmou pedras de gelo, Galarica, nível, troca, condições de noite/região.
- **Nova entrega:** branch `fix/10e2-5-evolucoes-regionais`, arquivo `evolucoes_regionais_10e2_5.json` com 17 ligações adicionais (8 automáticas pelo nível/pedra, 9 restritas ao mestre), serviço `importacao_evolucoes_service.py` com carregamento isolado e requisitos narrativos, CLI `completar-arvores-regionais`, rota administrativa em modo `regionais=1`, template compartilhado e link na Pokédex.
- **Proteções:** mesmo padrão da 10E.2.4: assinatura SHA256, simulação read-only, backup externo restaurável, autorização explícita, uma transação, histórico, idempotência e preservação de relações antigas e Pokémon capturados. Sem migration. Relações condicionais de Galar/Alola são marcadas para liberação individual na 10E.3.
- **Separações:** Darmanitan (Galar Zen) não é evolução, mas forma alternativa de combate (10E.4); não criar relação evolutiva artificial para ele. Aves lendárias de Galar e Stunfisk de Galar não evoluem. Nenhuma forma Hisui/Paldea na Pokédex de Ankar atual.
- **Arquivos e testes:** `docs/ETAPA_10E2_5_EVOLUCOES_REGIONAIS.md`, `tests/test_evolucoes_regionais_10e2_5.py`, `.github/workflows/test-evolucoes-regionais-10e2-5.yml`, mais os arquivos anteriores; CI e homologação PostgreSQL pendentes nesta entrada.
- **Próximos passos:** confirmar CI, revisar PR, aplicar complemento somente após backup e simulação no PostgreSQL, validar árvores de Vulpix/Geodude/Slowpoke de Galar, continuar 10E.3 e 10E.4.

- **CI validada:** workflow `Evoluções regionais 10E.2.5`, execução `44829302699`, job `136609875932`, commit `75d3164e`: **43 passed in 26.67s**. Testes regionais e regressões 10E.2.1/2/3/4 aprovados; outros 10 workflows de Campo, NPCs, saneamento e catálogo também concluíram com `success` no mesmo commit. Os testes são em SQLite/Linux; ainda falta a simulação e revisão do mestre no PostgreSQL real de Ankar. O PR #17 está aberto, mesclável, não mesclado automaticamente.


### 2026-11-20 — Etapa 10E.3.1: elegibilidade de evolução por Pokémon
- **Motivação:** importar as árvores não era suficiente para decidir se um Pokémon individual poderia evoluir. O mestre confirmou a aplicação do complemento regional no PostgreSQL.
- **Status:** implementado na branch `feature/10e3-1-consulta-elegibilidade`; CI e homologação visual no PostgreSQL a verificar nesta entrada.
- **Implementação:** `app/services/consulta_evolucao_service.py`, consulta a `EvolucaoPokemon` pela forma exata e à mochila do personagem, avaliação pelo nível compartilhado, validação conservadora de requerimento do mestre; `app/routes/pokemons.py` integra no fluxo já autorizado do jogador/mestre; painel no template `templates/jogador/pokemon.html` e CSS `static/css/pokemon.css`.
- **Estados:** requisito atendido, nível insuficiente, pedra ausente, depende do mestre. Não existe botão de evolução, nem consumo/alterações por GET. Formas regionais são separadas pelo UUID exato; Mega/reversíveis ficam de fora.
- **Cuidado:** aprovação editorial do catálogo não dá permissão para Pokémon individual; Espeon/Umbreon/Sylveon, Gallade (gênero), Slowpoke de Galar (item especial), Rattata de Alola (noite) e demais requisitos condicionais ficam sempre com mestre.
- **Bancos:** sem migration, sem alteração de PostgreSQL real pelo assistente, nenhuma atualização de ficha ou inventário. Testes em `tests/test_consulta_evolucao_10e3_1.py` e CI `test-elegibilidade-evolucao-10e3-1.yml` incluindo regressões das árvores. Consultar `docs/ETAPA_10E3_1_CONSULTA_ELEGIBILIDADE.md`.
- **Próximas etapas:** 10E.3.2 permissão persistida por Pokémon/relação; 10E.3.3 ação de evolução com confirmação; 10E.3.4 consumo transacional e recálculo de atributos/PV.

- **CI validada após correções dos auxiliares de teste:** workflow `Elegibilidade evolutiva por Pokémon - 10E.3.1`, execução 44831263885, job 136616499855, commit `5dfdb93e`: **64 passed in 41.61s** (consulta de elegibilidade, árvores regionais/nacionais, fichas/equipe, Box, inventário, catálogo e permissões). Os demais workflows do projeto presentes nessa revisão também concluíram com `success`. Testes rodaram com SQLite/Linux; homologação visual e consulta no PostgreSQL da campanha continuam pendentes, sem alteração de dados reais.
