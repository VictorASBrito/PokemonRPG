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
