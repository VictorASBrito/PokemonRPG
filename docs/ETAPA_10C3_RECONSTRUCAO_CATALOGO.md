# Etapa 10C.3 — Reconstrução controlada do catálogo e efeitos reais

**Base de código:** commit `5a544230641dcdade27c37c89dc3af206454ad2d` (“Imagens Itens 1”), com 37 imagens adicionadas a `static/img/inventory/itens/`. **Nenhuma operação no banco real foi executada ao criar este pacote.**

## Escopo

- Reconstruir o catálogo do PostgreSQL, a partir dos 77 códigos do relatório de 28/10/2026. Consolida seis grupos de variantes, preservando itens narrativos específicos e quantidades por personagem (soma na migração de IDs).
- Eliminar 21 nomes de naturezas erroneamente cadastrados como itens. **Uma unidade de Ingênuo** está atualmente presente no inventário histórico de Priscilla: a rotina bloqueia por padrão e exige `--descartar-naturezas` para consentir seu descarte (com backup).
- Criar 48 itens de destino (47 padronizados e o mapa de Ankar). Não dá unidades do mapa a nenhum jogador: a distribuição é posterior e manual.
- Utilizar arquivos do commit “Imagens Itens 1” quando disponíveis. Imagens externas/URLs já cadastradas são preservadas quando não existir arquivo local correspondente. Itens sem arte permanecem sem arte.
- O item **Mapa da Região de Ankar** usa o ícone `mapa.png` no inventário e abre o mapa completo `static/img/ankar-mapa.jpg` em um diálogo simples **sem marcadores interativos**. Requer que o Atlas 10A esteja instalado.
- Usar itens com efeitos `recuperar_pv` e `remover_status` passa a alterar o Pokémon selecionado; consumo e efeito são transação única. Não permite usar um item terapêutico quando o Pokémon está recuperado ou não possui condição correspondente.
- O mestre continua podendo cadastrar itens com os dois efeitos pelo editor visual existente. A cura admite valor fixo, percentual do PV máximo e expressões de dados limitadas (`NdF+B`). Remoção de status admite um status ou Todos.
- O cálculo de PV máximo é obtido de `calcular_pokemon` e das regras da campanha; cura não passa do máximo. Status são removidos de `pokemon_status` somente para o Pokémon escolhido.
- Não automatiza PP (Elixir continua sem efeito automático), experiência, amizade, consumo de turnos ou outras mecânicas.

## Instalação, sem mexer no banco

1. Faça backup do **PostgreSQL** antes de qualquer reconstrução, além do ZIP do projeto e dos uploads. **Não execute `dados importar` ou `jogadores-planilhas importar`** para tentar sincronizar os nomes antigos.
2. Extraia o ZIP na raiz `PokemonRPG`, conservando `static/img/inventory/itens/` do commit recente.
3. Execute `python scripts/instalar_itens_10c3.py`. O instalador faz cópias `.bak-10c3` dos arquivos editados, não acessa o banco e é idempotente.
4. Execute `python scripts/registrar_documentacao_itens_10c3.py` para acrescentar as notas aos documentos de continuidade.
5. Execute `python -m pytest -q tests/test_itens_10c3_puro.py tests/test_itens_10c3_flask.py`; em seguida execute testes de inventário já existentes (alguns testes antigos de consumo sem alvo devem ser atualizados para a nova regra).
6. `python scripts/reconstruir_catalogo_10c3.py --descartar-naturezas` **simula** a migração, sem alterar o banco. Veja `relatorios/catalogo_10c3/simulacao.json`. Sem a flag, a simulação bloqueia ao encontrar a unidade de natureza suspeita.
7. Verifique imagem, nome, categoria, efeito e equivalência de cada item; faça um `pg_dump -Fc` adicional do banco de produção e garanta que todos saíram do site para evitar alterações simultâneas.
8. **Somente após revisar e aprovar**, execute `python scripts/reconstruir_catalogo_10c3.py --aplicar --confirmar RECONSTRUIR-ANKAR --descartar-naturezas`.
9. O script grava `relatorios/catalogo_10c3/backup-pre-reconstrucao-*.json` antes da alteração e salva tudo em uma transação. Se detectar códigos novos/desconhecidos, naturezas equipadas, outra campanha usando esses itens, conflitos de imagens ou de efeitos, **bloqueia a execução**.
10. Rode `flask --app app.py inventario verificar` e `flask --app app.py catalogo auditar-itens --todos`; confira cada jogador, imagem, mapa e efeitos funcionais.

**Importante:** o backup JSON é um instantâneo detalhado para auditoria; para reversão integral prefira restaurar o backup `pg_dump` completo. Nenhuma restauração automática é fornecida aqui. Os itens de destino recebem **novos UUIDs**, e históricos anteriores preservam referências aos registros antigos, não apontando automaticamente para os novos IDs.

## Limitações e decisões explicitadas

- Os relatórios são uma fotografia de 77 itens, 110 registros e 456 unidades. Em reconstrução, uma unidade de `Ingênuo` foi identificada como falsa. Ao descartá-la conscientemente, o estoque passa a **455 unidades**, se não houver outras mudanças desde o relatório. Caso contrário, a rotina bloqueia.
- As propostas `Bola Grande → Grande Bola`, `cura queima → Cura Queimaduras`, `cura congela → Cura Congelamento` foram incluídas por serem equivalências prováveis e estão visíveis no JSON. Se alguma for diferente na lore, **edite o manifesto antes da aplicação**.
- **Poção** é pré-configurada com recuperação de 20 PV (proposta inicial editável), e os curativos de status correspondem às condições atualmente presentes no catálogo da campanha (`queimando`, `paralisado`, `dormindo`, `congelado`, `envenenado`, `muito-envenenado`).
- Nomes, preços, categorias e efeitos personalizados do banco são preservados quando possível; onde o manifesto define um nome/efeito de cura, ele é priorizado. A operação é intencionalmente invasiva e deve ser agendada em uma janela de manutenção.
- O botão de consumir item sem efeito terapêutico permanece disponível para itens consumíveis genéricos. Itens definidos no catálogo com efeitos não suportados por esta etapa continuam sem aplicação automática; não confundir registrar uso com execução desses efeitos.
- As nove contas e URLs `/p/<login>/` não são modificadas. Mestre continua tendo acesso a todos os inventários por suas rotas existentes.

## Arquivos novos

- `app/data/itens_padronizados_10c3.json`: fonte explícita das correspondências e dos novos registros.
- `app/services/efeitos_itens_10c3.py`: efeitos de cura e remoção de status.
- `scripts/instalar_itens_10c3.py`: atualização incremental, com preflight e backups.
- `scripts/reconstruir_catalogo_10c3.py`: simulação/reconstrução, somente com confirmação explícita.
- `static/css/efeitos-itens-10c3.css`: estilos pontuais do mapa e formulário.
- `tests/test_itens_10c3_puro.py` e `tests/test_itens_10c3_flask.py`.
- `scripts/registrar_documentacao_itens_10c3.py`.

**Nenhuma migration nova.** O comando de reconstrução **deleta e recria registros de itens e do inventário somente quando confirmado**; o instalador não faz isso.
