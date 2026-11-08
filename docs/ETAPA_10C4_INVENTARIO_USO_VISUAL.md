# 10C.4 — Uso visual na lista do inventário

## Origem e princípio

Base de referência: `main`, commit `e392239a` (`backup-pre-construcao`), após a Etapa 10C.3. Adaptação incremental **somente de UI e carregamento de condições**. Não há migration ou comando de limpeza do PostgreSQL.

## Comportamento

- A linha de cada item da mochila agora pode apresentar **Usar**. Para o mapa, Usar abre o mesmo `dialog` estático e **não consome o item**.
- Medicamentos de `recuperar_pv`: ao clicar em Usar, ficam destacados **somente os Pokémon da equipe com PV atual inferior ao máximo calculado**. Ao clicar em um destacado, o navegador envia POST à mesma rota de inventário da 10C.3; o servidor confere propriedade, estoque e efeito na mesma transação. Pokémon com PV desconhecido não é oferecido como alvo para evitar um falso destaque.
- Medicamentos de `remover_status`: somente Pokémon da equipe com os status relevantes ficam destacados. Podem estar com PV máximo, pois o tratamento de status é independente da cura de PV. O efeito `todos` abrange qualquer condição ativa.
- Se não houver alvo elegível, não ocorre consumo e a tela mostra aviso. Há Cancelar e tecla Escape para abandonar a seleção.
- Itens consumíveis sem terapia suportada têm botão Usar com confirmação de **registro de consumo sem efeito automático**. Não prometemos automatizar outros tipos de efeito nesta etapa.
- Itens equipáveis conservam ação **Equipar** na linha do item, abrindo diálogo com os Pokémon da equipe e da Box. Mantida a rota já existente de equipamento.
- O painel direito conserva título, imagem, descrição e formulário de transferência. Foram removidos editor JSON de efeitos, registro de uso, seleção de Pokémon para cura e equipamentos desse painel.
- O campo **Ajustar quantidade** (mestre) foi movido para a área inferior `Gerenciamento do mestre` junto de Adicionar item. O jogador não recebe essa permissão.

## Instalação incremental

1. Extraia este ZIP na raiz do projeto, preservando diretórios e imagens, sobre o commit correspondente.
2. Execute `python scripts/instalar_inventario_10c4.py` (idempotente, cria `.bak-10c4` dos dois arquivos alterados).
3. Opcional, para atualizar o diário e o documento de continuidade: `python scripts/registrar_documentacao_inventario_10c4.py` (idempotente).
4. Execute `python -m pytest -q tests/test_inventario_uso_10c4.py tests/test_itens_10c3_puro.py tests/test_itens_10c3_flask.py tests/test_itens_inventario.py`.
5. Reinicie o Flask e atualize a página forçando recarregamento (Ctrl+F5). O novo JS e CSS usam versionamento `10c4`.

## Testes manuais obrigatórios

- Coloque uma Poção (1) na mochila de um jogador, com pelo menos um Pokémon ferido e outro totalmente curado. Usar deve destacar somente o ferido; clicar nele deve curá-lo e reduzir o estoque para zero.
- Com Pokémon todos cheios, Usar deve mostrar aviso e não consumir o item.
- Com condição paralisado/queimando/envenenado, conferir que o medicamento correspondente destaca somente Pokémon afetados, inclusive com PV cheio.
- Troque de aba ou cancele durante a seleção; nenhuma unidade deve ser consumida.
- Adicione o mapa e pressione Usar: abre imagem sem pontos interativos e sem consumir o mapa.
- Com item equipável, abra Equipar e confirme que o seletor lista inclusive Pokémon da Box, mantendo a capacidade anterior.
- Mestre: conferir Adicionar item e Ajustar quantidade na área de gerenciamento; jogador não deve ver formulário de quantidade.
- Teste tela estreita/mobile, buscas, paginação visual por bolsas e link por URL `/p/<login>/`.

## Pendência visual registrada dos prints

- Tela do **mestre**: o quadro inferior `Gerenciamento do mestre · Adicionar item` aparece apertado/cortado na borda da mochila, e o seletor de itens extrapola o espaço disponível. Revisar posição do popup do autocomplete e regras de `height/overflow` do painel de mochila (especialmente em desktop com altura limitada).
- O painel detalhado da direita estava carregado de controles e exibia JSON técnico. Nesta etapa sua responsabilidade foi reduzida a **descrição + transferência**, com ações contextuais na lista.

**Não executar `scripts/reconstruir_catalogo_10c3.py --aplicar` para testar esta etapa.** O catálogo já está configurado; esta mudança apenas altera a interação.
