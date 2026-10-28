# Pokémon RPG — Revisão visual e mapa interativo de Ankar (Etapa 10A.3)

**Data:** 28/10/2026  
**Base:** Atlas instalado da etapa 10A.2 e correção de testes UTF-8 da etapa 10A.2.1; arquivos da estrutura Flask validados contra o repositório `VictorASBrito/PokemonRPG`.  
**Escopo:** aprimoramento visual incremental do Atlas. **Não** é reformulação das demais páginas.

## Revisão do padrão visual do site

Foram analisados os arquivos compartilhados `templates/base.html`, `static/css/geral.css`, `refinamento.css`, `tema.css`, `sistema-ui.css`, e amostras representativas de `dashboard.css`, `painel-mestre.css`, `campo.css`, `capturaveis.css` e templates do jogador e do mestre. O padrão existente usa:

- Variáveis semânticas `--fundo`, `--superficie`, `--superficie-suave`, `--texto`, `--texto-suave`, `--borda`, `--primaria`, sombras e equivalentes no modo escuro.
- Cartões e controles de cantos arredondados, navegação compacta e tipografia de sistema.
- Layout responsivo com pontos de quebra próprios por funcionalidade. A regra compartilhada de navegação mobile/tablet permanece intocada.
- Painéis compactos, sprites preservados, páginas de encontro/campo funcionais; mudanças globais exigiriam validação com usuários e foram evitadas.

**Ajuste implementado:** CSS do Atlas usava variáveis que não faziam parte do tema (`--surface`, `--border`, `--text`, `--text-muted`), forçando cores de fallback. Os estilos do Atlas agora reutilizam as variáveis oficiais. O cabeçalho foi reduzido para seguir a densidade das outras páginas. CSS adicional isolado em `.ankar-*`. Os arquivos globais e as telas dos jogadores **não foram alterados**.

**Limite da revisão:** não foi possível abrir o servidor real do usuário ou conferir visualmente todas as suas telas e combinações de dados. Foi renderizada uma prévia isolada do Atlas e exercitados seus controles em Chromium nos tamanhos de 390, 820 e 1440 pixels. Essa verificação não substitui avaliação local real das páginas existentes.

## O mapa

- A imagem fornecida pelo mestre está copiada **sem modificações** em `static/img/ankar-mapa.jpg` (1533 × 2048 px).
- Marcadores curados manualmente estão em `app/data/mapa_ankar_pontos.json` com porcentagens (`x`, `y`) da dimensão da arte. Eles correspondem a **73 rotas**, **18 cidades com ginásio**, **8 cidades auxiliares** e **20 pontos de interesse**.
- Cada marcador tem `id` referenciando exatamente uma página do `catalogo_ankar_visual.json` já instalado, sem inferir uma conexão geográfica não descrita no material.
- Filtros por **Rotas**, **Cidades** e **Pontos de interesse** evitam 119 alvos simultaneamente; iniciam com rotas selecionadas.
- Primeiro clique/toque em um marcador seleciona e identifica o local; o botão **Abrir ficha do local**, ou um segundo clique no mesmo marcador, permite navegar. Ctrl/Cmd/Shift+clique continuam com comportamento padrão de links.
- Botões de zoom (70% a 250%), localizar ponto selecionado e rolagem contida dentro da área do mapa; no celular a imagem não vira uma miniatura ilegível.
- Navegação de volta: cada ficha tem **Ver localização no mapa**, com seleção da categoria e foco visual da posição.
- Se o JavaScript não carregar, a imagem e as fichas na lista de locais permanecem disponíveis; os marcadores são links normais para as fichas.
- A imagem é decorativa para efeitos de regras: não calcula distância, movimento, caminhos ou teletransporte. Números e posições do mapa não determinam dados de captura.

## Arquivos novos/alterados

- `static/img/ankar-mapa.jpg` — imagem original sem modificações.
- `app/data/mapa_ankar_pontos.json` — 119 posições com `id` existente e nome para identificação.
- `app/services/regiao_ankar_service.py` — leitura em cache do mapa e acesso por slug, sem DB.
- `app/routes/regiao.py` — passa dados do mapa aos templates da mesma rota mestre já existente.
- `templates/regiao/indice.html` — mapa, filtros, legenda e painel de identificação; lista mantida.
- `templates/regiao/detalhe.html` — link de retorno ao local no mapa.
- `static/css/atlas-ankar.css` — cores corrigidas, dimensões compactas, mapa responsivo isolado.
- `static/js/atlas-ankar.js` — filtros, seleção e zoom; sem chamadas de rede.
- `tests/test_mapa_ankar_visual.py` — integridade dos dados, templates e isolamento de estilo.
- `scripts/registrar_revisao_visual_ankar.py` — anotação idempotente nos documentos mestres, sem editar código.
- Esta documentação.

## Instalação

A **etapa 10A.2 precisa já estar instalada**, porque esta atualização não substitui `app/data/catalogo_ankar_visual.json`, `app/__init__.py` nem `templates/base.html`.

1. Extraia o ZIP na raiz do `PokemonRPG`, preservando os caminhos. Isso substituirá **somente arquivos do Atlas**.
2. Execute `python scripts/registrar_revisao_visual_ankar.py` para atualizar o contexto histórico de maneira aditiva.
3. Execute `python -m pytest -q tests/test_mapa_ankar_visual.py tests/test_atlas_ankar.py tests/test_atlas_ankar_flask.py`.
4. Reinicie o Flask e acesse `/regiao/ankar` como mestre. Teste filtro de cidades, toque em marcador, zoom e retorno de uma ficha ao mapa.

**Não execute `scripts/instalar_atlas_ankar.py` novamente**: esta atualização não requer novo registro de rota ou menu. Nenhuma migration, `POST`, escrita no PostgreSQL ou alteração no GitHub.

## Testes realizados neste ambiente

- `python -m pytest -q tests/test_mapa_ankar_visual.py` → 6 passaram (bibliotecas de servidor não necessárias).
- `node --check static/js/atlas-ankar.js` → OK.
- `python -m compileall -q app` → OK.
- Chromium isolado em 390, 820 e 1440 px → categoria, seleção, botão, zoom, ocultação de pontos e sem rolagem horizontal **da página**; OK.
- A suíte Flask completa e a comparação com o servidor real do usuário não foram executadas aqui (Flask não instalado nesta execução).

## Observações e próximos refinamentos

- Coordenadas foram posicionadas por leitura visual do mapa. Se um marcador estiver alguns pixels fora do centro, ajustar apenas `x`/`y` no JSON; não alterar os `id` nem inventar trajetos.
- Como o mapa é grande e densamente numerado, mobile depende de arrastar e aproximar; o diretório de pesquisa permanece a alternativa mais direta.
- A revisão de telas do restante do projeto deverá ser validada em ambiente do usuário com capturas reais dos módulos (ficha, equipe, Box, inventário, campo e capturáveis) antes de mudanças cosméticas globais.
