# Pokémon RPG — Prompt mestre e contexto de continuidade

> **Fonte de verdade de contexto para os próximos chats e colaboradores.**  
> **Versão:** 1.2 — **Data da revisão:** 23/10/2026.  
> **Base examinada:** `PokemonRPG.zip`, ramo Git `feature/att-frontend`, commit `9517d8a` (23/10/2026).  
> **Escopo desta versão:** validação da correção anterior confirmada pelo usuário (9 testes passaram em 10,86 s); implantação de auditoria detalhada de catálogo **somente leitura**, com novos testes e documentação. A leitura do PostgreSQL real ainda depende da execução local.


## Etapa 10F.9 — Etiquetas de tipo e atributos calculados no modo normal (21/11/2026)

**Pedido:** aumentar as tags de tipo e corrigir letras comprimidas; aproximar os cartões de atributos normais dos valores de combate do modo expandido.

**Implementação:** branch `feat/dashboard-tipos-atributos-10f9`, baseada na main após merge do PR #39. `static/css/tipos.css` preserva a paleta por tipo e adota altura automática, mínimos 21–25px no dashboard, fonte de aproximadamente 11–12,5px, line-height 1,2 e ausência de sombra tipográfica. `templates/base.html` atualiza cache da folha comum. Os templates de jogador e NPC apresentam os seis totais calculados já disponíveis no contexto, com `Base X` abaixo de cada número; o título passa a Atributos. CSS do dashboard adota fonte de 1rem para os totais, rótulos/base menores e linhas mínimas de 52px. Cache e contratos de UI atualizados. Não recalcular atributos, alterar as ações, dados da campanha ou permissões; sem migration.

**Validação:** ampliar `tests/visual/test_dashboard_legibilidade_10f8.py` para testar igualdade entre totais e bases dos dois modos, limites das seis células, etiquetas de Pokémon de dois tipos (normal, expandido, lateral e golpes), tamanho de fonte, altura e limites reais do texto em cinco viewports (320/390/1024/1366/1720px, temas claro/escuro). Capturas em `test-results/dashboard-10f9/`. CI pendente de conclusão; NPC cadastrado e produção não verificados. PR para revisão, sem merge automático.

## Etapa 10F.8 — Legibilidade do combate no dashboard (21/11/2026)

**Plano e escopo:** (1) destacar os seis valores base com tipografia e contraste dos tokens do tema; (2) separar nome, dano e tipo dos golpes na visão normal preservando quatro slots; (3) compactar a grade 2x2 dos golpes detalhados, mantendo precisão e demais dados, e elevar a hierarquia dos atributos atuais; (4) permitir quebra dos nomes dos Pokémon laterais, empilhar a visão resumida no celular e preservar a rolagem dos notebooks baixos; (5) validar por Playwright com equipe fictícia de seis Pokémon, slots preenchidos/vazios e temas claro/escuro.

**Implementação:** branch `feat/dashboard-combate-legibilidade-10f8`. Alterados `static/css/dashboard.css`, templates de jogador e NPC (estrutura dos golpes e cache da folha compartilhada), contratos estáticos e novo teste `tests/visual/test_dashboard_legibilidade_10f8.py`. O painel expandido deixa de esticar a área de golpes por toda a altura restante e usa linhas dimensionadas por conteúdo; a coluna de detalhes pode rolar quando necessário. Não altera cálculos, ações, permissões ou dados da campanha; nenhuma migration. Prévia mestre usa o mesmo template do jogador.

**Validação:** Playwright em 1720×864 escuro, 1366×768 claro e 390×844 escuro; equipe fictícia completa, atributos maiores, dados dos golpes e altura dos quatro slots compactos, abertura/recolhimento por teclado/botão, largura do documento e capturas. Contratos anteriores preservados; alterações compartilhadas com o NPC, mas teste específico de NPC cadastrado permanece pendente. CI ainda a confirmar; PR sem merge automático.

## Etapa 10F.7 — Auditoria Playwright de telas e correção desktop da Bag (21/11/2026)

**Pedido:** revisar o projeto por completo procurando erros visuais, corrigindo e documentando. O alcance prático foi definido como auditoria **ampla, reproduzível e não destrutiva** das principais páginas de jogador e mestre, com dados falsos no SQLite e Chromium real; não afirmar revisão exaustiva do banco de produção ou de todos os estados de NPC.

**Branch/PR:** `audit/playwright-full-ui-10f7`, PR #38 contra `main`, **sem merge automático**, iniciada após a mesclagem do PR #37.

**Teste novo:** `tests/visual/test_auditoria_telas_10f7.py` visita as telas primárias de jogador/mestre em 390×844/1366×768, telas dinâmicas (ficha, equipe, edição de Pokémon, forma, golpe, item, prévia), menu mobile e alguns casos 320/768px. Registra exceções JavaScript, status, redirects, overflow global e screenshots por tela. Login de teste apenas no SQLite; nenhum POST de gameplay.

