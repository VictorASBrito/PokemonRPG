# Etapa 10D.1 — Padrão de navegação e cabeçalhos

Base verificada: `main` commit `a7198a1`.

## Instalação

1. Verifique `git status -sb` e faça um commit local das alterações importantes.
2. Extraia o ZIP na raiz do projeto, mantendo `scripts/`, `static/`, `tests/` e `docs/`.
3. Execute `python scripts/instalar_padrao_visual_10d1.py --verificar`: deve listar `templates/base.html` sem alterá-lo.
4. Execute `python scripts/instalar_padrao_visual_10d1.py`. O arquivo original será copiado para `relatorios/backups_ui_10d1/AAAAmmdd-HHMMSS/templates/base.html` (não versionar backups).
5. Execute `python -m pytest -q tests/test_padrao_visual_10d1.py`.
6. Reinicie Flask e use Ctrl+F5; navegue por **Catálogo → Pokémon → Golpes → Itens**, inclusive em telas de edição.
7. Faça testes em mestre e jogador, porque os cabeçalhos existentes voltam a aparecer; confirme que barras de ações não são cortadas.

## Regiões modificadas

- Barra secundária do catálogo: somente `catalogo_admin.*`, URLs antigas e permissões antigas.
- `.cabecalho-pagina.cabecalho-com-acoes`: restaura título/descrição que eram ocultados por regra legada; layouts compactos.
- `.cabecalho-dashboard`: mesma hierarquia; conferir o painel do jogador.
- Filtros, paginação e barras de ações: alinhamento leve por CSS, sem trocar HTML de formulários.

## Teste manual mínimo

- Mestre: catálogo geral e edições de Pokémon, Golpes e Itens; os 4 links contextuais devem aparecer. Campos, filtros e botões de salvar continuam funcionando.
- Mestre: painel, lista de jogadores, cadastro e ficha; os títulos não devem desaparecer.
- Jogador: dashboard, ficha, equipe, boxes e mochila; sem novos controles administrativos e sem rolagem horizontal.
- Atlas, Campo e Capturáveis: não devem perder estilos nem links existentes.
- Em telefone 360–390 px: menu principal abre, submenu do catálogo rola horizontalmente, nada é cortado.
- Em tablet 768–1024 px: ações podem quebrar linha, mas não podem sobrepor texto.
- Com tema claro/escuro e navegação por teclado, conferir foco visível.

## Reversão

Restaure `templates/base.html` do backup da instalação e remova ou deixe de carregar `static/css/padrao-visual-10d1.css`. Não há reversão de banco porque o instalador não acessa PostgreSQL.

**Nota:** não executar migrations, importações nem reconstrução de itens para instalar esta etapa. O pacote inaugura uma revisão sistêmica; não afirma que todas as telas já foram testadas dentro do Flask real.

## Evidência visual preliminar

Uma página HTML **representativa**, não a aplicação Flask, foi renderizada em Chromium nos viewports 360×740, 390×844, 768×1024, 820×1180, 1024×768, 1366×768 e 1440×900. Em todos os casos o título permaneceu visível e a largura total do documento foi igual à viewport (sem overflow horizontal). Essa checagem preliminar não substitui a revisão das páginas reais com os dados de Ankar.
