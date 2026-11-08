# Pokémon RPG — Auditoria de UX e funcionalidades (Etapa 10D.1)

**Referência conferida no GitHub:** `VictorASBrito/PokemonRPG`, `main`, commit **`a7198a1`** — *Repaginação Visual no inventário* (08/11/2026). A revisão foi **estática**, dos arquivos disponíveis no GitHub: templates, CSS, JavaScript, rotas e parte dos serviços. O PostgreSQL em execução e a aplicação real em celulares não estavam acessíveis neste ambiente. Por isso os pontos abaixo distinguem **evidência no código** de **hipóteses que exigem teste de integração**.

## Objetivo de produto

Manter uma identidade única para jogadores e mestre, especialmente em cabeçalhos, navegação, busca, filtros, botões, detalhes, formulários e mensagens. Evitar que ajustes de CSS de uma tela alterem regras de jogo ou escondam controles em mobile/tablet. Priorizar correções com menor risco antes de refatorações que exigem testes do backend.

## Mapa das telas revisadas no código

- **Acesso e estrutura:** `templates/base.html`, `templates/entrada_personagens.html`, `static/css/geral.css`, `static/css/sistema-ui.css`, `static/css/tema.css`, `static/css/visual-global-10c5.css`, `static/js/visual-navegacao-10c5.js`.
- **Mestre:** `templates/mestre/dashboard.html`, `mestre/jogadores.html`, `mestre/novo_jogador.html`.
- **Catálogos:** dashboard, listagem e edição de Pokémon, Golpes e Itens, vínculos dos golpes — oito templates em `templates/mestre/catalogo/`.
- **Jogadores/Pokémon:** `templates/jogador/dashboard.html`, `ficha.html`, `equipe.html`, `boxes.html`, `novo_pokemon.html`, `pokemon.html`.
- **Mochila:** `templates/jogador/inventario.html`, `static/css/inventario.css`, `visual-inventario-10c5.css`, `inventario-uso-10c4.css`, `static/js/inventario-uso-10c4.js`, `app/services/efeitos_itens_10c3.py`.
- **Ankar/combate:** `templates/regiao/indice.html`, `detalhe.html`, `templates/campo/painel.html`, `templates/capturas/mestre.html`, `jogador.html`, e respectivos CSS.
- **Serviços e permissões:** rotas `catalogo_admin.py`, `pokemons.py`, `boxes.py`, `inventario.py`, `capturas.py`, `combates.py`, `mestre.py`, `jogadores.py`, com amostras dos serviços e `fichas_url_service.py` de etapas anteriores.

## Achados com prioridade

| Prioridade | Área | Evidência e consequência | Ação |
| --- | --- | --- | --- |
| **P1 — corrigido em 10D.1** | Títulos de páginas | `static/css/geral.css` contém `.cabecalho-pagina.cabecalho-com-acoes > div:first-child { display:none; }` e regra equivalente para `.cabecalho-dashboard`. Isso oculta títulos e descrições que existem no HTML das fichas, equipe, caixas, catálogo e gestão. | Restaurar os blocos com uma hierarquia compacta e responsiva, sem reintroduzir grandes cabeçalhos. |
| **P1 — corrigido em 10D.1** | Navegação do catálogo | Os oito templates usam botões próprios de retorno, sem um menu secundário único para alternar entre Pokémon/Golpes/Itens. | Incluir navegação contextual **somente em `catalogo_admin.*`**, com URLs existentes, foco e item ativo; não alterar permissões. |
| **P1 — mitigado em 10D.1** | Filtros/ações | Catálogos, Boxes e Mestre usam classes próprias para filtros, botões e paginação, com larguras/recuos diferentes. | Reunir espaçamento, altura e responsividade comuns numa camada CSS global, sem substituir as regras específicas. |
| **P1 — verificar na aplicação real** | Inventário do mestre | 10C.5 corrigiu altura rígida, `overflow` e autocomplete, mas a interação com dados reais, janela de altura baixa e listas longas ainda não foi testada neste ambiente. | Validar em navegador real 1366×768, 820×1180 e 390×844 com resultados de autocomplete abertos. |
| **P1 — segurança existente** | Acesso por links de personagens | `fichas_url_service.py` oferece acesso direto por `/p/<login>/` sem senha, conforme decisão registrada na 10B.3. Há proteção de endpoints, mas quem obtém a URL pode acessar ações de jogador. | Manter acesso externo restrito; se houver publicação aberta, discutir autenticação/convites antes de liberar. **Não alterado** neste pacote. |
| **P1 — definir regra e testar** | Uso terapêutico | A interface `inventario-uso-10c4.js` destaca apenas Pokémon da **equipe**; o serviço `aplicar_efeitos_terapeuticos` valida dono/ativo, mas não restringe `localizacao == 'equipe'`. Uma requisição manual pode escolher Pokémon ativo da Box. | Decidir se cura de Box é permitida. Se não for, validar a localização também no servidor e acrescentar teste específico. **Não alterado**. |
| **P2 — revisão funcional** | Efeitos de itens | A execução automática cobre `recuperar_pv` e `remover_status`; outros tipos de efeito podem existir no catálogo, mas não são automaticamente aplicados nesse serviço. | Identificar na UI quais são narrativos/manuais e quais são executáveis; testar comportamento de consumo com estoque mínimo. **Não alterado**. |
| **P2 — revisão de acessibilidade** | Avisos | Flash e avisos dinâmicos usam toasts de **1,5 s** conforme requisito. Mensagens longas ou erros podem ser difíceis de ler nesse intervalo, especialmente em leitores de tela. | Preservar o tempo acordado; verificar se erros de formulário também têm contexto persistente no campo quando necessário. **Não alterado**. |
| **P2 — revisão visual** | Atlas | Atlas possui layout próprio de filtros, mapa e encontros. O 10C.5 já adicionou limites responsivos. | Testar seleção de marcador e diálogo de capturável em tablets de orientação retrato e navegadores móveis. **Não alterado**. |
| **P2 — revisão visual/funcional** | Capturáveis | O jogador usa carrossel e o mestre usa formulário/listagem, com CSS específico e regras de permissões. | Testar cards longos, atribuição à Box, feedback de limites e múltiplos jogadores. **Não alterado**. |
| **P2 — revisão funcional** | Campo | Painel compartilhado permite até 16 times; há rotas para colocar/mover/remover/limpar. | Testar atualização entre abas e comportamento com múltiplos jogadores, sem supor que turnos ou ações automáticas estejam implementados. **Não alterado**. |
| **P2 — dívida técnica visual** | Camadas de CSS | `geral.css`, `sistema-ui.css`, CSS por página e patches 10C.5 acumulam regras para breakpoints e componentes semelhantes. | Consolidar design tokens e retirar regras obsoletas somente com testes de regressão visual por rota. **Não alterado** nesta etapa. |

