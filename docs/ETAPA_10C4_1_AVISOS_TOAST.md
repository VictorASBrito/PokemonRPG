# 10C.4.1 — Avisos temporarios em todas as paginas

## Problema visual

Nos prints do inventario de Ankar, mensagens como **"Uso do item registrado e quantidade atualizada."** e **"Ficha salva com sucesso no PostgreSQL."** eram exibidas em caixas estaticas dentro do `main`. Elas ocupavam espaco permanente e interferiam no enquadramento da mochila em telas de altura limitada.

## Solucao entregue

- O componente comum `templates/base.html` apresenta todas as mensagens `flash()` em **toasts flutuantes** no canto superior direito, abaixo da barra de navegacao. Nenhuma pagina precisa de adaptacao individual.
- As categorias `sucesso`, `erro`, `aviso`, `info` usam icones/acentos proprios. Categorias novas usam estilo neutro.
- Notificacoes desaparecem em **1,5 segundo** (incluindo o desvanecimento), sem recarregar a pagina.
- Ao passar o mouse ou receber foco, a contagem pausa; ha botao `Fechar` para dispensar imediatamente.
- Sem banners na area do conteudo; sem alteracao nas mensagens, no fluxo de flash ou na persistencia de dados.
- Responsivo, respeita o tema claro/escuro e `prefers-reduced-motion`.

Acessibilidade: como o prazo solicitado e curto, as mensagens de erro tambem desaparecem em 1,5 segundo. Os erros mais detalhados ainda devem continuar visiveis proximo aos campos do formulario quando aplicavel. Se os jogadores relatarem dificuldade de leitura, reconsiderar este prazo especificamente para erros.

## Instalacao incremental

1. Extraia o ZIP na raiz da instalacao do PokemonRPG, preservando as subpastas.
2. Execute `python scripts/instalar_avisos_toast_10c4_1.py` (idempotente, cria `templates/base.html.bak-10c4-1`; nao acessa banco).
3. Execute `python scripts/registrar_documentacao_avisos_10c4_1.py` para registrar as notas na documentacao ja existente.
4. Execute `python -m pytest -q tests/test_avisos_toast_10c4_1.py tests/test_avisos_toast_10c4_1_flask.py`.
5. Reinicie o Flask e force a atualizacao do navegador com Ctrl+F5.

## Testes manuais

- Salvar ficha, adicionar/transferir/usar item, alterar catalogo: observar aviso discreto por 1,5s, sem deslocamento do layout.
- Gerar aviso de erro e aviso informativo: confirmar estilos e comportamento.
- Passar o cursor sobre a notificacao ou usar Tab para focar o botao Fechar: o temporizador deve pausar ate a interacao acabar.
- Testar tema claro e escuro, mobile e duas notificacoes consecutivas.
- A funcionalidade dos itens da 10C.4 continua independente deste pacote.

## Pendencia visual que permanece aberta

O seletor de itens no rodape **Gerenciamento do mestre** ainda precisa de correcao de overflow/posicionamento quando o inventario ocupa toda a altura da tela. O novo toast nao corrige esse problema; ele evita que mensagens flash piorem o layout.

**Nao execute migrations nem scripts de reconstruir catalogo para instalar toasts.**
