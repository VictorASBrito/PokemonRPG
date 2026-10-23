# Pokémon RPG — revisão estrutural de HTML/CSS

**Origem:** `PokemonRPG.rar` recebido em 23/10/2026. A atualização preserva o Flask, JavaScript, rotas, formulários e modelos existentes.

## O que foi feito

- Centralizada a camada visual em `static/css/sistema-ui.css`, carregada **por último** no `templates/base.html`, com padrões de espaçamento, controle, foco, borda, card e responsividade.
- Adicionada a classe `app-shell`, identificador de página, link de pular para conteúdo e organização da navegação em tablet/celular (sem ocultar os links principais).
- Padronizadas classes HTML auxiliares de **86 componentes** (`ui-card`, `ui-grade`, `ui-formulario`) em templates existentes, sem trocar `id`, `name`, métodos `POST`, endpoints ou marcadores exigidos pelo JS.
- Corrigido o isolamento de largura nos grids, listas, filtros e cards: conteúdo longo não força as colunas a ultrapassarem seus limites.
- Corrigida a coluna de seis Pokémon da mochila: nomes longos passam a ocupar até duas linhas; nível, PV, barras e retratos continuam dentro do cartão, sem rolagem horizontal acidental.
- Adicionados ajustes compartilhados para painel do mestre, ficha/dashboards de jogador, Pokémon, Boxes, inventário, formulários e catálogo.
- O inventário passa a mostrar o nome da **bolsa visual correta** na listagem e nos detalhes, sem mudar a categoria do item no banco. Exemplo: Antídoto na bolsa Cura mostra "Cura", mesmo se seu cadastro original for genérico.
- Extraídas regras CSS inline do formulário de senha para sua classe própria.
- Preservados `static/css/tema.css`, o modo claro/escuro e os estilos especiais de cada página. Um arquivo de padrões novos evita continuar acumulando correções contraditórias em todos os arquivos existentes.

## Atualizar projeto existente — Windows

1. **Encerre o servidor** e, por segurança, mantenha backup do projeto.
2. Extraia o ZIP em uma pasta temporária.
3. No PowerShell, entre na pasta **PokemonRPG extraída** e execute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\APLICAR_PADRONIZACAO_UI.ps1 -Destino "C:\Users\Victor\Desktop\Projetos\PokemonRPG"
```

4. Reinicie seu servidor Python e pressione `Ctrl+F5` no navegador.
5. No código-fonte HTML, confira se há a referência `sistema-ui.css?v=ui1-20261023`.

**O instalador copia somente templates, o CSS de padronização e o serviço de apresentação do inventário.** Faz backup dos arquivos sobrescritos em `backups/padronizacao_ui_<data>`. Não copia arquivos `.env`, credenciais, bases PostgreSQL, dados pessoais, `data/`, imagens enviadas nem migrations.

## Importante ao usar o ZIP inteiro

O ZIP contém o código-fonte, testes, scripts, arquivos de migração e os catálogos JSON legados, mas deliberadamente **não contém** a pasta `.venv`, o histórico `.git`, o `.env` real, os backups de jogadores nem o conteúdo de `static/uploads/`. Para uma instalação existente, mantenha essas pastas e use preferencialmente o instalador acima, evitando substituir os dados dos jogadores.

## Validação

```powershell
python -m pytest -q tests/test_sistema_ui.py tests/test_inventario_bw_refator.py tests/test_itens_inventario.py
```

A compilação Jinja foi validada para todos os templates. O conjunto selecionado passou com **19 testes**, e outra rodada abrangendo painel do mestre, Boxes e refinamento passou **38 de 39** testes: um teste antigo ainda espera a expressão "Área do jogador", já removida por escolha de produto. A suíte geral contém também falhas preexistentes em testes de acesso ao catálogo e em renderização independente do filtro `tipo_visual` (sem registrar o filtro no ambiente Jinja isolado). Portanto, **não declaramos a suíte completa como 100% verde**.

### Limitações

- Não houve execução visual em navegador real nesta máquina: Chromium bloqueou acesso tanto a arquivos locais quanto ao servidor local. A compatibilidade responsiva foi verificada por CSS, compilação Jinja e testes de Flask, mas a inspeção final deve ser feita nos navegadores dos jogadores.
- Não foram alteradas regras de combate, cálculos, conta, banco de dados ou permissões.
- Não se pode garantir ausência absoluta de bugs visuais em todas as resoluções, mas o novo design system evita as principais classes de regressão de largura, responsividade e alinhamento.