## Padrão comum adotado

1. **Navegação primária:** no `templates/base.html` e menu móvel existente da 10C.5. A edição de 10D.1 não remove nenhum link nem altera as permissões.
2. **Navegação secundária:** surge abaixo do cabeçalho **apenas na área do catálogo**; contém Visão geral, Pokémon, Golpes e Itens. Em telas estreitas é horizontal e rolável; em formulários de edição mantém o grupo correspondente ativo.
3. **Cabeçalho de página:** rótulo contextual pequeno, título visível, descrição curta e ações à direita; no celular os controles passam para baixo do título.
4. **Filtros e formulários:** controles com altura e espaçamentos coerentes, textos visíveis e foco de teclado. Não converter automaticamente submits em botões genéricos.
5. **Mensagens:** continuar com o toast da 10C.4.1 (1,5 s), sem banners permanentes.
6. **Responsividade:** até 420 px (telefones pequenos), até 700 px (telefone), até 1100 px (tablets); respeitar temas, navegação por teclado e redução de movimento.

## Como dar continuidade à padronização sem regressão

**10D.1 (este pacote):** restaurar títulos visíveis; menu único dos catálogos; espaçamento e filtros compartilhados. CSS + um template base, sem mudar o banco.

**10D.2 — jornadas completas:** testar cadastro/edição/duplicação/ativação de Pokémon, Golpes e Itens; formulário de jogador e Pokémon; inventário (cura, condição, mapa, transferir, equipar); capturáveis e campo. Criar testes de regressão Flask com banco de **teste**, sem usar a base de produção.

**10D.3 — componentes reutilizáveis:** extrair cabeçalhos, filtros, estados vazios, barras de ações e confirmação de exclusão para macros/templates Jinja, uma família de telas por commit. Remover CSS conflitante somente após screenshots de referência.

**10D.4 — validação visual real:** tirar capturas de referência no Flask em 360×740, 390×844, 768×1024, 820×1180, 1024×768, 1366×768 e 1440×900, nos dois temas. Validar links e acessos com contas mestre e jogador em URLs independentes.

## Segurança da entrega

- **Altera:** `templates/base.html` (novo menu contextual + referência ao CSS).
- **Acrescenta:** `static/css/padrao-visual-10d1.css`, instalador, testes e documentação.
- **Não altera:** rotas, contas, sessões, regras de cura, estoque, catálogo PostgreSQL, permissões, schema, JS de inventário, scripts de reconstrução, sprites, ou estado da campanha.
- **Validação possível:** testes estruturais/idempotência/sintaxe Jinja, sem banco. O CSS real das páginas só pode ser avaliado no navegador ligado ao Flask após aplicação.