**Primeira execução CI Playwright:** [GitHub Actions #44879022964](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44879022964), **53 passed, 3 failed em 89,75s**. Achado real: `/jogador/inventario` no desktop 1366px tinha largura de documento 1458px, excesso de **92px**. `static/css/visual-inventario-10c5.css` permite `overflow:visible !important` no desktop; o pseudoelemento `.inventario-nds-bag::after` saía 120px para a direita (a contenção 10F.3 era apenas mobile). **Correção:** tornar contenção `right:0; width:min(380px,100%)` global na camada visual e atualizar `v=` de cache em `templates/jogador/inventario.html`; atualizar teste CSS 10F.3. Sem mudar o overflow da Bag, o autocomplete ou o JS.

**Falhas não referentes a layout:** duas tentativas de abrir `/regiao/ankar` como jogador terminavam em `/login`. Inspeção da rota comprovou `@perfil_obrigatorio("mestre")`. Corrigimos o **teste**, não a autorização, e adicionamos uma verificação negativa explícita.

**Segunda execução de CI (antes da correção do link de criação):** [GitHub Actions #44879376337](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44879376337), **88 passed, 2 failed em 158,65s**. Ambas as falhas eram de teste: a rota `/mestre/jogadores/<id>/equipe/novo` intencionalmente redireciona para a Box se não receber `?destino=box:box-unica`, conforme `app/routes/pokemons.py::_novo`. O cenário Playwright agora inclui esse parâmetro; a permissão/validação do backend não mudou. Capturas da segunda execução foram inspecionadas, confirmando telas de formulários e prévia em 390/1366px. A fixture `tests/visual/conftest.py` foi corrigida para usar o sprite local do Bulbasaur no lugar de `https://img/` (URL falsa do dataset de serviço), e o teste da Bag agora exige que a imagem fictícia carregue. Foram acrescentados 12 cenários de tema escuro para painéis, Equipe, Bag e catálogo.

**Validação final:** [Playwright #44879957277](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44879957277): **102 passed in 153.41s**, Chromium real, 96 screenshots no artefato, incluindo tema escuro, detalhe/edição, 320/390/768/1366px e acesso/foco. [Contrato visual #44879957142](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44879957142): **59 passed in 2.04s**. Conferidas capturas representativas antes/depois da Bag desktop e em mobile escuro; imagem do Pokémon sintético agora carrega. Sem novos erros observados nos cenários cobertos. **Status:** patch e documentação concluídos na branch, PR #38 aberto sem merge automático.  As páginas de NPC cadastrado não são garantidas pela fixture mínima e serão auditadas em etapa específica quando houver dados artificiais representativos. Nenhum dado real, migration, rota ou regra da campanha alterado.

## Etapa 10F.6 — Playwright com navegador real e SQLite isolado (21/11/2026)

**Motivo:** usuário instalou e validou localmente Playwright, colocou `tests/visual/test_smoke.py` no GitHub e pediu adicionar dependências e **executar os testes agora**. A `main` ainda não continha `pytest-playwright` em `requirements-dev.txt` nem workflow de navegador.

**Implementação na branch `test/playwright-ui-browser-10f6`:** adicionar `pytest-playwright>=0.7,<1.0` às dependências de desenvolvimento; manter e integrar o smoke existente, com URL pública opcional e Flask isolado por padrão. A fixture em `tests/visual/conftest.py` sobe Flask real em porta aleatória com SQLite temporário, login fictício, sprite de teste válido e um Pokémon na equipe. `tests/visual/test_fluxos_jogador.py` navega com Chromium e verifica o sprite/atalho da ficha, a altura real do quadro de atributos ao abrir/recolher e a largura/abas da Bag em 390px. O workflow `.github/workflows/test-playwright-ui-10f6.yml` instala Chromium via `python -m playwright install --with-deps chromium`, executa testes e publica screenshots/traces como artefatos. `.gitignore` exclui `test-results/` e `playwright-report/`; README explica instalação e execução.

**Escopo:** testes e infraestrutura de desenvolvimento; nenhum modelo, regra do RPG, dado real, upload, sessão de usuário, segredo, migration ou rota modificados. O teste de smoke pode inspecionar outra URL explicitamente fornecida via variável de ambiente, mas os fluxos autenticados usam exclusivamente o app de testes. PR para revisão, não mesclar automaticamente.

**Status:** [GitHub Actions — Playwright real, Chromium e SQLite isolado](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44878523109) **aprovado: 5 testes passaram em 9,94s**, incluindo smoke 390/1366px, sprite/ficha, altura de atributos no foco e Bag mobile. Screenshots e traces foram tratados pelo workflow; a validação externa do túnel e do PostgreSQL real não faz parte deste teste. Se novos cenários revelarem erros visuais, registrar diagnóstico e corrigir separadamente.

## Etapa 10F.5 — Sprite do personagem, ficha pelo retrato e altura dos atributos (21/11/2026)

**Pedido:** após confirmar a correção mobile, o usuário enviou prints do painel normal e do Pokémon expandido pedindo três mudanças: usar o sprite de cada personagem no lugar da foto/inicial do painel; retirar o botão `Minha ficha` da barra e abrir a ficha ao clicar no sprite; preservar o tamanho do quadro `Atributos` do personagem na transição de foco.

**Implementação na branch `feat/dashboard-sprite-ficha-atributos-10f5`:** o serviço `app/services/entrada_personagens_service.py` expõe `sprite_personagem_por_login`, baseada na configuração já existente do seletor de personagens; as rotas `jogadores.dashboard` e `mestre.preview_jogador` passam `sprite_personagem_url` ao template compartilhado. O painel usa esse sprite (ou a foto/inicial como fallback) como link acessível para a rota existente de ficha, e `templates/base.html` remove apenas o item `Minha ficha` dos menus de jogador e prévia. `dashboard-pokemon.js` mede a altura do quadro de atributos antes do foco e a restaura após recolher; `dashboard.css` a preserva via variável CSS somente no painel do jogador, sem aplicar a regra ao painel do NPC. Atualizar cache de CSS e JS nos dois templates afetados.

**Preservações:** tela de ficha, edições GET/POST, foto cadastrada, permissões, login e vínculo de personagem não foram removidos nem alterados; nenhuma migration, atualização de banco ou regra do RPG. A configuração de sprite continua usada só para visualização, não para autorização. Testes visuais e de integração `tests/test_dashboard_sprite_ficha_atributos_10f5.py` e `tests/test_fichas_por_url_10b3_flask.py` no workflow.

**Status:** PR #36 aberto sem merge; CI inicial **Contrato visual e organização do repositório** aprovada com **59 testes** (21/11/2026) e verificações de sintaxe JavaScript aprovadas ([run](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44876143408)); integração **Correção de evolução tester e fichas por URL** aprovada com **48 testes** ([run](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44876143468)); suíte **Ações no painel expandido e Mega no menu mestre** aprovada com **87 testes** ([run](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44876143310)). Inspeção visual real e confirmação em ambiente publicado continuam pendentes. Inspecionar com diferentes sprites, conta sem sprite configurado, URLs /p/<login>, prévia mestre e comparação da altura do quadro de atributos antes/depois de abrir/recolher um Pokémon. Na janela com altura baixa preservar a rolagem implementada na etapa 10F.4.

## Etapa 10F.4 — Foco acessível em notebooks baixos (21/11/2026)

**Escopo:** continuação incremental da revisão de frontend após a confirmação do usuário de que a Bag mobile ficou correta. A inspeção do código compartilhado por jogador e NPC encontrou um risco de corte no modo expandido: a partir de 901px, `dashboard.css` bloqueia o overflow do documento e fixa grade, card principal e detalhes à altura da viewport; os golpes e ações também têm contenção. Em alturas baixas isso pode ocultar informações sem alternativa de rolagem.

**Branch:** `fix/dashboard-foco-rolagem-10f4`, baseada na `main` após o PR #34 já mesclado. Propor PR independente, **sem merge automático**.

**Implementação:** adicionar `@media (min-width: 901px) and (max-height: 760px)` em `static/css/dashboard.css`: restaurar scroll vertical do documento, alturas naturais na ficha, grade e card em foco, detalhes/golpes/anotações sem clipping, companheiros laterais com tamanho natural e treinador não sticky; manter layout desktop alto e mobile intactos. Atualizar cache de CSS nos dois templates do dashboard. Criar `tests/test_dashboard_foco_baixa_altura_10f4.py` no workflow visual. Nenhuma alteração de JS, rotas, dados ou regras de Ankar.

**Status:** implementação e testes adicionados; CI inicial do contrato visual aprovada (**54 passed in 1.46s**, em 21/11/2026) no [GitHub Actions](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44873226725); validação visual real ainda pendente. **Verificação complementar:** jogador, mestre em prévia e NPC em notebooks 1024×600 e 1366×768, zoom 200%, 1–6 Pokémon, campos de informações longos, uso de Recolher, editar e ações de retrato. Não afirmar correção visual definitiva sem navegador real.

## Etapa 10F.3 — Largura do inventário e abas completas no celular (21/11/2026)

**Origem:** usuário relatou que a Bag continuava visualmente cortada depois da etapa 10F.2 (PR #33 já mesclado). Inspeção do CSS revelou outro transbordamento potencial: `inventario.css` coloca `.inventario-nds-bag::after` 120px para fora do painel, e `visual-inventario-10c5.css` permite `overflow: visible` até 1199px. A faixa circular que aparece no espaço escuro à direita do print é compatível com esse elemento decorativo. O teste no celular ainda deve confirmar a correção.

**Branch:** `fix/inventario-mobile-largura-abas-20261121`, baseada em `main`. Nova PR de correção incremental, sem merge automático.

**Alterações:** no `static/css/visual-inventario-10c5.css`, limitar o pseudoelemento decorativo ao painel até 1199px; até 540px, substituir o carrossel de abas por grade 2 colunas que exibe as cinco categorias inteiras e quebra nomes longos. `templates/jogador/inventario.html` recebe nova versão de cache. `tests/test_inventario_largura_10f3.py` cobre contratos CSS e do template, incluído no workflow de CI visual. Atualizar documentação e diário.

**Preservações:** nenhuma mudança no JS, regras de itens, banco, migrations, permissões, ações ou dados. O carrossel de Pokémon continua rolável horizontalmente; o painel de mestre mantém `overflow: visible` para o autocomplete.

**Status:** patch preparado e CI inicial aprovada: 49 testes passaram em 1,96s no [workflow visual](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44869536228), incluindo a nova regressão; sintaxe do JavaScript aprovada. Em teste isolado com Chromium a largura do documento passou de 430→320px (viewport 320), 500→390px (viewport 390) e 540→430px (viewport 430), com todas as abas contidas no painel. **Ainda falta verificar o site completo no mesmo Android/Chrome depois de publicar a alteração** (320/390/430px, zoom 200%, cabeçalho, categorias e autocomplete mestre).

## Etapa 10F.2 — Correção da Bag/Inventário em celular (21/11/2026)

**Motivo:** captura de tela de Android/Chrome enviada pelo usuário mostrou cards da equipe cortados lateralmente e a aba Item-chave ativa sem aparecer por completo. A inspeção do código confirmou o conflito: `sistema-ui.css` forçava `overflow-x: hidden` com seletor mais específico que o `overflow-x: auto` planejado por `visual-inventario-10c5.css`. O JS selecionava a primeira bolsa não vazia, mas não a posicionava na faixa horizontal.

**Branch:** `fix/inventario-mobile-rolagem-20261121`, iniciada em `main` depois que o PR #32 da etapa 10F.1 foi mesclado. **Status:** alterações e regressões adicionadas; contrato visual e sintaxe JS aprovados no GitHub Actions (45 testes, 21/11/2026); teste no aparelho do usuário pendente. Nova PR para revisão, sem merge.

**Mudanças:** remover apenas os overrides globais de `overflow-x` e tamanhos de cards/fotos no tablet/celular, preservando valores de desktop em `@media (min-width: 1200px)`; fazer `static/js/inventario.js` rolar **a faixa de abas**, sem rolar a página; atualizar cache em `templates/base.html` e `templates/jogador/inventario.html`; atualizar `tests/test_sistema_ui.py` e adicionar `tests/test_inventario_mobile_10f2.py` ao workflow de contrato visual.

**Escopo:** somente frontend, nenhuma alteração de PostgreSQL, migration, rotas, autorizações, troca de personagem, transferência de itens ou lógica de uso/equipamento. A captura mostra também espaço à direita da área do site: o código corrigido não comprova sozinho a causa dessa aparência externa; solicitar revisão visual no dispositivo após deploy antes de considerar toda a questão encerrada.

**Validação CI:** a primeira execução teve 1 falha em 45 cenários devido a um teste de navegação que exigia o identificador de cache CSS antigo; foi ajustado `tests/test_navegacao_mobile_10f1.py` para verificar a existência de versionamento sem fixar um sufixo específico. A execução seguinte do workflow `Contrato visual e organização do repositório` passou: `45 passed in 1.43s`, com `node --check static/js/inventario.js` aprovado. [Execução aprovada](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44867035422).

**Validação necessária:** conferir rolagem por toque da equipe (mais de um Pokémon), abertura direta em Item-chave, troca e navegação por teclado entre abas, zoom, largura total no Chrome do celular, painel mestre e jogador. Próxima etapa: revisão visual localizada da interface conforme novos achados, após aprovação deste patch.

## Etapa 10F.1 — Navegação mobile e conflito entre CSS globais (21/11/2026)

**Status:** IMPLEMENTADO NA BRANCH; CI DO CONTRATO VISUAL APROVADA (40 testes, 21/11/2026); VALIDAÇÃO VISUAL REAL PENDENTE. Branch: `fix/mobile-nav-global-css-20261121`, baseada em `main`. PR proposto contra `main`, sem merge automático.

**Diagnóstico:** `sistema-ui.css` possuía regras de cabeçalho e um `@media (max-width: 900px)` com seletores mais específicos (`body.app-shell .navegacao-principal`, `body.app-shell .topo`, `body.app-shell .marca` e `body.app-shell .usuario-topo`). Elas competiam com `visual-global-10c5.css`, impedindo o estado `display: none` do menu móvel e misturando `grid-template-areas` com as linhas/colunas móveis.

**Alteração:** retirar de `sistema-ui.css` as regras concorrentes de navegação; deixar layout/estado responsivo exclusivamente em `visual-global-10c5.css`, preservando o nome do usuário oculto abaixo de 900px. Atualizar versões CSS em `templates/base.html`; ajustar `tests/test_sistema_ui.py`, adicionar `tests/test_navegacao_mobile_10f1.py` e incluí-lo no workflow `.github/workflows/test-contrato-ui-repositorio.yml`. Atualizar `docs/ARQUITETURA_FRONTEND.md` e o diário de desenvolvimento.

**Escopo seguro:** sem mudanças em rotas, JavaScript da navegação, autenticação, permissões, modelos, dados, sprites, migrações ou regras de Ankar. Os testes estáticos verificam contratos CSS/template, **não** a renderização no navegador ou acessos reais.

**Validação automatizada efetiva:** workflow [Contrato visual e organização do repositório](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44865434964) executou `python -m pytest -q` com **40 passed in 2.97s** na PR #32, incluindo `tests/test_navegacao_mobile_10f1.py`. **Validação manual pendente:** conferir também a navegação de mestre/jogador/prévia em 320, 390, 768, 900, 901, 1100, 1101 e 1440px, com modo claro/escuro, zoom 200%, clique fora, Escape e troca de breakpoint. Próxima etapa recomendada depois disso: revisão localizada do dashboard do jogador e do painel de NPCs, sem redesenho massivo.

## Atualização de arquitetura visual e limpeza de repositório — 21/11/2026

A revisão de novembro mantém **o mesmo Flask/PostgreSQL e as regras ativas de Ankar**. Foi criada a branch `refactor/visual-system-repo-cleanup-2026` para:
- concentrar tokens e densidade em `static/css/sistema-ui.css`, remover `refinamento.css` e conflitos legados de cabeçalhos em `geral.css`;
- manter `visual-global-10c5.css` e `padrao-visual-10d1.css` para comportamento responsivo e navegação, usando tokens de base;
- remover 37 backups versionados (com recuperação pelo histórico Git), arquivar READMEs e instruções legadas fora da raiz e documentar instaladores antigos;
- criar `README.md`, `docs/ARQUITETURA_FRONTEND.md`, `docs/ORGANIZACAO_REPOSITORIO.md` e o teste de contrato `tests/test_contrato_visual_repositorio.py`.

**Atenção:** referências de versões anteriores neste documento são históricas. O código da `main`, o README principal e os documentos atualizados de arquitetura prevalecem. Não remover migrações, sprites, uploads ou dados privados para reduzir o número de arquivos. Não executar instaladores PowerShell legados sobre a versão atual. A revisão é exclusivamente visual/organizacional, sem migrations ou alteração de dados reais.


## 1. Missão e instrução para o próximo assistente

Você está continuando, **não recriando**, o site de gerenciamento da campanha Pokémon RPG da região fictícia de **Ankar**. Trabalhe incrementalmente no código existente, preservando dados, permissões, rotas e comportamentos que já funcionam. Use este documento como orientação inicial, porém **confirme os detalhes no código da cópia mais recente**: uma implementação posterior prevalece sobre descrições históricas.

Ao iniciar uma nova conversa:

1. Leia este documento, `docs/DIARIO_DESENVOLVIMENTO.md`, `docs/AGENTS.md` e os documentos de referência relevantes ao módulo trabalhado.
2. Confira a revisão atual do Git (`git status`, `git log -5`) e quais alterações locais ainda não foram commitadas; **não descarte mudanças do usuário**.
3. Identifique qual demanda está ativa e se uma correção anterior foi realmente aplicada. Nunca trate uma etapa planejada como concluída.
4. Antes de mudar esquema de dados, verifique as migrations e o estado real do banco, se houver acesso autorizado. Não execute alterações destrutivas nem importação de dados em produção sem plano de backup.
5. Implemente uma alteração por vez, com verificação correspondente. Registre arquivos alterados, mudanças de comportamento, comandos de teste e seus resultados reais.
6. **Após cada etapa concluída, atualize este documento e o diário**, incluindo a próxima tarefa recomendada, de modo que o contexto sobreviva a quebras de conversa.

> **Limitação operacional:** este documento só será atualizado quando o projeto/arquivo for disponibilizado e a atualização for feita de fato. Não há monitoramento autônomo de mudanças futuras no Git ou no servidor.

## 2. Propósito do sistema e fontes de regras

O site serve como plataforma de apoio a mestre e jogadores na campanha Ankar: fichas de treinador, equipes de Pokémon, Boxes, catálogo, inventário, gestão administrativa e futuras ferramentas de encontro e batalha.

**Fontes fornecidas para o projeto:**

- `pkmrpg-playtest-2_5.pdf` — manual base do Pokémon RPG v2.5 (Vinícius Ottoni).
- `Ficha Editável v2.5.xlsx` e `Utilitários v2.5.xlsx` — fichas e ferramentas do sistema original.
- `Ankar - Cidades e Pontos de Interesse - PokéRPG.xlsx` — locais da campanha.
- `Região de Ankar - Rotas - PokéRPG.xlsx` — rotas da campanha.
- `Mapa.jpg` — mapa da região.

**Hierarquia de decisões:** (1) decisões explícitas atuais da campanha e código validado, (2) documentação técnica atualizada do projeto, (3) manual PKMRPG 2.5, quando não houver adaptação específica. **Não restaurar automaticamente mecânicas do manual que foram retiradas de Ankar.**

### Adaptações obrigatórias da campanha

Confirmadas em `README.md`, `ALTERACOES_CAMPANHA.md` e implementação:

- **Nível compartilhado:** `personagens.nivel` governa os cálculos de todos os Pokémon do treinador, inclusive na Box; não há nível próprio na tabela `pokemons`.
- **Mecânicas retiradas do fluxo atual:** experiência individual de Pokémon, amizade, taxa de captura automática, recurso/consumo dos golpes, contagem de usos dos golpes e ataque de emergência por falta de recurso.
- **Equipe com até 6 Pokémon**; **uma Box por personagem, com 100 espaços**; novos Pokémon são criados por vagas na Box, respeitando as permissões.
- Cálculos atuais consideram estatísticas por nível, atributos base, Shiny, natureza, estilo de combate, alguns estados e bônus manuais.
- Golpes individuais: máximo de 4. Alteração de item carregado deve passar pelo inventário com movimentação de unidades.

**Consequência para os novos módulos:** “captura” é atualmente o nome de uma necessidade visual/narrativa de geração e **atribuição pelo mestre**; **não** presumir que se deva criar uma rolagem de taxa de captura, XP individual ou recursos de PP.

## 3. Stack técnica e execução

Verificado na aplicação e dependências:

- **Backend:** Python 3.10+, Flask 3.x, Flask-SQLAlchemy, SQLAlchemy 2.x, Flask-Migrate/Alembic, psycopg 3, python-dotenv.
- **Banco persistente de referência:** PostgreSQL. JSONs em `data/` existem para importação/legado e alguns backups; não substituem o PostgreSQL para fichas, Pokémon e inventários atuais.
- **Frontend:** templates Jinja2 em `templates/`, CSS em `static/css/`, JavaScript vanilla em `static/js/`.
- **Servidor de testes remotos:** Waitress e scripts PowerShell com Cloudflare Quick Tunnel, conforme `TESTES_REMOTOS_CLOUDFLARE.md`.
- **Testes:** pytest, arquivos sob `tests/`, com fixtures de SQLite para parte dos testes; resultados atuais precisam ser obtidos no ambiente apropriado.
- **Inicialização:** `app.py` chama a fábrica Flask `create_app()` em `app/__init__.py`.
- **Configuração:** variáveis de ambiente em `.env` (arquivo **sensível**, não deve ser compartilhado/publicado). Referência segura: `.env.example`.

Procedimento documentado para ambiente Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
flask --app app.py db current
pytest -q
python app.py
```

Não execute `db upgrade` sem antes validar backup e revisar as migrations pendentes. Os comandos administrativos de diagnóstico incluem:

```powershell
flask --app app.py catalogo verificar
flask --app app.py inventario verificar
flask --app app.py pokemon verificar
flask --app app.py midia verificar
```

## 4. Estrutura atual de diretórios

```text
PokemonRPG/
├── app.py                       # Entrada Flask
├── servidor_teste.py           # Servidor de teste
├── app/
│   ├── __init__.py             # create_app, registro de blueprints e comandos
│   ├── config.py, extensions.py
│   ├── routes/                 # HTTP/controle de acesso/telas
│   │   ├── auth.py
│   │   ├── jogadores.py, mestre.py
│   │   ├── pokemons.py, boxes.py
│   │   ├── inventario.py, catalogo_admin.py
│   │   └── combates.py, utilitarios.py  # Reservados (placeholders)
│   ├── services/               # Negócios, validações, transações
│   │   ├── pokemon_db_service.py
│   │   ├── personagem_service.py, painel_mestre_service.py
│   │   ├── item_admin_service.py, inventario_service.py
│   │   ├── catalogo_admin_service.py, golpe_admin_service.py
│   │   ├── permissoes_service.py, calculo_atributos.py
│   │   ├── gerador_pokemon.py, calculo_combate.py, calculo_captura.py # Reservados
│   │   └── importacao/
│   ├── models/db/              # ORM PostgreSQL
│   ├── commands/               # Comandos Flask de diagnóstico/importação
│   └── seed/
├── migrations/versions/        # Migrations Alembic
├── templates/                  # Páginas mestre e jogador, componentes
├── static/css/, static/js/     # Estilos e scripts
├── static/uploads/             # Uploads locais: preservar/backup separado
├── data/                       # Dados locais, legado e backups
├── tests/                      # Testes automatizados
├── scripts/                    # Importação, utilitários, túnel de testes
└── docs/                       # Estes arquivos de continuidade
```

### Divisão de responsabilidades existente

- **Rota:** requisição, sessão, autorização, resposta/redirect e mensagens.
- **Serviço:** regra de negócio, validações, transações e cálculos.
- **Modelo:** entidade relacional e integridade de dados.
- **Template/JS/CSS:** apresentação e interação.
- **Migrations:** evolução explícita e versionada do esquema.

**Observação:** `app/routes/catalogo_admin.py` concentra vários módulos e é candidato a refatoração futura, mas **não** refatorar apenas para incluir documentação ou uma pequena correção.

## 5. Autenticação, perfis e permissões

Perfis no banco: `administrador`, `mestre`, `tester`, `jogador`; a validação atual consulta o perfil no PostgreSQL para evitar usar apenas controles de tela.

- **Mestre/administrador:** acesso administrativo, fichas de jogadores, catálogos, ajuste de inventário e criação/edição de Pokémon em Boxes dos personagens.
- **Tester:** telas pessoais, criação de Pokémon em espaços vazios da própria Box e edição completa dos próprios Pokémon; não pode criar/conceder itens.
- **Jogador:** consulta e administra seus Pokémon existentes (limitado nos campos de identidade); não pode criar Pokémon nem itens; usa inventário conforme permissões.

Regras detalhadas: `PERFIS_E_PERMISSOES.md`, `PERMISSOES_POKEMON_E_TIPOS.md` e `app/services/permissoes_service.py`.

Não ampliar permissões por meio de um botão no frontend; verificar autorização no servidor, vínculo de campanha e propriedade dos registros.

## 6. Principais entidades relacionais existentes

Verificadas em `app/models/db/`:

| Área | Tabelas principais | Notas |
|---|---|---|
| Identidade | `usuarios`, `campanhas`, `campanha_membros` | Perfil e vínculo de campanha |
| Treinador | `personagens`, `personagem_atributos`, `personagem_insignias` | Contém `personagens.nivel` |
| Pokémon | `especies_pokemon`, `formas_pokemon`, `pokemons`, `pokemon_golpes`, `pokemon_status`, `pokemon_bonus_atributos` | `pokemons.personagem_id` obrigatório; `localizacao` é `equipe` ou `box` |
| Mecânicas | `golpes`, `naturezas`, `natureza_modificadores`, `status_condicoes`, `tipos_pokemon`, `efetividades_tipo`, `forma_pokemon_golpes` | Catálogos e relacionamentos |
| Itens | `categorias_item`, `itens`, `personagem_itens` | `itens.efeitos` JSON versionado; quantidades por personagem |
| Configuração e auditoria | `regras`, `regra_valores`, `historico_alteracoes` | Regras e trilha de modificações |

O registro `pokemons` contém `forma_pokemon_id`, `genero`, `shiny`, `natureza_id`, `pv_atual`, `localizacao`, `posicao`, `item_equipado_id` e campos complementares. A estrutura **não comporta diretamente um Pokémon ainda não atribuído**, pois requer `personagem_id`. A nova tela de geração deve projetar claramente o estado temporário ou persistente dos encontros antes de conceder ao jogador, sem violar essa restrição.

O arquivo de migrations mais recente na cadeia do código inspecionado é `b72cf044e6ad_reconciliar_perfil_tester_postgresql.py`. **Isso não comprova que a base de dados real já foi atualizada até essa revisão.** Algumas documentações antigas citam heads anteriores; consultar sempre `flask --app app.py db current` na instalação correta.

## 7. Funcionalidades implementadas ou estruturadas

**Confirmado em rotas/modelos/documentação; o funcionamento em produção não foi testado nesta revisão:**

- Login/logout e gerenciamento de perfis (`app/routes/auth.py`).
- Ficha e dashboard do treinador (`app/routes/jogadores.py`, `app/routes/mestre.py`).
- Painel do mestre, gestão de jogadores e ajuste separado de nível (`app/routes/mestre.py`).
- Catálogos de espécies/formas, golpes, vínculos de aprendizado e itens (`app/routes/catalogo_admin.py`).
- Pokémon individual e equipe (`app/routes/pokemons.py`).
- Box única por treinador (`app/routes/boxes.py`).
- Inventário, transferências, consumo e equipamento (`app/routes/inventario.py`).
- Autocomplete e pesquisas dinâmicas (`static/js/` e endpoints de catálogo).
- Upload de imagens e controle de arquivos locais (`app/services/upload_service.py`).
- Testes automatizados presentes em `tests/`.

**Reservado/não implementado como funcionalidade ativa:**

- `app/services/gerador_pokemon.py` contém apenas uma indicação de módulo futuro.
- `app/services/calculo_combate.py`, `app/services/calculo_captura.py`, `app/routes/combates.py` e `app/routes/utilitarios.py` contêm placeholders.
- Os blueprints de combate/utilitários **não estão registrados** em `app/__init__.py`, embora existam templates relacionados. Um template isolado não significa uma funcionalidade utilizável.
- Não foi identificado painel multi-equipes ativo de até 16 times, nem a nova geração visual e atribuição de Pokémon para os jogadores.

## 8. Pendências e roteiro do produto

### Etapa A — Verificar a correção anterior e o cadastro de itens

A última conversa mencionou uma **primeira correção** não totalmente identificada pelo histórico disponível. O Git fornecido mostra alterações recentes no inventário (23/10/2026); não considerar que isso resolva necessariamente o problema de cadastro.

1. Reproduzir o defeito real de criação de item, com dados válidos e inválidos.
2. Examinar `templates/mestre/catalogo/item_form.html`, `static/js/itens-admin.js`, `app/routes/catalogo_admin.py` (rota `novo_item`) e `app/services/item_admin_service.py` (`criar_item_admin`).
3. Avaliar formulário, editor de efeitos, categoria, preço, upload, validação, rollback e mensagens de erro.
4. Corrigir de modo cirúrgico; testar criação, edição e persistência.
5. Partir de `tests/test_itens_inventario.py` e testes relacionados, ampliando cobertura quando necessário.

**Situação em 23/10/2026:** **PARCIAL — CORREÇÃO IMPLEMENTADA, TESTE INTEGRADO PENDENTE.** Revisão estática confirmou dois comportamentos defeituosos:

- Preço de item com valor textual ou decimal era silenciosamente transformado em `0` pelo helper de inteiro. `app/services/item_admin_service.py` agora rejeita valores não inteiros e valores acima de `999.999.999` (limite já definido no formulário). Preço em branco permanece `0`.
- No editor de itens, após remover todos os efeitos, caso outro campo fosse inválido, `app/routes/catalogo_admin.py` restaurava os efeitos anteriores na tela via fallback `or efeitos_iniciais`. Agora respeita a lista vazia enviada.

Novos testes de regressão estão em `tests/test_itens_inventario.py`. **Validações realmente executadas:** 7 casos isolados da função de preço, compilação dos arquivos Python alterados e verificação da sintaxe do JavaScript; todos passaram. **Bloqueio:** dependências Flask/Flask-SQLAlchemy ausentes no ambiente desta revisão e instalação online indisponível; testes de integração não executados. Banco PostgreSQL real não acessado.

**Próximo passo:** em ambiente com dependências instaladas, executar `pytest -q tests/test_itens_inventario.py`, reproduzir o fluxo real de criação e edição no navegador (inclusive upload e efeitos), e depois executar `flask --app app.py catalogo verificar` e `flask --app app.py inventario verificar` antes de auditar dados. Não houve migration.

### Resultado registrado da correção anterior — 23/10/2026

O usuário relatou **`9 passed in 10.86s`** após executar os testes recomendados para a revisão do cadastro de itens. Esse resultado veio da instalação do usuário; **não foi reexecutado neste ambiente de análise**. A execução manual no navegador e o catálogo PostgreSQL da campanha permanecem por conferir.

### Etapa B — Auditar catálogo e banco de itens

Após estabilizar o formulário:

- Verificar consistência, duplicatas, categorias, imagens, preços, sinalizadores `consumivel`, `equipavel`, `uso_em_batalha` e formato de `efeitos`.
- Validar relacionamentos `personagem_itens` e `pokemons.item_equipado_id`.
- Confrontar categorias e itens com o capítulo 16 do manual e as adaptações Ankar, sem sobrescrever customizações.
- Executar diagnósticos do catálogo/inventário antes de aplicar qualquer correção em massa; proteger dados reais com backup e alterações reversíveis.

**Situação (23/10/2026):** nova ferramenta de diagnóstico implementada no código, sem escrita no banco. A auditoria real dos registros continua **pendente** até que o usuário execute o comando no seu PostgreSQL e compartilhe o resultado.

**Novo comando:** `flask --app app.py catalogo auditar-itens` (usar `--todos` para listar todos os achados). Verifica estrutura/versionamento dos efeitos, referências internas, categorias, códigos equivalentes, preços e suspeitas de duplicatas. **Erros** produzem saída diferente de zero; **avisos** não bloqueiam o processo e exigem análise humana. Não faz update, delete, importação ou migration. Para a parte de inventário/equipamentos, executar também `flask --app app.py inventario verificar`.

**Arquivos desta entrega:** `app/services/auditoria_itens_service.py`, `app/commands/catalogo.py`, `tests/test_auditoria_itens.py`, documentação em `docs/`.

**Testes nesta revisão:** oito verificações isoladas da lógica de auditoria passaram; compilação Python passou. Testes integrados dependentes de Flask não executados neste ambiente (as dependências não estão disponíveis). Os seis novos cenários de pytest devem ser validados pelo usuário.

**Não inferir cobertura do manual:** o diagnóstico é de integridade de dados e estrutura, não certifica que todos os itens da edição 2.5 estão no catálogo nem que seus efeitos/preços correspondem ao livro. Comparação semântica exige os dados reais e critérios próprios de Ankar.

### Etapa C — Geração visual de Pokémon / atribuição pelo mestre

**Objetivo:** permitir que o mestre gere Pokémon para exibição em uma tela compartilhada e os atribua a jogadores.

**Requisitos confirmados pela conversa:**

- Natureza e sexo devem ser gerados aleatoriamente quando aplicáveis.
- Os Pokémon gerados ficam visualmente disponíveis aos jogadores.
- O mestre decide a qual jogador atribuir cada Pokémon.
- Após atribuição, a instância deve aparecer no conjunto correto do jogador e ser persistida.

**Decisões de projeto a validar antes de codificar:**

- Definir se o encontro gerado vive somente na sessão ou necessita de tabela própria (`encontros_pokemon` ou equivalente); não inserir Pokémon sem dono na tabela atual, que exige `personagem_id`.
- Definir como selecionar espécie/forma e quais campos de configuração específica de sexo estão disponíveis no catálogo. Não presumir que o banco já guarda proporções por espécie.
- Reutilizar `app/services/pokemon_db_service.py` e respeitar Box única com 100 vagas; impedir duplicidade de atribuição.
- Diferenciar visualização pública de ações exclusivas do mestre.
- A geração deve seguir as adaptações atuais da campanha (sem XP/amizado/PP automáticos e sem cálculo automático de chance de captura).
- Se forem desejados vários encontros simultâneos, definir identificadores, validade e remoção.

**Situação:** planejado; implementação principal ainda ausente.

### Etapa D — Campo de batalha compartilhado

**Objetivo:** cada jogador posicionar Pokémon em uma página compartilhada, com **até 16 equipes** independentes.

**Requisitos confirmados:**

- Jogadores colocam Pokémon em campo e todos os participantes visualizam.
- Times distintos permitem PvP; um mesmo time pode reunir Pokémon de jogadores diferentes para cooperação contra outros adversários.
- Suportar vários participantes e equipes sem impor combate apenas 1x1.

**Decisões a validar:**

- Entidade para sessão/arena, membros e posições; independência entre estado da batalha e localização `equipe`/`box` do Pokémon.
- Autorizações de inclusão, movimentação, troca, remoção e encerramento, incluindo controle do mestre.
- Atualização compartilhada por polling ou tecnologia em tempo real ainda a escolher segundo infraestrutura existente; **não presumir Socket.IO já instalado**.
- Definir quais atributos são exibidos sem reintroduzir mecânicas desativadas.
- Combate automático, iniciativa, ataques, dano e efeitos são uma fase **separada** se não forem solicitados.

**Situação:** planejado; placeholders de combate disponíveis, sem implementação funcional.

## 9. Regra de atualização da documentação (obrigatória)

Sempre que uma etapa do projeto terminar, atualizar **no mesmo conjunto de alterações**:

1. `docs/CONTINUIDADE_PROJETO.md`: versão/data, estado da arquitetura, módulos alterados, novas decisões e roteiro/próxima tarefa.
2. `docs/DIARIO_DESENVOLVIMENTO.md`: adicionar entrada cronológica com motivo, arquivos alterados, migrations, comandos de teste **realmente executados**, falhas conhecidas e próximo passo.
3. `docs/AGENTS.md`: atualizar apenas se mudar a convenção principal de leitura/execução do projeto.
4. Manter as instruções de README e docs especializadas coerentes quando seus comportamentos mudarem.

**Formato de status:** `CONFIRMADO NO CÓDIGO`, `DOCUMENTADO (NÃO TESTADO)`, `PLANEJADO`, `BLOQUEADO` ou `CONCLUÍDO E TESTADO`. Não tratar um teste existente no repositório como prova de que passou nesta execução.

**Segurança:** nunca incluir `.env`, senhas, tokens, backups privados, registros identificáveis de jogadores ou dumps completos do banco em pacotes de documentação. Preservar `static/uploads/` e dados PostgreSQL separadamente. Nunca aplicar alterações destrutivas sem autorização e backup.

## 10. Restrições e incertezas desta leitura inicial

- Somente o código empacotado foi inspecionado; o PostgreSQL de execução não foi acessado.
- Não foram executadas as rotas no navegador real.
- `pytest --collect-only` foi tentado, mas falhou por ausência do módulo Flask neste ambiente; **não é um defeito confirmado do projeto**.
- O ramo Git do ZIP trazia uma alteração local não commitada sob `data/campanhas/ankar/jogadores/`; ela deve ser preservada.
- O projeto possui documentos antigos que citam revisões intermediárias e números históricos de testes; usar o estado mais recente do código, não uma contagem histórica, para novas verificações.

## 11. Texto curto para iniciar o próximo chat

> Quero continuar o desenvolvimento do meu site **Pokémon RPG — Ankar**, sem recomeçar. O ZIP do projeto contém `docs/AGENTS.md`, `docs/CONTINUIDADE_PROJETO.md` e `docs/DIARIO_DESENVOLVIMENTO.md`: leia esses arquivos e confronte-os com o código atual antes de qualquer mudança. A aplicação usa Flask + PostgreSQL, com nível compartilhado e algumas mecânicas oficiais desativadas. Preserve meus dados, minhas permissões e a arquitetura existente. Informe a etapa ativa e os arquivos envolvidos, implemente a tarefa solicitada com testes e **atualize os documentos de continuidade** ao final, registrando exatamente o que foi modificado e o que segue pendente.

---

**Documentos técnicos existentes úteis:** `README.md`, `ORGANIZACAO_PROJETO.md`, `ALTERACOES_CAMPANHA.md`, `BANCO_DE_DADOS.md`, `PERFIS_E_PERMISSOES.md`, `PERMISSOES_POKEMON_E_TIPOS.md`, `ITENS_INVENTARIO.md`, `CATALOGO_ADMIN.md`, `PAINEL_MESTRE.md`, `ALINHAMENTO_INVENTARIO_UI2.md`.

## 12. Andamento — 23/10/2026: importação de naturezas como equipamento

**Confirmado nos dados de origem:** a última saída da auditoria, enviada pelo mestre, apontou inúmeros avisos de itens `importado-ficha-*` sem categoria; `inventario verificar` confirmou 110 registros, 456 unidades e 48 itens equipados consistentes em termos referenciais. A análise do JSON das nove fichas identificou **49 referências preenchidas de `item` que são literalmente iguais à `natureza` do próprio Pokémon** (21 naturezas distintas). Essa é uma falha na preparação/importação de dados legados, não uma categoria que deva ser criada.

**Alterações disponíveis em pacote incremental:** o importador agora ignora `item == natureza` com aviso, e o comando `flask --app app.py catalogo revisar-naturezas-importadas` faz simulação de vínculos suspeitos exclusivamente na campanha Ankar. Somente `--aplicar` remove as referências elegíveis e registra histórico, sem alterar unidades de inventário e sem apagar itens do catálogo. Consulte `docs/ITENS_INVENTARIO.md` para os critérios restritivos de segurança e as instruções.

**Situação:** código preparado; 3 testes unitários puros passaram; testes integrados e execução em PostgreSQL pelo mestre PENDENTES. O número de 49 é do seed original e **não** deve ser confundido com os 48 vínculos atualmente relatados no banco. Não sugerir limpeza em massa, deleção de natureza ou categorização automática desses pseudoitens. Itens genuínos sem categoria continuarão exigindo revisão manual. Nenhuma migration nesta etapa.

**Próximo passo recomendado:** mestre executar `python -m pytest -q tests/test_reparo_natureza_importada.py tests/test_auditoria_itens.py` e `flask --app app.py catalogo revisar-naturezas-importadas` (SEM `--aplicar`) e enviar resultados. Só após confirmar os candidatos deve decidir pela aplicação. Em seguida, auditoria e classificação conservadora dos itens realmente válidos, antes do módulo de geração de Pokémon.


## Atualização — Capturáveis em campo

- Implementada a primeira versão do módulo de capturáveis em campo.
- O mestre pode registrar até 15 Pokémon capturáveis por campanha.
- Cada registro guarda a forma do Pokémon e qual personagem o encontrou.
- A tela do jogador exibe nome, sprite e tipos dos Pokémon disponíveis.
- A tela do mestre permite adicionar e remover capturáveis, preparando a futura etapa de atribuição/captura.

### Etapa 05.1 — Correção de auditoria dos capturáveis (23/10/2026)

O módulo de até 15 capturáveis foi adicionado na Etapa 05, usando a tabela `pokemons_capturaveis` (migration `6f355a4d5b2e`). O usuário executou `tests/test_capturaveis_campo.py`, obtendo `2 failed, 1 passed` devido à tentativa de criar `HistoricoAlteracao` com campos inexistentes `entidade_id`/`detalhes`. A correção alinha o serviço ao modelo vigente (`registro_id`, `dados_anteriores`, `dados_novos`) na criação e remoção de capturáveis e adiciona verificações de regressão do histórico. **Sem nova migration.** Sintaxe Python verificada neste ambiente; integração Flask pendente de reexecução na máquina do usuário.

**Próxima ação:** reexecutar `python -m pytest -q tests/test_capturaveis_campo.py`, confirmar funcionamento do campo do mestre/jogador; a atribuição definitiva à Box é etapa futura.


### Atualização 05.2 — Correção de seleção de espécie no campo

O autocomplete de formas tem dois valores distintos: `valor` (nome exibido, compatibilidade com formulários existentes) e `id` (UUID da forma, usado no campo oculto `forma_id` ao adicionar capturáveis). A UI compartilhada deve preencher o ID para `tipo === 'pokemon'` quando houver campo oculto; itens continuam usando `valor`. O serviço de criação mantém compatibilidade limitada com envios antigos em que `forma_id` e `forma_nome` continham o mesmo nome válido. Sem nova migration. A correção 05.1 do histórico continua necessária.

**Estado dos testes:** usuário relatou aprovação dos testes 05.1. Novos testes 05.2 aguardam execução no ambiente local. Próximos passos: confirmar adição real pela tela, revisar apresentação e evoluir para atribuição à Box.

### Atualização 05.3 — Remoção segura e renumeração (23/10/2026)

Com vários capturáveis, a remoção falhava por conflito da restrição UNIQUE `(campanha_id, ordem)` do PostgreSQL. A etapa 05.3 introduz renumeração em duas fases, ambas na mesma transação: liberar as posições sobreviventes com `NULL` e `flush`, depois definir `1..N` e `flush`. As mutações agora bloqueiam a campanha no PostgreSQL para reduzir conflitos concorrentes entre adicionar/remover. A remoção mantém inativo o registro retirado, o histórico e os dados do Pokémon. Nenhuma migration nova.

**Status:** pacote corretivo pronto; validação integrada e teste manual no PostgreSQL do usuário pendentes. **Verificar:** `python -m pytest -q tests/test_capturaveis_campo.py`, depois remover um capturável do meio da lista e conferir as posições.

### Validação confirmada pelo mestre — Etapa 05.3 (23/10/2026)

**Status: FUNCIONALIDADE DE EXIBIÇÃO/GERENCIAMENTO DE CAPTURÁVEIS VALIDADA NA INSTALAÇÃO DO USUÁRIO.** Após instalar a correção 05.3, o mestre confirmou: “Ótimo, está funcionando corretamente agora”. A confirmação sucede erros reais de seleção de espécie (corrigidos em 05.2), persistência de histórico (05.1) e remoção/reordenação sob restrição UNIQUE (05.3). Os capturáveis já apareciam em campo antes da correção 05.3. Não afirmar quantidade de testes da 05.3 sem receber nova saída do pytest, nem interpretar a confirmação como validação da atribuição à Box, que ainda não foi implementada.

**Próximo desenvolvimento:** atribuição pelo mestre de um capturável à Box de um jogador, preservando forma, natureza e gênero gerados, com garantia de não duplicidade, verificação de capacidade da Box, permissões e histórico. Usar ZIP atualizado para preservar quaisquer alterações locais. A experiência de tentativa de captura é uma fase distinta a definir.


## Etapa 06 — Atribuição de capturáveis à Box (23/10/2026)

**Status: IMPLEMENTADO NO CÓDIGO; TESTES INTEGRADOS PENDENTES NA MÁQUINA DO USUÁRIO.** Base: ZIP enviado após confirmação do funcionamento da Etapa 05.3.

- O mestre escolhe um capturável e um personagem destinatário ativo da campanha e aciona **Atribuir à Box**.
- O servidor usa autenticação e autorização já existentes (`perfil_obrigatorio("mestre")`), mais token de formulário dedicado. Jogadores apenas visualizam o campo.
- O serviço `atribuir_capturavel_box` em `app/services/capturaveis_service.py` bloqueia a campanha para serializar mutações, valida conta ativa de jogador/tester e capacidade da Box, cria um Pokémon na próxima posição e preserva forma/espécie, natureza, sexo e Shiny sem sortear novamente. PV segue o nível compartilhado e as regras do destinatário.
- A retirada do encontro é atômica com a criação na Box: faz a renumeração em duas fases sem conflito UNIQUE e grava históricos `pokemon` e `pokemon_capturavel` vinculados por IDs. Reenvio não duplica.
- Arquivos alterados: `app/services/capturaveis_service.py`, `app/routes/capturas.py`, `templates/capturas/mestre.html`, `static/css/capturaveis.css`, `tests/test_capturaveis_atribuicao.py` (novo), `docs/CAPTURAVEIS.md` (novo), e estes documentos de continuidade.
- **Nenhuma migration nova**; depende da tabela criada na Etapa 05.
- Verificações locais: compilação Python e análise de sintaxe Jinja; testes Flask integrados ainda não executados por ausência das dependências Flask/Flask-SQLAlchemy neste ambiente. Executar `python -m pytest -q tests/test_capturaveis_campo.py tests/test_capturaveis_atribuicao.py` na instalação do mestre.
- Atenção: `docs/CAPTURAVEIS.md` é a referência funcional atual; descrições históricas anteriores que chamam a atribuição de "planejada" refletem versões antigas.
- Próxima fase: testar transferência no PostgreSQL e confirmar na Box; depois decidir sobre tentativa de captura e/ou o painel de batalha de até 16 times.

## Etapa 07 — Painel compartilhado de batalha (23/10/2026)

Implementada a primeira versão do **campo compartilhado com até 16 times**. Jogadores colocam ou movem Pokémon da própria equipe; mestre administra todos, pode retirar Pokémon ou limpar a formação. Os times são compartilhados entre navegadores e atualizados por polling a cada 6 segundos. Cada Pokémon ocupa um único time; os registros são persistidos em `pokemons_em_campo`, com auditoria e validação de permissões no servidor. Enviar Pokémon à Box ou excluí-lo da ficha remove sua participação no campo. Arquivos de implementação, instalação, testes e limites: `docs/CAMPO_COMPARTILHADO.md`.

**Decisão expressa do usuário:** não implementar mecânica automática de tentativa de captura. A tentativa é narrativa entre os jogadores, e a atribuição efetiva é administrada pelo mestre.

**Validação:** sintaxe e integridade dos arquivos verificadas; testes integrados a executar no ambiente local. Nova migration `7a1f20d9c405` deve ser aplicada após backup. Próxima etapa opcional: evolução da interface de combate (HP, ações/turnos) e suporte a oponentes NPC independentes, conforme prioridade do usuário.

## Etapa 08 — Shiny automático e UX de capturáveis (2026-10-25)

- A geração de capturável agora consulta `numeros_shiny` do **personagem que encontrou** o Pokémon, realiza um **1d100 por encontro** e registra `shiny` se o resultado estiver nos números do treinador. Os números são valores **1–100**, não IDs ou números de espécies. Não reprocessar encontros antigos; Shiny é persistido e preservado ao atribuir à Box. O mestre consegue auditar o sorteio no histórico.
- O mestre tem métricas, prévia de espécie, filtros por nome/treinador/Shiny e cards mais legíveis. O jogador tem carrossel com foco nos próprios encontros, seleção de outro treinador ou de todos, miniaturas e setas. Fonte dos dados: mesmo PostgreSQL e endpoints de capturáveis existentes.
- Arquivos: `app/services/capturaveis_service.py`, `app/routes/capturas.py`, `templates/capturas/`, `static/css/capturaveis.css`, `static/js/capturaveis.js`, `tests/test_capturaveis_shiny_carrossel.py`, `tests/test_capturaveis_ui.js`.
- **Sem migration.** Regressões Python dependem da execução na máquina com Flask; o teste JS com Node.js passou (2/2). Tentativa de captura permanece narrativa, sem automação de rolagens de captura.


## Etapa 09 — Qualidade de imagens Pokémon

- Adicionado `static/css/pokemon-hd.css`, carregado por último no tema: interpola imagens de Pokémon suavemente, incluindo carrossel, Campo, Equipe, Box e painel do mestre; não altera artes dos itens.
- Novo comando administrativo `flask --app app.py midia pokemon-hd`: simulação padrão ou download HD de Pokémon HOME (512 px) em lotes, opcional, com atualização das URLs de imagem normal/Shiny quando disponíveis.
- Imagens personalizadas/locais são preservadas; fontes sem correspondência também. Arquivos baixados em `static/img/pokemon-hd/`. Não há migrations.
- Documentação completa em `docs/IMAGENS_POKEMON_HD.md`.
- Limitação atual: ambiente do assistente sem acesso à internet externa para os downloads; comando deve ser executado na instalação local após validação.

## Etapa 09.1 — Diagnóstico e retentativa de imagens HD (25/10/2026)

- O mestre executou a sincronização 09 em sua máquina: **953 formas atualizadas, 110 ignoradas/falhas** entre 1.063 processadas. Detalhes em `docs/FALHAS_SINCRONIZACAO_HD_09_1.md`.
- Da lista textual visível: 88 falhas 404, 1 timeout (Beautifly), 1 limite de resposta (Mew). As 20 entradas anteriores ao início da lista, em Armaldo, foram inferidas como 18 Arceus e 2 Aegislash, com confirmação pendente via PostgreSQL.
- Aprimorado `app/services/imagens_pokemon_hd.py`: aliases seguros para formas, endpoint `pokemon-form`, arte oficial como reserva, retry de rede e JSON até 5 MB.
- Aprimorado `app/commands/midia.py`: atualiza normal/Shiny de maneira independente, comando `pokemon-hd-pendentes`, relatório `relatorio-ultima-sincronizacao.json` e preservação das URLs originais enquanto não há substituto HD válido.
- Testes de regressão adicionados em `tests/test_imagens_pokemon_hd.py` para as falhas reportadas. Nenhuma migration. Testes Flask integrados pendentes de execução pelo mestre.
- A sincronização ocorre **apenas mediante execução manual com `--aplicar`**; não afirmar que as 110 imagens foram corrigidas até receber o novo resultado do comando.


### Etapa 09.2 — Recuperação de oito artes finais (25/10/2026)
O mestre informou oito pendências após a rotina 09.1: `eevee-parceiro` (Shiny), `frillish` (ambas), `jellicent` (ambas), `minior-nucleo` (ambas), `pikachu-parceiro` (Shiny), `pyroar` (ambas), `zacian-heroi` (ambas), `zamazenta-heroi` (ambas). O sincronizador passou a testar fontes WebP 512px além de PNGs, inclui IDs exatos de cinco espécies problemáticas e oferece `--representativas` para opções explicitamente aproximadas de parceiro/núcleo Minior. Nenhuma migration foi criada; nenhuma alteração é aplicada sem `--aplicar`; resultado de integração PostgreSQL/download pendente de validação do usuário. Ver `docs/IMAGENS_POKEMON_HD.md`.


### Etapa 09.3 — Visibilidade de todos os capturáveis no carrossel (26/10/2026)
- Ajustada a inicialização de `/jogador/capturaveis`: o filtro padrão agora é **Todos os Pokémon**; quando há encontro próprio, ele é apenas o slide inicial selecionado, sem esconder Pokémon de outros jogadores.
- Setas, miniaturas e opção de seleção direta abrangem todos desde a entrada. O filtro **Meus encontrados** continua disponível.
- Arquivos: `templates/capturas/jogador.html`, `static/js/capturaveis.js`, `tests/test_capturaveis_ui.js`, `tests/test_capturaveis_shiny_carrossel.py`. Querystring do JS alterada para evitar cache da versão antiga.
- Correção de interface, sem migration, sem impacto em imagens HD, capturas, Shiny ou Boxes. A validação real pelo mestre permanece pendente.


---

<!-- ANKAR-10A-1-1-2026-10-27 -->
## Versão 10 — Etapa 10A.1.1: auditor das planilhas de Ankar (27/10/2026)

- **Base de código conferida:** commit `871cfaefbb1b6c59a0b001d1f9fa172d38cb1529` (27/10/2026), `main` idêntica a `feature/att-frontend` nessa revisão. Preparada uma entrega incremental para instalação local; nenhuma alteração foi feita no GitHub.
- **Escopo entregue:** serviço `app/services/auditoria_ankar_service.py` e comando `flask --app app.py ankar auditar-planilhas --rotas ... --cidades ...` (texto ou JSON) em leitura exclusiva; separação de local, zona, terreno e entradas, sem deduzir significado dos dados ambíguos. Registrado em `docs/AUDITORIA_PLANILHAS_ANKAR.md`.
- **Planilhas reais analisadas somente leitura:** 73 rotas e 47 abas de cidades/pontos (120 no total); 352 tabelas e 2.683 entradas observadas, com 313 erros e 626 avisos de auditoria no estado atual. Relatório detalhado em `docs/RELATORIO_AUDITORIA_ANKAR_2026-10-27.txt`. Essas contagens não são conteúdo importado/validado.
- **Ocorrências importantes:** sobreposição Pyukumuku 56–60 / Skrelp 60–75 na Rota 1 Água; datas Excel indevidamente interpretadas; tabelas incompletas, intervalos inválidos, `x` e marcadores `Random`. Não converter datas ou `x` automaticamente.
- **Compatibilidade:** registrados novos comandos por Blueprint, `openpyxl>=3.1,<4.0` em `requirements.txt`; nenhum modelo ORM, migration, PostgreSQL, captura, combate ou regras Shiny alterado.
- **Testes neste ambiente:** 10 testes unitários passaram; 1 teste de CLI ficou ignorado por ausência de Flask, Flask-SQLAlchemy e Flask-Migrate no ambiente de trabalho. **Não afirmar integração Flask/PostgreSQL validada** até execução local.
- **Ação seguinte:** instalar, executar `python -m pytest -q tests/test_auditoria_ankar.py`, executar o comando sobre as planilhas reais, revisar erros e relatar resultados. Somente depois planejar aprovação/importação validada da geografia (10A.1.2). Etapas de NPCs, Campo e eventos continuam não implementadas nesta Versão 10.


<!-- ATLAS_ANKAR_V10A2 -->
### Etapa 10A.2 — Atlas visual de Ankar (28/10/2026)
- Entregue catálogo visual **somente leitura** com 119 locais: 73 rotas, 26 cidades e 20 pontos de interesse (352 tabelas, 2.683 entradas).
- Rotas em `/regiao/ankar`; detalhes em `/regiao/ankar/<slug>`; acesso restrito ao mestre para evitar spoilers aos jogadores.
- Fonte estática: `app/data/catalogo_ankar_visual.json`, gerada das duas planilhas originais pelo script `scripts/gerar_catalogo_ankar.py`; fontes não são necessárias em produção para a consulta.
- Habitats principal/secundário, terrenos, acessos, deslocamento/tamanho, descrições, zonas e encontros por terreno são exibidos. `% Captura` não é peso de encontro.
- Datas que o Excel gerou automaticamente a partir de d100 são apresentadas como faixas (dia-mês) mantendo o valor original no JSON. Marcadores `x`, sobreposições e dados incompletos não são alterados.
- Novos módulos: `app/routes/regiao.py`, `app/services/regiao_ankar_service.py`, `templates/regiao/`, `static/css/atlas-ankar.css`, `static/js/atlas-ankar.js`.
- Registro do blueprint e links da navegação inseridos por `scripts/instalar_atlas_ankar.py`, que preserva conteúdo local e é idempotente.
- Nenhuma migration, escrita no PostgreSQL, rolagem de encontros ou atribuição de capturáveis. Validar testes Flask com dependências instaladas e conferir UI local.
- Próxima etapa: revisão visual/conteúdo e só depois discussão do fluxo de encontros, permissões e dados persistidos.


<!-- ATLAS_ANKAR_V10A2_1_UTF8 -->
### Etapa 10A.2.1 — Correção dos testes no Windows (28/10/2026)
- Corrigido `tests/test_atlas_ankar.py`: todas as leituras de arquivos no teste de idempotência agora especificam `encoding='utf-8'`. A codificação padrão `cp1252` do Windows gerava `UnicodeDecodeError` ao ler o diário.
- O instalador, o Atlas visual, os JSON, a navegação, os acessos e as planilhas não sofreram mudanças nesta correção.
- Relato do usuário antes do patch: 9 testes passaram e 1 falhou; aguardar reexecução dos 10 testes no Windows para confirmar a correção no ambiente real.
- **Sem migrations ou escrita no PostgreSQL.**

<!-- ANKAR_10A3_REVISAO_VISUAL -->
### Etapa 10A.3 — Mapa interativo e revisão visual (28/10/2026)
- Integração **somente leitura** do `Mapa.jpg` original em `/regiao/ankar`: 119 marcadores manuais, 73 rotas, 26 cidades e 20 POIs vinculados aos slugs existentes.
- Filtros de pontos, zoom, toque, identificação e links de detalhe; acesso exclusivo do mestre, como na etapa 10A.2.
- CSS do Atlas harmonizado com as variáveis do design system; estilos globais e telas de jogador permanecem inalterados.
- Mapa em `static/img/ankar-mapa.jpg` e posições em `app/data/mapa_ankar_pontos.json`. Não representa caminhos calculados.
- Seis testes de mapa e verificações Chromium isoladas em 390/820/1440 px passaram. Validação integrada do Flask e do site real pendente no ambiente do mestre.
- Sem migration, acesso a PostgreSQL, alteração de planilha ou de contas.
- Detalhes: `docs/REVISAO_VISUAL_ANKAR_10A3.md`.

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
### Etapa 10B.2 — Refinamento da seleção de personagens (28/10/2026)
- Alterações restritas a `templates/entrada_personagens.html` e `static/css/entrada-personagens.css`.
- O décimo slot foi renomeado de Coringa para **Mestre**, com a Pokébola já presente em `static/img/pokebola.png`. A rota de acesso tradicional permanece `entrada_personagens.coringa`.
- Slots dos nove jogadores mantêm exatamente a mesma dimensão visual; sprites exibidas inteiras com `object-fit: contain`, centralizadas e sem corte. A ordem, as imagens dos slots e a configuração de logins permanecem intactas.
- Texto sob o título: apenas “Escolha seu personagem para abrir a ficha.”; textos explicativos do coringa e rodapé removidos.
- Sem alterações na autenticação, sessões, permissões, banco de dados, migrations ou configurações de contas.
- Verificações: executar `python -m pytest -q tests/test_entrada_10b2_visual.py tests/test_entrada_personagens.py tests/test_entrada_personagens_flask.py` no ambiente do projeto.


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
### 2026-10-28 — Etapa 10C.3: reconstrução de itens e efeitos reais
- Escopo: manifesto explícito de 77 códigos legados para 48 itens de destino, com preservação de vínculos e somatório de estoques; remoção de naturezas falsas somente mediante aceite consciente.
- Catálogo reconstruído somente com `--aplicar --confirmar RECONSTRUIR-ANKAR`, após backup de dados e auditoria. Nunca aplicar como efeito colateral da instalação.
- Cura PV/remover condição passa a funcionar ao consumir com seleção do Pokémon, transação conjunta e histórico; sem PP automático.
- Mapa da Região de Ankar: item-chave sem interação, visualizado no inventário em modal com `static/img/ankar-mapa.jpg`.
- Fonte: commit `5a54423` (“Imagens Itens 1”). **Sem migrations**. Integração PostgreSQL não verificada neste ambiente.
- Detalhes em `docs/ETAPA_10C3_RECONSTRUCAO_CATALOGO.md`.

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



<!-- ANKAR_10E1_1_NUMEROS_POKEDEX_20261120 -->
## 2026-11-20 — Etapa 10E.1.1: números nacionais nos cartões do catálogo
- **Contexto:** a 10E.1 foi mesclada pelo PR #8 e ordena corretamente as 1.064 formas por `configuracoes["ordem_catalogo"]`; entretanto, `EspeciePokemon.numero` permanece nulo em registros importados, fazendo a interface mostrar `#—`.
- **Solução incremental:** serviço de apresentação `app/services/numeracao_pokedex_service.py` consulta `data/catalogo/pokemons.json` em memória (cache por processo), atribuindo uma posição nacional a cada um dos 898 nomes-base únicos em ordem original e reutilizando-a em todas as formas; a rota administrativa passa a fornecer a função ao template.
- **Exemplos:** Bulbasaur #001, Venusaur e Venusaur Mega #003, Charmander #004, Nidoran♀ #029, Nidoran♂ #032, Morpeko #877 e Calyrex #898. Para espécies personalizadas, o número manual é respeitado ou o cartão mantém `#—`.
- **Integridade:** nenhuma escrita em PostgreSQL, nenhuma migração, nenhum ajuste em Pokémon de jogadores, nenhuma modificação da fonte JSON; a auditoria e o saneamento definitivo dos registros pertencem à 10E.2.
- **Arquivos:** `app/services/numeracao_pokedex_service.py`, `app/routes/catalogo_admin.py`, `templates/mestre/catalogo/pokemons.html`, `tests/test_ordenacao_pokedex_10e1.py`, `docs/ETAPA_10E1_ORDEM_POKEDEX.md` e os documentos de continuidade.
- **Validação:** testes incluídos no workflow de regressão existente, execução via PR; testes PostgreSQL locais não executados aqui.
- **Próxima tarefa:** auditoria 10E.2 dos números persistidos e das relações de espécies/formas, principalmente Nidoran, sem renumerar automaticamente.


<!-- ANKAR_10E2_1_AUDITORIA_POKEDEX_20261120 -->
## 2026-11-20 — Etapa 10E.2.1: auditoria somente leitura de números e vínculos
- **Base efetiva:** `main` após PR #10 (`2e8f337`); a 10E.1 ordena por `ordem_catalogo` e a 10E.1.1 apresenta números nacionais na lista sem preencher `EspeciePokemon.numero`.
- **Implementação:** `app/services/auditoria_pokedex_service.py` compara a fonte versionada (1.064 formas, 898 espécies) com as espécies, formas e contagens agregadas de Pokémon ativos no PostgreSQL. Identifica números ausentes/incorretos, ligações erradas (Nidoran♂ → espécie Nidoran♀), formas ausentes, divergência da ordem e números customizados coincidentes.
- **Operação:** `flask --app app.py catalogo auditar-pokedex` (primeiros 50 achados), `--todos` (lista integral), `--json` (serialização do relatório). Erros resultam em código não zero; avisos não bloqueiam. Não há opção de reparo ou `--aplicar`.
- **Proteções:** queries SELECT (incluindo contagens agregadas) sob `db.session.no_autoflush`, sem `commit`/UPDATE/DELETE e sem coleta de dados pessoais. Nenhum Pokémon, FK, item, número de espécie ou JSON original alterado; nenhuma migration.
- **Regressão:** `tests/test_auditoria_pokedex_10e2_1.py` + workflow `.github/workflows/test-auditoria-pokedex-10e2.yml`; status dos testes deve ser confirmado na execução do PR. Ver `docs/ETAPA_10E2_1_AUDITORIA_POKEDEX.md`.
- **Pendência e próximo:** rodar o diagnóstico na instalação com dados reais, preservar relatório para análise, aprovar correções pontuais **após backup** e depois criar o editor de relações 10E.2.2. PR #9 antigo permanece separado; não o mesclar sem reconciliar com PR #8/#10.

<!-- ANKAR_10E2_1_2_SANEAMENTO_POKEDEX_20261120 -->
## 2026-11-20 — 10E.2.1.2: saneamento controlado após auditoria real
- **Base:** relatório `auditoria-pokedex.json` adicionado pelo mestre: fonte 898 espécies/1.064 formas, banco 897 espécies/1.066 formas; 2 erros (Nidoran♂ ausente e vínculo `nidoran-2` apontando para Nidoran♀); 897 avisos de número nacional NULL; 2 formas extras preserváveis.
- **Implementação em branch:** `feature/10e2-1-2-saneamento-controlado`, baseada em `main` após merge do PR #11, enquanto o PR #12 de codificação Windows seguia aberto. `codigo_especie_oficial` foi centralizado em `app/services/importacao/utils.py` e consumido por importador e saneamento, para evitar a colisão e dependências circulares.
- **Nova CLI:** `flask --app app.py catalogo sanear-pokedex` simula e imprime SHA256 de estado+fonte; `--aplicar` exige mesma assinatura, `--backup-confirmado` e `--confirmar SANEAR-POKEDEX-ANKAR`. Bloqueia divergências, nomes/ordens inesperados, números já preenchidos incorretamente e fontes modificadas; bloqueio de linhas no PostgreSQL, logs `HistoricoAlteracao`, uma transação, pós-auditoria antes do commit e rollback se necessário.
- **Limite:** apenas preenche números NULL oficiais e cria Nidoran♂/corrige FK da forma original. Não apaga, renumera identificadores, troca Pokémon dos jogadores, faz backup automaticamente nem altera as duas formas adicionais. Nenhuma migration.
- **Documentação:** `docs/ETAPA_10E2_1_2_SANEAMENTO_POKEDEX.md`, plano de evoluções e diário; testes de regressão no workflow `test-saneamento-pokedex-10e2.yml`.
- **Estado:** código preparado, mas **não executado no PostgreSQL real**. Seguir revisão do PR, validação CI, backup realizado e validado pelo mestre, simulação local e autorização explicitamente informada por ele. Só então prosseguir 10E.2.2 editor de vínculos.

<!-- ANKAR_10E2_1_1_WINDOWS_CP1252_20261120 -->
## 2026-11-20 — Correção 10E.2.1.1: auditoria da Pokédex no PowerShell/cp1252
- **Sintoma real informado pelo mestre:** `flask --app app.py catalogo auditar-pokedex --json` sob Python 3.13/Windows falhou no `click.echo` com `UnicodeEncodeError` em `encodings/cp1252.py`, ao tentar exibir Nidoran♂ (U+2642).
- **Causa:** o comando do PR #11 escrevia JSON com `json.dumps(..., ensure_ascii=False)`, e o `stdout` codificado como `cp1252` não comporta símbolos de gênero. Não é falha dos dados do PostgreSQL nem da construção do relatório.
- **Correção:** `app/commands/catalogo.py` usa `ensure_ascii=True` no JSON, mantendo nomes Unicode após leitura por parser, e proteção de emissão da saída em texto, que substitui somente caracteres incompatíveis por escapes `\\uXXXX` (`_texto_compativel_saida`).
- **Testes:** `tests/test_auditoria_pokedex_10e2_1.py` incorpora simulação de `cp1252`, parse JSON e preservação semântica de Nidoran♂. Confirmar resultado CI na branch `fix/10e2-1-auditoria-windows-encoding`.
- **Banco e esquema:** sem migrations, sem alterações no PostgreSQL, fichas ou `data/catalogo`.
- **Próximo:** mesclar correção após CI; obter o relatório da instalação Windows; revisar erros antes de qualquer saneamento real da 10E.2.


<!-- ANKAR_10E2_2_EDITOR_RELACOES_20261120 -->
## 2026-11-20 — Etapa 10E.2.2: edição de evoluções e formas no Catálogo
- **Contexto:** saneamento 10E.2.1.2 concluído pelo mestre, com auditoria reportada de 898 espécies, 1066 formas, zero erros e avisos. O código da nova etapa foi criado após verificar que PR #12 e #13 já estavam mesclados na main.
- **Fontes verificadas:** PDF `pkmrpg-playtest-2_5.pdf`, cap. 9 pp. 44–45 (evolução opcional por nível, amizade, item; Mega temporária); cap. 16 p. 60 (pedras Mega); PokéAPI `/api/v2/evolution-chain/{id}/` (cadeias 1, 2, 3); Pokémon Database `/evolution/level`. Hierarquia: regras de Ankar > manual > jogos. Não reintroduzir amizade individual, experiência ou mudança automática de forma.
- **Funcionalidade:** `app/services/evolucoes_admin_service.py`, rotas `/mestre/catalogo/pokemons/<id>/relacoes`, template `pokemon_relacoes.html` e links nos cartões/edição. Relações de entrada/saída, criação, edição, desativação, histórico. Tipos: evolução permanente, Mega temporária, alternativa reversível e parentesco regional. Valida pré-condições, duplicação e ciclos apenas nas evoluções permanentes.
- **Dados referenciados:** seis sugestões cruzadas de iniciais em `data/referencias/evolucoes_verificadas_10e2.json`. Só registra após clique explícito do mestre; nenhuma importação automática nem consulta externa em runtime.
- **Modelagem:** reaproveita `EvolucaoPokemon.tipo_requisito` para gatilho e `requisitos['tipo_relacao']` para natureza do vínculo. Sem migration, sem tocar nos Pokémon dos jogadores, itens, PV ou nível de treinador.
- **Testes:** `tests/test_evolucoes_admin_10e2_2.py`, workflow `.github/workflows/test-evolucoes-10e2-2.yml`; verificar execução na PR. Ver `docs/ETAPA_10E2_2_RELACOES_POKEMON.md`.
- **Próximo:** verificar CI, revisar na interface, depois 10E.2.3 árvore visual e comparações das demais famílias; 10E.3 elegibilidade real sob as regras de Ankar.


<!-- ANKAR_10E2_3_ARVORE_20261120 -->
## 2026-11-20 — 10E.2.3: árvore evolutiva e revisão de cadeias divergentes
- **PR/branch:** `feature/10e2-3-arvore-evolutiva`, criada da main após PR #14 (editor de relações) ser mesclado.
- **Objetivo:** nova rota de leitura `/mestre/catalogo/pokemons/<forma_id>/arvore`, acessível pelo editor. Inclui raízes, ancestrais, ramos, convergências, estágios e requisitos das evoluções permanentes ativas. Outros tipos de relação aparecem à parte. Detector de ciclos legados, cap de 120 nós e estado vazio.
- **Arquivos:** `app/services/arvore_evolutiva_service.py`, `templates/mestre/catalogo/pokemon_arvore.html`, `static/css/arvore-evolutiva.css`, `app/routes/catalogo_admin.py`, `app/services/evolucoes_admin_service.py`, `templates/mestre/catalogo/pokemon_relacoes.html`, `data/referencias/evolucoes_revisadas_10e2_3.json`, `tests/test_arvore_evolutiva_10e2_3.py`, workflow `test-arvore-evolutiva-10e2-3.yml`, docs da etapa/continuidade/diário/plano.
- **Fontes:** PDF original cap. 9 página impressa 44 (PDF 45), cap. 16 páginas impressas 59–60 (PDF 60–61); PokéAPI evolution chain 67 (Eevee) e 10 (Pichu/Pikachu); PokémonDB stone/trade e Pokédex Eevee. Comparações feitas individualmente e documentadas.
- **Novas propostas:** 12: sete por pedra liberadas somente após clique mestre (5 ramos de Eevee, Pikachu, Vulpix padrão), cinco pendentes de regra da campanha (Espeon/Umbreon/Sylveon e Porygon→Porygon2→Porygon-Z). Pendentes não são aprováveis por endpoint nem importadas automaticamente.
- **Conflito importante:** livro PKMRPG v2.5 condiciona materiais a amizade máxima 100; Ankar não usa amizade numérica. O editor exibe alerta; aprovação do mestre é registro de regra, não execução da evolução. Trocas de Porygon e variantes Eevee diferem entre livro e jogos, pendentes de decisão.
- **Sem migrations / sem mutação:** navegação da árvore é somente SELECT; sugestões armazenadas em JSON versionado não alteram catálogo até aprovação; nenhuma evolução/mega mudança de Pokémon do jogador é ativada.
- **Testes:** `tests/test_arvore_evolutiva_10e2_3.py`, com testes de ramos, convergência, ciclo legado, tipos especiais, acesso e manutenção dos Pokémon do jogador. Confirmar resultados no CI do PR. Próximo 10E.3 evoluções na ficha, com nível de treinador e autorização narrativa.


<!-- ANKAR_10E2_4_POKEDEX_EVOLUTIVA_20261120 -->
## 2026-11-20 — Etapa 10E.2.4: geração integral das árvores da Pokédex
- **Pedido:** mestre quer cadastrar automaticamente **todas** as evoluções oficiais por nível puro e pedras comuns. Outras condições dependem de liberação pelo mestre, em especial Eevee→Umbreon, Espeon e Sylveon.
- **Fonte e auditoria:** 898 espécies da Pokédex Ankar, cruzadas com PokeAPI/pokeapi `pokemon_species.csv`, `pokemon_evolution.csv`, `items.csv`, Pokémon Database e manual cap. 9 e cap. 16. **430 relações:** 297 por nível sem condição adicional, 43 por pedras comuns, 90 especiais. O CSV completo e classificado está em `data/referencias/pokedex_evolucoes_898_10e2_4.json`, com rastreabilidade por linha/versão.
- **Linhagens regionais:** relações que dependem da forma Galar usam códigos exatos, não espécies genéricas: Meowth (Galar)→Perrserker, Corsola (Galar)→Cursola, Mr. Mime (Galar)→Mr. Rime. Linhagens condicionais de Galar permanecem restritas. Nidoran♀/♂ continuam distintos. Vivillon nível 12 foi conservado, mesmo com variantes de padrão.
- **Implementação:** `app/services/importacao_evolucoes_service.py` planeja e adiciona links sem sobrescrever relações existentes; CLI `flask --app app.py catalogo gerar-arvores-pokemon`, UI `/mestre/catalogo/pokemons/gerar-arvores` com prévia, assinatura do estado, backup confirmado, frase de autorização e token de formulário. Históricos e commits transacionais, sem migration.
- **Controle futuro:** relações especiais usam `requisitos.requer_liberacao_mestre` e `liberacao_individual`; guarda conservadora também cobre relações legadas. O editor preserva a restrição ao editar; a árvore a sinaliza. A autenticação e liberação REAL por Pokémon, com execução da evolução, ainda é tarefa da 10E.3.
- **Divergência PKMRPG:** livro p. 59 exige amizade 100 para qualquer material; amizade numérica retirada de Ankar. Pedido explícito libera pedras comuns sem esse requisito no cadastro, mas não define consumo/ativação automática. Itens especiais requerem mestre.
- **Proteções:** consulta/simulação read-only, aplicação aditiva, não apagar/alterar vínculos antigos, trava e assinatura, backup externo informado, não tocar em Box/natureza/PV/IV/nível, idempotência. Sem alterações de esquema.
- **Arquivo de referência:** `docs/ETAPA_10E2_4_GERACAO_COMPLETA_EVOLUCOES.md`; testes `tests/test_importacao_evolucoes_10e2_4.py` e workflow `test-importacao-evolucoes-10e2-4.yml`. Validar CI e depois homologar geração real no PostgreSQL.


<!-- ANKAR_10E2_5_REGIONAIS_20261120 -->
## 2026-11-20 — 10E.2.5: revisão e complemento das formas regionais
- **Pedido:** mestre importou grande parte das árvores, mas percebeu ausência sistemática das famílias de Alola/Galar. Foi auditado o `data/catalogo/pokemons.json` e o arquivo `pokedex_evolucoes_898_10e2_4.json` da main (PR #16 já mesclado). São 38 formas regionais ou correlatas: 18 Alola sem vínculo, 18 Galar com seis vínculos anteriores, mais duas formas de Darmanitan Galar.
- **Causa:** a primeira importação operava por espécie, não por `required_pokemon_form_id` / `evolved_pokemon_form_id` / `region_id` da PokéAPI; caminhos de variantes regionais não apareciam mesmo com código das formas no catálogo. A análise não consultou o PostgreSQL real, e formas sem evolução não são erros.
- **Fonte:** novos 17 caminhos regionais revisados nos CSV `pokemon_evolution.csv` da PokéAPI, Pokémon Database e adaptações do manual. Documento `docs/ETAPA_10E2_5_EVOLUCOES_REGIONAIS.md` contém tabela completa de oito vínculos simples e nove especiais.
- **Alterações:** `data/referencias/evolucoes_regionais_10e2_5.json`; `app/services/importacao_evolucoes_service.py` com loader e plano isolado regional; comando `flask --app app.py catalogo completar-arvores-regionais`; rota mestre `/mestre/catalogo/pokemons/gerar-arvores?regionais=1`; template `gerar_arvores_pokemon.html` em modo regional; link `Completar árvores regionais` na lista do catálogo; testes/CI e docs.
- **Segurança:** importação só com simulação, assinatura, backup confirmado e `COMPLETAR-REGIONAIS-ANKAR`, mantendo os 430 vínculos anteriores intocados. Não apaga/reativa relações personalizadas, não muda Pokémon de jogadores e não utiliza migrations.
- **Regra Ankar:** 8 novos arcos regulares por nível/pedra, 9 reservados ao mestre (noite, região, amizade, troca, Galarica Cuff/Wreath). Darmanitan Zen é alternância de modo e fica para 10E.4; 10E.3 evoluções efetivas individuais.
- **Testes:** `tests/test_evolucoes_regionais_10e2_5.py`, workflow `test-evolucoes-regionais-10e2-5.yml`, resultado a verificar na CI.


<!-- ANKAR_10E3_1_ELEGIBILIDADE_20261120 -->
## 2026-11-20 — 10E.3.1: consultar evoluções possíveis por Pokémon
- **Confirmação do mestre:** as árvores regionais 10E.2.5 já foram aplicadas no PostgreSQL local da campanha. Não executar importação novamente nesta etapa.
- **Objetivo:** exibir na ficha de equipe/Box (tanto rota do jogador quanto mestre) as evoluções disponíveis ao Pokémon **específico**, com estado calculado a partir de `personagens.nivel`, relação permanente ativa e pedra real na mochila (`personagem_itens`).
- **Regras:** quatro estados — requisito atendido, nível insuficiente, pedra ausente, depende do mestre. Itens não são consumidos; evolução ainda não é oferecida. O nível segue compartilhado e não há amizade/XP individual. Regiões e formas são distintas pelo UUID exato da origem.
- **Proteção:** requisitos de amizade/troca/condição/itens especiais, flags mestre, sexo, horário, região e metadados ambíguos sempre ficam restritos. `aprovado_mestre` no catálogo não é autorização por Pokémon. O Pokémon precisa pertencer ao personagem autorizado pela sessão nas rotas existentes.
- **Arquivos:** serviço `app/services/consulta_evolucao_service.py`; integração em `app/routes/pokemons.py`; seção read-only em `templates/jogador/pokemon.html`; CSS `static/css/pokemon.css`; `tests/test_consulta_evolucao_10e3_1.py`; CI `test-elegibilidade-evolucao-10e3-1.yml`; documentação `docs/ETAPA_10E3_1_CONSULTA_ELEGIBILIDADE.md`, plano/continuidade/diário.
- **Bancos/migrations:** zero alterações de esquema e zero escrita automática. A consulta à ficha não cria, grava ou confirma evoluções, não muda Box, PV, atributos, ataques, inventário ou identidade. CI é SQLite; homologar no PostgreSQL real após merge.
- **Próxima:** 10E.3.2 autorização persistida e individual por relação+Pokémon, com perfis de mestre, trilha de auditoria e proteção por transação; após, botão de evolução e consumo com recálculo.


<!-- ANKAR_10E3_2_AUTORIZACAO_20261120 -->
## 2026-11-20 — 10E.3.2: liberação individual de evolução por Pokémon
- **Estado inicial:** PR #18 da elegibilidade 10E.3.1 já mesclado em `main`. Usuário confirmou que complemento regional 10E.2.5 já foi aplicado ao PostgreSQL de Ankar; NÃO reimportar árvores.
- **Objetivo:** mestre autoriza ou revoga um destino evolutivo especial para um Pokémon individual (não espécie inteira). Ex.: autorizar Eevee Lua→Umbreon não libera Eevee Sol nem Espeon. Pokémon não evoluem automaticamente, não se consome item nem se recalculam atributos nesta etapa.
- **Schema novo:** modelo `app/models/db/pokemon_evolution_auth.py` e migration `migrations/versions/b93e21c031a2_autorizacao_evolucao_individual.py` com `down_revision=a14d4e4044a1`; tabela `autorizacoes_evolucao_pokemon` de par único Pokémon/relação, origem, mestre autor, justificativa, status, data e motivo da revogação. `app/models/db/__init__.py` atualizado. Downgrade bloqueia perda de registros existentes. Fazer backup real antes de `flask --app app.py db upgrade`.
- **Serviço:** `app/services/autorizacao_evolucao_service.py` verifica ator ativo e perfil, presença do mestre na campanha, personagem/Pokémon, origem e destino ativos, condição especial e bloqueia decisões concorrentes na linha do Pokémon. Autorizar/revogar é idempotente e registram `HistoricoAlteracao`; alterações de forma via `pokemon_db_service.py` invalidam permissões na mesma transação.
- **Rotas/visão:** `app/routes/pokemons.py` com endpoints mestre POST autorizar/revogar protegidos por sessão/CSRF; `app/services/consulta_evolucao_service.py` marca o ramo liberado só para a instância+origem atual; painel na ficha `templates/jogador/pokemon.html`, CSS `static/css/pokemon.css`. O jogador vê apenas o status.
- **Testes:** `tests/test_autorizacao_evolucao_10e3_2.py`, workflow `test-autorizacao-evolucao-10e3-2.yml` e regressões anteriores. Confirmar CI e validar migration no PostgreSQL real após merge; testes CI usam SQLite.
- **Limites:** nenhum botão de evolução, nenhuma mudança de `Pokemon.forma_pokemon_id` por autorização, nenhum consumo de item ou recálculo. Evolução real e inventário transacional na 10E.3.3/4.


<!-- ANKAR_10E3_3_4_EVOLUCAO_EFETIVA_20261120 -->
## 2026-11-20 — Evolução permanente opt-in e atomicidade 10E.3.3/4
- **Pedido:** após mestre confirmar que encontrou as permissões especiais, avançar para evolução real. PR #19 da 10E.3.2 já mesclado; nesta etapa não reimportar árvores, não executar alterações em PostgreSQL remoto.
- **Fluxo:** jogador na própria ficha encontra `Evoluir para ...` somente se `pode_evoluir`; tela exige confirmação via JS, formulário com token CSRF, POST exclusivo do jogador. Mestre continua autorizando caminhos especiais, mas não inicia evolução na ficha do jogador.
- **Serviço:** `app/services/evolucao_efetiva_service.py` valida dono via `Usuario`/campanha/personagem, Pokémon ativo fora do Campo, origem/destino e vínculo ativos, nível compartilhado, permissão individual especial vigente, material real ativo/consumível; locks `FOR UPDATE`; faz flush sem commit, endpoint comita só após todos os passos ou faz rollback.
- **Itens:** `app/services/materiais_evolucao_service.py` usa mapeamento explícito de dez pedras e materiais especiais do PKMRPG v2.5 cap. 16/PokéAPI, correspondência exata de código/nome; requer estoque do mesmo personagem, consome uma unidade na mesma transação, audita, não usa equipamento fora da mochila, bloqueia item desconhecido/não consumível. Ex.: Galarica Cuff/Wreath exigem mestre e item.
- **PV/atributos:** `calcular_pokemon` refaz os atributos da nova `FormaPokemon` com a regra vigente, nível igual do treinador, Shiny/natureza/bônus/status; `pv_atual` preserva o dano absoluto, Pokémon desmaiado permanece com 0. Esta política de PV é adaptação de engenharia, não regra expressa no manual. Conserva UUID, golpes, posição, Box, item equipado, apelido, natureza, Shiny e anotação.
- **Autorizações:** ao mudar de forma por evolução, todas permissões anteriores do Pokémon são encerradas transacionalmente com motivo correto; não podem ser reutilizadas. Relacionamentos não permanentes como Mega não são evoluídos.
- **Rotas/UI:** `app/routes/pokemons.py`, `templates/jogador/pokemon.html`, `static/css/pokemon.css`, `static/js/pokemon.js`, serviço de consulta fornece `pode_evoluir` e `bloqueio_execucao`.
- **Testes/docs:** `tests/test_evolucao_efetiva_10e3_3_4.py`, CI `test-evolucao-efetiva-10e3-3-4.yml` e `docs/ETAPA_10E3_3_4_EVOLUCAO_EFETIVA.md`. Sem migration nova; confirmar que a migration `b93e21c031a2` da 10E.3.2 está aplicada na instalação.
- **Próximo:** 10E.4 formas temporárias/Megas, política separada da evolução permanente.


<!-- ANKAR_CORRECAO_EVOLUCAO_TESTER_URL_20261120 -->
## 2026-11-20 — Correção de acesso à evolução para tester e ficha /p/<login> (após PR #20)
- **Relato:** ao confirmar `Evoluir`, a aplicação mostrava a página branca `A evolução deve ser solicitada pelo dono do Pokémon.`. O serviço `evolucao_efetiva_service.py` só aceitava `Usuario.perfil == 'jogador'`, mas `perfil_obrigatorio('jogador')` admite também `tester` via `PERFIS_JOGADOR`. Assim, a conta tester com Pokémon próprio passava pela rota e era barrada pelo serviço. Não foi possível identificar o perfil exato do usuário a partir da captura; esta é uma incompatibilidade de código comprovada.
- **Outra falha:** `app/services/fichas_url_service.py` não incluía `pokemons.evoluir_jogador` na allowlist da ficha isolada `/p/<login>/`, bloqueando POSTs válidos nesse acesso.
- **Correção:** o serviço admite jogador **ou tester** ativos, mas continua exigindo `Personagem.usuario_id == usuario.id` e o Pokémon da personagem/campanha atual. A allowlist inclui **apenas** a ação pessoal de evoluir, não endpoints de mestre. Um `PermissionError` residual agora faz rollback, mostra mensagem amigável na ficha e registra warning, sem página branca.
- **Arquivos:** `app/services/evolucao_efetiva_service.py`, `app/services/fichas_url_service.py`, `app/routes/pokemons.py`, `tests/test_correcao_evolucao_tester_url.py`, CI `test-correcao-evolucao-tester-url.yml`, docs/diário. Sem migration, sem reimportação, sem alteração ao PostgreSQL real por esta entrega.
- **Regressões:** testar (1) conta tester evoluindo Pokémon próprio; (2) ficha isolada `/p/bartz-db` evoluindo e preservando a sessão do mestre em outra aba; (3) negação do mestre/outro usuário e (4) suites anteriores de autorização/consulta de evolução.


<!-- ANKAR_10E4_MEGAS_ALTERNATIVAS_20261120 -->
## 2026-11-20 — 10E.4: Mega por autorização do treinador, alternativas por escolha do dono
- **Decisão EXPRESSA do mestre:** (1) Formas alternativas — como Morpeko — são permitidas ao próprio Pokémon e seu dono sem liberação individual. (2) Mega Evolução requer **permissão ao treinador** que o mestre pode conceder/revogar, **sem exigência de Pedra Chave, Mega Pedras ou golpe específico**. Esta decisão prevalece sobre condicionantes do manual e sobre rascunhos preliminares da 10E.4.
- **Implementação:** migration `c42e10040001` sobre `b93e21c031a2` cria `personagens.mega_habilitada` (false por default) e `pokemons.forma_temporaria_id`/`tipo_transformacao` com check. Não afeta `Pokemon.forma_pokemon_id` permanente. Migrations só após backup/deploy, NÃO executadas no PostgreSQL da campanha.
- **Serviço:** `app/services/transformacoes_service.py`; 48 Megas + 46 vínculos alternativos revisados em `data/referencias/transformacoes_10e4.json`; formas disponíveis de mesma espécie/categoria apropriada, sem Mega de outras espécies ou regionais arbitrárias. Alternativas livres pelo dono; Mega requer personagem habilitado e no Campo, limite de uma ativa por treinador, sem itens. Locks da linha do Personagem e Pokémon; auditoria de concessão, mudança e reversão.
- **Interface:** mestre concede/revoga Mega em `Campo → Permissões de Mega Evolução`; jogador ativa Mega no próprio Pokémon em Campo; alterna formas na ficha ou Campo, com retorno à forma original. `/p/<login>/` mantém acesso isolado de jogador ao POST de transformações de sua própria ficha.
- **Integrações:** `pokemon_db_service.calcular_pokemon` lê forma overlay para atributos, sem sobrescrever espécie persistente; PV preservam dano já sofrido/zero quando KO. `campo_service` mostra sprite e tipos ativos e reverte Mega quando retirada/limpeza; `evolucao_efetiva_service` bloqueia permanente com forma temporária ativa; edição manual de forma remove overlay; mestras revogando permissão encerram Megas ativas. Campo não automatiza habilidades, turnos e clima (ex. Morpeko).
- **Arquivos:** migrations, models de Personagem/Pokemon/FormaPokemon, services `transformacoes_service.py`/`campo_service.py`/`pokemon_db_service.py`/`evolucao_efetiva_service.py`, rotas `combates.py`/`pokemons.py`, `fichas_url_service.py`, templates e CSS/JS de Campo/ficha, `tests/test_mega_alternativas_10e4.py`, workflow dedicado, doc `ETAPA_10E4_MEGAS_FORMAS_ALTERNATIVAS.md`.
- **Testes:** CI e regressão pendentes de confirmação nesta entrada, usam SQLite; PostgreSQL a homologar após merge e upgrade. Sem alterações de dados reais feitas pelo assistente.


<!-- ANKAR_10E4_1_EXPANDIDO_VISUAL_20261120 -->
## 2026-11-20 — 10E.4.1: ações integradas ao painel expandido + Mega no ⋮
- **Decisão do mestre:** UMA implantação para revisar toda a UX. Evolução permanente e formas temporárias/Mega devem ser executadas **no painel expandido do Pokémon** (dashboard do jogador), não em tela separada ou Campo. Evolução pronta tem indicador **vermelho**; formas/Mega têm indicador **azul**. Uma alternativa mostra **sprite+nome diretamente**; várias mostram **Mudar de forma** com menu sprite+nome; Mega mostra **ícone da Mega Pedra + Mega Evoluir**, com escolha X/Y quando múltipla.
- **Permissão Mega:** saiu da interface do Campo, entrou nos **três pontinhos (⋮)** do cartão do treinador no Painel Mestre, com ícone de Mega Pedra e switch habilitar/revogar. Segue por Personagem, não Pokémon; sem pedras, usando `permitir_mega_treinador` validado pelo backend e CSRF do mestre.
- **Arquivos:** novo `app/services/painel_acoes_pokemon_service.py`; atualização `app/routes/jogadores.py`, `app/routes/mestre.py`, `app/routes/pokemons.py`, `app/services/painel_mestre_service.py`; templates `jogador/dashboard.html`, `mestre/dashboard.html`, `jogador/pokemon.html`, `campo/painel.html` e `campo/_times.html`; `dashboard.css`, `painel-mestre-10d3.css`, `dashboard-pokemon.js`; três ícones SVG originais; regressões/testes. Revisão descrita em `docs/ETAPA_10E4_1_PAINEL_EXPANDIDO.md`.
- **Fluxo:** dashboard injeta CSRF e elegibilidade por Pokémon; ações reais reutilizam rotas do jogador/serviços existentes. Após POST com origem `painel`, redirect `?foco=<id>` reabre o mesmo expandido. Em master preview, controles de evolução e transformação não aparecem. Em Campo, ficam só os estados, sprites e tipos.
- **Banco:** não há migration nesta revisão. Requer a migration anterior `c42e10040001` já aplicada; sem escrita em Pokémon reais ou permissões da campanha pelo assistente. Regressões e CI a confirmar.


## Atualização 10E.4.1 — Keystone e aviso de Mega (20/11/2026)

A Mega Evolução segue sendo uma permissão concedida ao treinador pelo mestre, sem pedras/inventário, com ativação apenas no Campo e uma Mega por treinador. A interface expandida agora reaproveita o PNG local `static/img/inventory/itens/keystone.png` para todas as ações Mega (jogador e mestre); o SVG ilustrativo antigo deixou de ser referenciado. Seletores CSS do retrato do Pokémon usam `> img`, evitando que as imagens de botões sejam ampliadas e cortadas. As razões de indisponibilidade da Mega são apresentadas explicitamente no painel e incluem outra Mega ativa. Nenhuma migration ou atualização do PostgreSQL foi aplicada pelo assistente.


## Continuidade 10E.4.2 — Ícones acionáveis e Campo pausado

Regra atual: Campo é **visualização de combate**, não pré-requisito para evolução ou Mega. A Mega depende apenas de permissão do mestre, dono, Pokémon consciente, destino válido e uma Mega ativa por treinador. Os comandos de evolução (esquerda) e formas/Mega/reversão (direita) são ícones de verdade sobre o retrato expandido. Uma ação funciona diretamente com confirmação; várias abrem menu de destino com sprites. Os botões sob os golpes foram removidos.

Campo tem `CAMPO_ATIVO=False` por padrão e `CAMPO_OPERACOES_ATIVAS=False`. Nenhuma rota POST antiga pode operar quando pausado, e a visualização opt-in é somente demonstrativa. Catálogo NPC e Capturáveis são áreas oficiais para preparação fora de batalha; hordas antigas podem ser encaminhadas à captura sem Campo. Manter dados, serviços, modelos e migrations do Campo para etapa futura. Consultar `docs/ETAPA_10E4_2_RETRATO_E_CAMPO_PAUSADO.md`.
