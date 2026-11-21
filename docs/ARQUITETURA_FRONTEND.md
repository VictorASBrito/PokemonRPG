# Arquitetura visual do Pokémon RPG

**Padrão atual — 21/11/2026.** O objetivo é manter um único sistema de componentes que sirva a jogador, mestre e NPC sem alterar lógica de autorização, dados ou regras de Ankar.

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
- `tests/test_visual_10c5.py` — navegação responsiva e rolagem.
- `tests/test_padrao_visual_10d1.py` — contexto do catálogo.
- `tests/test_refinamento_frontend.py` — modos claro/escuro, fichas e Painel.
- `tests/test_padronizacao_dashboard.py` — grade de equipe.
- `tests/test_painel_npcs_10d4_5.py` — edição e ações do mestre nos NPCs.
- `tests/test_contrato_visual_repositorio.py` — novos invariantes de organização, sem uso de PostgreSQL.

Os testes estáticos **não substituem** uma revisão visual real após deploy (Chrome/Firefox, mobile, modo claro/escuro e diferentes equipes).

## Manutenção incremental

A base global foi consolidada sem redesenhar cada tela individual. A fase seguinte será migrar seletores de páginas legadas para componentes compartilhados aos poucos, com comparação visual; não realizar uma substituição em massa de CSS que altere menus, contrastes ou tamanho dos sprites.
