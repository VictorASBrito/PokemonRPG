# Pokémon RPG — Etapa 10C.5: repaginação visual responsiva

**Base revisada:** `main` / commit `bbe10f7a165ec43d81599f990c061ac85d02caa6` ("Avisos via toast 2"). A Etapa 10C.4, 10C.4.1 e 10C.4.2 já constam no GitHub. O pacote atual é uma camada incremental de CSS e navegação, **sem alteração no PostgreSQL, regras de batalha, autenticação, URLs, permissões, eventos de cura ou consumo de itens**.

## Falhas identificadas nos prints e na documentação

| Ponto | Achado | Abordagem 10C.5 |
|---|---|---|
| Mochila do mestre | A área de gerenciamento inferior e o autocomplete ficavam cortados pela altura/overflow rígidos em desktop. | Remove o travamento vertical de `body`, `inventario-nds` e containers dependentes, preserva rolagem das listas e permite que o gerenciamento expanda a página. |
| Autocomplete | Popup podia extrapolar o espaço disponível e ficar atrás das seções. | Largura limitada por viewport, altura rolável e aumento do contexto de empilhamento da área de gerenciamento. |
| Formulários de mestre | Dois accordions apertados na base da mochila. | Espaçamentos, campos fluidos, dimensionamento em tablet/mobile e foco visível; continuam exclusivos do mestre. |
| Mochila dos jogadores | Coluna de 6 Pokémon ocupa a maior parte da tela em celular. | Faixa horizontal de cards roláveis com destaque elegível preservado. |
| Tablets | Cartões Pokémon e detalhes perdiam espaço útil. | Equipe em grade 3 colunas (800–1199 px), e detalhes alinhados em duas colunas quando houver largura suficiente. |
| Abas de bolsas | Cinco botões poderiam apertar nomes em largura limitada. | Abas horizontais roláveis, com áreas de toque adequadas. |
| Cabeçalho do site | A navegação desaparecia abaixo de 900 px sem alternativa. | Menu acessível no cabeçalho até 1100 px, com os links atuais, Escape, clique externo e `aria-expanded`. |
| Layout geral | Formulários, botões, cards e popups sobrepostos em telas pequenas. | Margens fluidas, foco de teclado, campos sem overflow, diálogo limitado à janela e refinamentos para Atlas, Campo e Capturáveis. |
| Avisos | Flash e instruções da mochila já migraram para toasts de 1,5 s. | **Preservados.** Não há banners ou contagens extras. |
| Mapa | Item do inventário já abre mapa estático. | Modal redimensionado; nenhuma funcionalidade do mestre é exposta. |

## Instalação

1. Faça commit ou backup das alterações não publicadas antes de aplicar, para que os arquivos não sejam sobrescritos inadvertidamente.
2. Extraia os arquivos do ZIP na raiz do projeto `PokemonRPG`, mantendo as subpastas (`scripts/`, `static/`, `docs/`, `tests/`).
3. Execute `python scripts/instalar_visual_10c5.py --verificar` para pré-validar as âncoras. Nenhum arquivo é escrito nesse modo.
4. Execute `python scripts/instalar_visual_10c5.py`. O instalador edita **somente** `templates/base.html` e `templates/jogador/inventario.html`. Antes da gravação, cria backups dos dois templates em `relatorios/backups_ui_10c5/`.
5. Teste com `python -m pytest -q tests/test_visual_10c5.py` e a regressão existente: `python -m pytest -q tests/test_inventario_uso_10c4.py tests/test_avisos_toast_10c4_1.py tests/test_aviso_selecao_10c4_2.py tests/test_itens_inventario.py`.
6. Reinicie o Flask e use Ctrl+F5. Os CSS/JS usam sufixo de versão `10c5-1`.
7. **Não execute migrações ou reconstrua o catálogo:** esta entrega é exclusivamente visual.

## Checklist manual de validação

- Desktop **1920×1080 e 1440×900**: painel do mestre mostra os accordions de adicionar/ajustar sem cortar autocomplete. Abrir e selecionar um item, verificar se a página rola normalmente quando necessário.
- Notebook **1366×768**: conferir cabeçalho, seis Pokémon, itens e gerenciamento, evitando corte de botões.
- Tablet **1024×768 e 820×1180**: menu de navegação acessível, três Pokémon por linha e detalhes legíveis. Testar orientação paisagem/retrato.
- Mobile **390×844 e 360×740**: menu abre/fecha, sem links inacessíveis; equipe de Pokémon em faixa horizontal; abas de bolsas também horizontais; painel de detalhes e transferência sem largura excedente.
- Sempre verificar tema claro/escuro e `prefers-reduced-motion`.
- Fluxos: usar Poção, remover status, transferir, equipar, abrir mapa, pesquisar no catálogo e salvar ficha; mensagens globais continuam com **1,5 s**, sem duplicar avisos.
- Verificar seleção independente em URLs `/p/<login>/` e também formulário de login do mestre. O CSS/JS não toca em cookies ou no middleware.

## Limites da validação

Os testes incluídos verificam integridade estrutural, repetição segura do instalador e sintaxe dos novos arquivos. Adicionalmente, foi executado um **smoke test em Chromium com uma página de teste representativa** nos viewports 360×740, 390×844, 768×1024, 820×1180, 1024×768, 1366×768 e 1440×900: sem rolagem horizontal, com menu móvel acessível via botão/Escape e gerenciamento rolável. **Esse teste representativo não equivale a testes de navegador dentro da aplicação Flask real.** Recomendamos a verificação manual dos tamanhos de tela acima antes de promover para uso em sessão. Não alteramos telas sem evidência de defeito funcional; os ajustes globais são conservadores e permitem etapas adicionais de refinamento pontual.

## Arquivos

- `scripts/instalar_visual_10c5.py`: pré-validação e atualização segura/idempotente dos templates.
- `static/css/visual-global-10c5.css`: cabeçalho, layouts compartilhados, legibilidade e responsividade.
- `static/css/visual-inventario-10c5.css`: mochila, gerenciamento, autocomplete, mapa e seleção por Pokémon.
- `static/js/visual-navegacao-10c5.js`: menu móvel acessível, sem alterar rotas.
- `tests/test_visual_10c5.py`: 6 testes de regressão isolados.

**Os backups locais e relatórios gerados devem ficar fora dos commits futuros.**
