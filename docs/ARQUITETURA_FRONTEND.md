# Arquitetura visual do Pokémon RPG

**Padrão atual — 21/11/2026 (ajuste 10F.1).** O objetivo é manter um único sistema de componentes que sirva a jogador, mestre e NPC sem alterar lógica de autorização, dados ou regras de Ankar.

## Responsabilidades de cada camada

1. `static/css/geral.css`: estilos básicos HTML, paleta clara, botões e cartões originais.
2. `{% block estilos %}`: CSS específicos da página, sem regras globais `body`, `.topo`, `html` ou `.conteudo`.
3. `static/css/tema.css`: variáveis escuras e ajustes de elementos antigos que usam cores literais.
4. `static/css/tipos.css` e `static/css/seletor-visual.css`: componentes funcionais.
5. `{% block estilos_finais %}`: extensões locais existentes (evitar criar novas sem necessidade).
6. **`static/css/sistema-ui.css`**: **autoridade** dos tokens `--ui-*`, densidade operacional, controles e prevenção de overflow.
7. `pokemon-hd.css`, toast e `visual-global-10c5.css`: mídias, notificações e navegação responsiva.
8. `padrao-visual-10d1.css`: apresentação dos títulos e menu de contexto.

A folha legada `refinamento.css` foi absorvida por `sistema-ui.css`. Não reintroduzir seletores que escondem títulos para depois mostrá-los em outra folha.

## Navegação responsiva — contrato 10F.1

- O layout, a visibilidade e o posicionamento de `.topo`, `.marca`, `.navegacao-principal`, `.usuario-topo` e `.ui-mobile-nav-toggle` pertencem a `static/css/visual-global-10c5.css`. O CSS `geral.css` fornece apenas a base legada; `sistema-ui.css` não deve adicionar seletores `body.app-shell` para reorganizar esses elementos.
- Até **1100px**, a navegação principal começa recolhida (`display: none`) e só aparece com `.topo[data-ui-nav-open="true"]`. O botão Menu permanece na primeira linha, as ações de conta na segunda e o menu aberto na terceira. Até **900px**, o nome do usuário não ocupa espaço no cabeçalho.
- Acima de **1100px**, o menu fica visível em linha e o botão Menu permanece oculto. Cada link continua sendo decidido pelo template conforme o perfil e as permissões.
- O script `static/js/visual-navegacao-10c5.js` mantém `aria-expanded`, `aria-label`, fechamento ao clicar fora e pela tecla Escape, além de recolher o menu ao cruzar o breakpoint. Não duplicar esse controle em outras folhas de estilo.
- O template `base.html` deve atualizar a versão de cache de **ambas** as folhas CSS envolvidas em qualquer mudança na navegação.

**Regressão estática:** `tests/test_navegacao_mobile_10f1.py` confere a separação de responsabilidade, os estados do menu, os breakpoints e os recursos do template/script. `tests/test_sistema_ui.py` preserva os demais contratos de componentes. Ambos integram o workflow `test-contrato-ui-repositorio.yml`.

**Validação manual complementar:** conferir largura 320, 390, 768, 900, 901, 1100, 1101 e 1440px, em claro/escuro e com zoom de 200%. Testar mestre, jogador, prévia de mestre e URLs de ficha; abrir/fechar Menu, selecionar link, usar Escape, clicar fora, alternar tamanho da janela e conferir que ações de conta permanecem acessíveis. Essa inspeção real em navegador não é coberta pelos testes estáticos.


## Inventário mobile — contrato 10F.2

- A disposição horizontal da equipe até 799px é definida em `static/css/visual-inventario-10c5.css`: `.inventario-nds-equipe-lista` usa `display: flex`, `overflow-x: auto` e cartões com `flex: 0 0 224px`. Isso permite rolar pelos Pokémon sem ampliar a largura do documento.
- `static/css/sistema-ui.css` continua protegendo textos longos e barras de PV, mas **não** pode forçar `overflow-x: hidden` no carrossel nem sobrescrever as dimensões de cards/fotos em celular e tablet. Valores compactos globais de cards só se aplicam a partir de 1200px.
- A faixa `.inventario-nds-abas` já tem rolagem horizontal; `static/js/inventario.js` centraliza **apenas a faixa** na aba selecionada, inclusive quando a mochila inicia na primeira categoria com itens. Não usar `scrollIntoView()` que também possa saltar a página inteira.
- Em mudanças de layout ou JavaScript, atualizar os parâmetros `v=` do CSS global e do JS no template, para evitar cache móvel.

