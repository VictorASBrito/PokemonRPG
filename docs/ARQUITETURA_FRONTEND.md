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
- `tests/test_painel_npcs_10d4_5.py` — edição e ações do mestre nos NPCs.
- `tests/test_contrato_visual_repositorio.py` — novos invariantes de organização, sem uso de PostgreSQL.

Os testes estáticos **não substituem** uma revisão visual real após deploy (Chrome/Firefox, mobile, modo claro/escuro e diferentes equipes).

## Manutenção incremental

A base global foi consolidada sem redesenhar cada tela individual. A fase seguinte será migrar seletores de páginas legadas para componentes compartilhados aos poucos, com comparação visual; não realizar uma substituição em massa de CSS que altere menus, contrastes ou tamanho dos sprites.