**Regressão:** `tests/test_inventario_mobile_10f2.py` examina a cascata global, o contrato CSS responsivo, a seleção da aba e a versão de cache. O workflow de contrato visual executa esses testes sem banco. Conferir manualmente em Android/Chrome, 320–430px, retrato/paisagem, zoom 200%, equipe com 1–6 Pokémon e bolsas com itens em categorias à direita.

## Inventário mobile — complemento 10F.3

O print do celular mostrou uma faixa escura extra à direita, mesmo após 10F.2. O CSS tinha uma arte decorativa absoluta (`.inventario-nds-bag::after`) com `right: -120px`, enquanto a camada responsiva deixava `.inventario-nds-bag` com `overflow: visible` para preservar controles flutuantes. Portanto, o desenho podia ampliar a área horizontal rolável da página.

- Até **1199px**, manter a decoração dentro do painel com `right: 0` e `width: min(380px, 100%)`. Não trocar o overflow do painel para `hidden`, pois isso pode cortar o autocomplete do mestre.
- Até **540px**, exibir as cinco abas em **grade de duas colunas**, com texto quebrável e botões completos; não depender de rolagem horizontal para encontrar Item-chave. De 541px a 1199px, preservar a faixa horizontal já existente; acima disso, manter o layout desktop.
- O JavaScript `inventario.js` continua gerenciando seleção/teclado e só rola abas quando a faixa de fato ultrapassa sua largura. Não alterar regras de itens.
- Atualizar a versão do CSS específico do inventário no template ao alterar esses breakpoints.

**Teste estático:** `tests/test_inventario_largura_10f3.py`, integrado ao workflow de contrato visual. **Verificação manual obrigatória:** confirmar em Android Chrome a largura do cabeçalho e da Bag, ausência de faixa vazia à direita e cinco categorias visíveis em 320px e 390px. Validar também o autocomplete do mestre e a rolagem da equipe; CI estática não substitui inspeção de layout no navegador.

## Dashboard Pokémon em notebooks de pouca altura — contrato 10F.4

O modo de foco de `static/css/dashboard.css` é compartilhado pelo dashboard do jogador e pelo painel do NPC. Em desktop com altura suficiente (`min-width: 901px`), permanece a apresentação compacta sem rolagem da página. A regra de exceção para **largura a partir de 901px e altura até 760px** impede que essa apresentação corte dados e controles.

- Na exceção, `body.dashboard-foco-aberto` retoma `overflow-y: auto`, `.dashboard-jogador` e `.grade-pokemons-dashboard.dashboard-pokemon-modo-foco` passam a ter altura natural.
- O card em foco, os detalhes, os golpes e as anotações podem crescer sem `overflow: hidden`; os demais Pokémon permanecem na coluna lateral com altura natural. A coluna do treinador deixa de ser sticky somente nessa condição.
- Não modificar o comportamento do `dashboard-pokemon.js`, seus modais, formulários, ações de retrato nem rotas. A correção é de layout; o estado de foco e o retorno por Esc permanecem iguais.
- Ao alterar a folha compartilhada, atualizar seu parâmetro de cache em `templates/jogador/dashboard.html` e `templates/mestre/catalogo/npc_painel.html`.

**Regressão estática:** `tests/test_dashboard_foco_baixa_altura_10f4.py`, integrado à suíte de contrato visual, verifica a exceção de altura, o desktop preservado, controles e os dois templates. **Validação visual complementar:** conferir 1024×600, 1366×768, 1440×900, navegador com zoom 200%, jogador e NPC, equipe de 1 a 6 Pokémon, modal de confirmação, botões Recolher/Editar e opções de Mega/forma. Teste de CSS não substitui uso real no navegador.

## Identidade do personagem e quadro de atributos — contrato 10F.5

- O painel do jogador recebe seu sprite a partir da configuração **já validada** de `data/entrada_personagens.json` (`configuracao_login()`), consultando `sprite_personagem_por_login(ficha.personagem.usuario.login)`. O mesmo mapeamento é usado na prévia autenticada do mestre. Nunca selecionar um sprite pela posição do personagem na tela nem pelo texto de seu nome.
- Se um slot não possui sprite local válido, o dashboard preserva a imagem `foto_url` anterior ou a inicial, sem gravar nada no PostgreSQL. O arquivo original da foto continua editável na ficha.
- O ícone do treinador em `templates/jogador/dashboard.html` é um link com rótulo acessível para `dashboard_ficha_url`. Esse destino usa `jogadores.ficha` para jogador e `mestre.ficha_jogador` na prévia; as rotas, permissões, edição de atributos e botão **Editar** continuam intactos.
- O menu de `templates/base.html` não mostra mais `Minha ficha` nos perfis jogador e prévia. A página **não foi excluída**; apenas seu acesso principal saiu da barra de navegação.
- Para que `.painel-atributos-treinador` não encolha ao expandir um Pokémon, `dashboard-pokemon.js` mede a altura **antes** de aplicar a classe `dashboard-foco-aberto`, atribui-a à variável CSS `--dashboard-altura-atributos-original` e a remove ao recolher o Pokémon. O CSS aplica essa altura mínima somente em `.dashboard-jogador:not(.npc-painel)`; o NPC não recebe esse ajuste.
- Atualizar o cache de `dashboard.css` e `dashboard-pokemon.js` nos templates de jogador e NPC quando houver alterações nesses arquivos compartilhados.

**Regressão:** `tests/test_dashboard_sprite_ficha_atributos_10f5.py` valida o mapeamento por login, o link da ficha, a fallback de foto e a preservação do quadro, no workflow visual. `tests/test_fichas_por_url_10b3_flask.py` verifica que duas URLs de personagem exibem sprites distintos, com base na configuração isolada do próprio teste. Testar no navegador abertura/recolhimento do Pokémon, zoom de 200%, troca de perfil, prévia do mestre e acesso por URL de ficha. Não remover as rotas GET/POST da ficha.

## Auditoria de telas em Chromium — contrato 10F.7

A partir da etapa 10F.6, `tests/visual/` roda Playwright contra Flask efêmero + SQLite isolado; não acessa o túnel Cloudflare, sessão TinyFish nem PostgreSQL real. A etapa 10F.7 adicionou `test_auditoria_telas_10f7.py`: telas GET de jogador/mestre em **390×844 e 1366×768**, formulários com IDs da fixture fictícia, navegação no menu mobile, Bag em **320×700** e breakpoints intermediários (768px). O navegador mede `document.documentElement.scrollWidth`, coleta exceções de JavaScript e gera capturas em `test-results/auditoria-telas/`. O teste exige a rota/permissão esperada e não submete formulários de gameplay. A matriz foi ampliada para cobrir 13 formulários/visões com identificadores do SQLite e 9 cenários intermediários; outras 12 combinações avaliam as telas-chave em tema escuro. O servidor de testes substitui a URL fictícia da imagem do Bulbasaur pelo sprite local versionado em `static/img/pokemon-hd/`, sem mudar os dados reais nem o template.

**Achado 10F.7 comprovado em Chromium:** inventário do jogador a 1366px tinha `scrollWidth=1458px` (**+92px**). No arquivo `static/css/inventario.css`, o desenho `.inventario-nds-bag::after` usa `right:-120px`. Já `visual-inventario-10c5.css` deixa a Bag com `overflow:visible !important` no desktop (para preservar controles). A correção move a contenção da decoração (`right:0; width:min(380px,100%)`) para a **regra global** da camada visual, não só `@media(max-width:1199px)`. Preserva overflow visível para autocomplete e evita cortar menus. Versão da folha CSS no template do inventário atualizada. Contrato em `tests/test_inventario_largura_10f3.py` examina a regra global; Playwright verifica a dimensão calculada do documento.

**Permissões observadas:** `/regiao/ankar` é protegida por `@perfil_obrigatorio("mestre")`; o redirect do jogador para login é intencional. A matriz de telas considera Região somente para mestre e registra explicitamente a negação ao jogador.

**Evidência de execução:** [Playwright final #44879957277](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44879957277): **102 testes aprovados em 153,41s**, com 96 screenshots publicados no artefato e inspeção visual das capturas de Bag desktop e mobile/dark. [Contrato visual #44879957142](https://github.com/VictorASBrito/PokemonRPG/actions/runs/44879957142): **59 testes aprovados**. A imagem Bulbasaur local aparece corretamente na fixture e a Bag desktop não apresenta mais overflow do documento.

**Limites:** não existe cobertura de todas as combinações de campanha, NPCs cadastrados, uploads, ações destrutivas, Firefox/WebKit ou zoom. Resultado verde não dispensa inspeção manual dos artefatos. Erros de fixtures devem ser distinguidos de bugs do site. Não remover controles ou rotas para fazer um teste passar.

## Dashboard — legibilidade de combate (10F.8)

A visão normal mantém seis posições de equipe, seis atributos base e quatro slots de golpe, com nome em cima e dano/tipo embaixo. Os valores base usam fonte responsiva de 1,1 a 1,45rem e números tabulares. Até 640px, atributos e golpes empilham para evitar compressão excessiva. Na visão expandida, os golpes continuam em 2x2 (uma coluna até 650px), com linhas de conteúdo a partir de 56px; a grade detalhada não distribui mais a altura excedente para a seção de golpes. A coluna detalhada rola internamente quando necessário em desktop alto, preservando o fallback de página rolável em janelas baixas (10F.4). Totais de combate ganham hierarquia; nomes laterais podem quebrar. As ações de retrato, ficha, altura dos atributos do treinador e quatro slots vazios permanecem. O mesmo CSS e a mesma estrutura de resumo são aplicados ao NPC, sem alterar o backend.

Testar em Chromium com equipe completa, golpes e slots vazios, temas e resoluções 1720×864, 1366×768 e 390×844; evidências em `test-results/dashboard-10f8`. Testes prévios de foco e navegação continuam obrigatórios.

## Etiquetas e atributos do dashboard (10F.9)

As etiquetas comuns em `tipos.css` usam altura automática, mínimo de 24px geral (21–25px nos contextos reduzidos e expandidos), fonte legível de 0,69–0,78rem no painel e line-height 1,2, sem sombra de texto; paletas dos tipos não mudam. Não usar altura fixa ou fonte de 9px nos selos. O card normal agora mostra os seis totais e bases fornecidos pelo servidor (a mesma fonte dos dados do expandido), com título Atributos e fonte de 1rem nos totais. Classe `.atributos-base-pokemon` é mantida para compatibilidade, apesar de agora conter totais e bases. A grade tem mínimos de 52px; celular mantém empilhamento. Os templates do jogador/prévia e NPC seguem a mesma hierarquia. Testar igualdade dos valores e limites dos textos dos selos com dois tipos e seis Pokémon no Playwright; manter as regressões anteriores.

## Tokens compartilhados

- **Cores:** `--fundo`, `--superficie`, `--superficie-suave`, `--texto`, `--texto-suave`, `--borda`, `--primaria`; a variante escura vem de `tema.css`.
- **Espaço:** `--ui-space-1` a `--ui-space-6`, `--ui-page-gutter`.
- **Raios:** `--ui-radius-xs`, `--ui-radius-sm`, `--ui-radius-md`, `--ui-radius-lg`.
- **Controles:** `--ui-control-height`, `--ui-field-height`, `--ui-focus`, `--ui-ring`, `--ui-campo`, `--ui-campo-borda`, `--ui-fundo-controle`.
- **Compatibilidade:** `--ui-v10-gutter`, `--ui-v10-radius`, `--ui-v10-focus` e `--ui10d-*` permanecem como aliases no design system. Novas páginas devem preferir nomes `--ui-*`.

Exemplo:

```css
.meu-bloco {
  min-width: 0;
  padding: var(--ui-space-4);
  border: 1px solid var(--borda);
  border-radius: var(--ui-radius-md);
  background: var(--superficie);
  color: var(--texto);
}
```

## Componentes e estilos de tela

Use as classes de contrato existentes:

- `.botao`, `.botao-primario`, `.botao-secundario`, `.botao-link`
- `.cartao`, `.ui-card`, `.campo`, `.formulario`
- `.cabecalho-pagina`, `.cabecalho-dashboard` e `.ui10d-menu-contexto`
- `.dashboard-jogador`, `.pokemon-dashboard-card`, `.pokemon-dashboard-detalhes-expandidos` para Pokémon.

O painel do NPC compartilha `dashboard.css`: em `npc-painel.css` devem ficar **apenas** estilos específicos das ações administrativas e modais, sem redefinir a grade principal. Não adicionar formulários extensos à grade expandida dos golpes; usar modais.

As ações de Mega/forma pertencem aos services/rotas; CSS e JS só apresentam os controles. Menus de várias formas exibem sprite e nome; o botão Keystone apresenta Mega Evoluir. Acessibilidade e foco não podem interferir em submit/CSRF.

## Regras de refatoração

1. **Antes de criar arquivo CSS novo**, verificar se o estilo pertence a um componente ou página já existente.
2. Não esconder funcionalidades por CSS para substituir permissões do backend; preservar checagem de servidor.
3. Evitar valores de cor hexadecimais para superfícies neutras em arquivos de página; usar tokens. Cores semânticas de tipos Pokémon e estado podem ser específicas.
4. CSS local deve ser limitado por classe de página/componente; evitar `html`, `body`, `.botao` e `.cartao` globais.
5. Regras de `@media` devem preservar desktop, tablet e mobile; conferir interface com 320px e zoom 200%.
6. Controles acionáveis devem ter `type="button"` quando não forem submit; `dialog` com rótulo, botão de cancelar e retorno de foco.
7. Mudanças compartilhadas exigem teste de templates, CSS válido, rotas e regressão visual de jogador, NPC e mestre.
8. Arquivos com versionamento de CSS no `url_for` precisam de atualização de versão após alteração para não exibir cache antigo.

## Mapa de testes visuais

- `tests/test_sistema_ui.py` — CSS de base e compilação de templates.
- `tests/test_navegacao_mobile_10f1.py` — estados fechado/aberto e ausência de regras globais concorrentes.
- `tests/test_inventario_mobile_10f2.py` — rolagem móvel de Pokémon e aba ativa visível.
- `tests/test_visual_10c5.py` — navegação responsiva e rolagem.
- `tests/test_padrao_visual_10d1.py` — contexto do catálogo.
- `tests/test_refinamento_frontend.py` — modos claro/escuro, fichas e Painel.
- `tests/test_padronizacao_dashboard.py` — grade de equipe.
- `tests/test_dashboard_foco_baixa_altura_10f4.py` — foco rolável em janelas baixas nos painéis do jogador e NPC.
- `tests/test_painel_npcs_10d4_5.py` — edição e ações do mestre nos NPCs.
- `tests/test_contrato_visual_repositorio.py` — novos invariantes de organização, sem uso de PostgreSQL.

Os testes estáticos **não substituem** uma revisão visual real após deploy (Chrome/Firefox, mobile, modo claro/escuro e diferentes equipes).

## Manutenção incremental

A base global foi consolidada sem redesenhar cada tela individual. A fase seguinte será migrar seletores de páginas legadas para componentes compartilhados aos poucos, com comparação visual; não realizar uma substituição em massa de CSS que altere menus, contrastes ou tamanho dos sprites.
