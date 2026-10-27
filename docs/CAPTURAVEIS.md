# Capturáveis em campo — funcionamento e atribuição à Box

## Estado da funcionalidade

- Até **15 capturáveis ativos por campanha**, persistidos em `pokemons_capturaveis`.
- O mestre adiciona e remove encontros em `/mestre/capturaveis`.
- Jogadores visualizam nome, sprite, tipos e quem encontrou o Pokémon em `/jogador/capturaveis`.
- **Etapa 06:** o mestre pode escolher um personagem ativo da campanha para receber o encontro na sua Box. A atribuição não faz rolagem de captura: é decisão do mestre.
- A atribuição é uma operação atômica entre criação do Pokémon na Box e retirada/reordenação dos capturáveis: falhas devem reverter ambas.

## Atribuição à Box

1. Na tela do mestre, no card de um encontro, escolher **Atribuir à Box de** e um personagem.
2. Clicar em **Atribuir à Box**.
3. O servidor valida login/perfil, token do formulário, campanha, disponibilidade do encontro, destinatário com conta ativa (jogador ou tester) e capacidade da Box.
4. Cria um `Pokemon` com a mesma forma, natureza, sexo e marcador Shiny já registrados no capturável. A localização é `box` e a posição é a próxima vaga. Calcula PV com nível e regras do personagem destinatário; não cria XP, amizade ou PP individuais.
5. Desativa o encontro (sem excluir o registro), libera a posição e reorganiza o campo de `1..N` em duas fases (`NULL` + `flush`, depois `1..N` + `flush`) para não violar a UNIQUE do PostgreSQL.
6. Registra histórico de `pokemon` (`criacao`) e de `pokemon_capturavel` (`atribuir`) contendo o ID do Pokémon recém-criado e destinatário. Commit único.

É permitido atribuir o Pokémon a um personagem diferente do que o encontrou, exclusivamente por decisão do mestre. A tela do jogador é somente leitura. A atribuição **não** consome Pokébolas nem resolve chance de captura; as tentativas de captura são resolvidas narrativamente pelos jogadores e pelo mestre, sem rolagem automática pelo site.

**Limitações atuais:** o gerador de sexo usa os gêneros globais ativos na campanha; taxas/restrições por espécie não foram implementadas. As mudanças do campo são visíveis após recarregar a página, sem transmissão em tempo real. Naturezas e sexo são gerados na criação do encontro, não na atribuição.

## Arquivos principais

- `app/models/db/capturable.py`: tabela dos encontros.
- `app/services/capturaveis_service.py`: geração, consulta, remoção, atribuição e reordenação.
- `app/services/pokemon_db_service.py`: regras e cálculo de atributos para instâncias na ficha.
- `app/routes/capturas.py`: rotas do mestre e do jogador, com autorização em servidor.
- `templates/capturas/mestre.html` e `static/css/capturaveis.css`: formulário e cards.
- `tests/test_capturaveis_campo.py` e `tests/test_capturaveis_atribuicao.py`: testes de integração.

## Validação após aplicar atualização

Use a instalação que possui a migration `6f355a4d5b2e` (Etapa 05). **Etapa 06 não possui migration adicional**.

```powershell
python -m pytest -q tests/test_capturaveis_campo.py tests/test_capturaveis_atribuicao.py
```

Valide manualmente: gerar vários encontros, atribuir um encontro do meio, verificar natureza/sexo/PV na Box do destinatário, repetir o pedido (deve falhar sem duplicar) e testar Box cheia (deve manter encontro em campo). Fazer backup antes de operações no banco real.

## Próximos desenvolvimentos

- **Não implementar rolagem automática de captura**: a experiência narrativa dos jogadores é intencional.
- Atualizações compartilhadas mais imediatas entre navegadores, caso necessário.
- Painel de Pokémon em campo/batalha com até 16 times.

## Etapa 08 — Shiny automático e apresentação dos encontros (2026-10-25)

**Regra de geração:** quando o mestre cria um novo encontro, o serviço consulta `Personagem.numeros_shiny` **do personagem que encontrou o Pokémon**. A lista é composta por números escolhidos pelo treinador entre 1 e 100, não por números da Pokédex. A cada encontro, o sistema sorteia um número inteiro entre **1 e 100 (1d100)** e marca `PokemonCapturavel.shiny = True` se esse número estiver na lista válida do encontrador. O sorteio acontece **uma única vez na criação**. As listas vazias não produzem Shiny, e valores fora do intervalo são ignorados. O histórico `pokemon_capturavel` de ação `criar` registra `sorteio_shiny` e `shiny` para auditoria do mestre. A identidade do capturável continua preservada quando é transferido à Box, inclusive seu Shiny e sprite.

**Importante:** não confundir sorteio de Shiny (automático) com tentativa de captura (narrativa, decidida pelos jogadores e pelo mestre). Não rodar sorteios sobre encontros já existentes: isso alteraria retroativamente a história da campanha.

**Interface do mestre:** quatro métricas (ativos, vagas, Shinies, treinadores envolvidos), formulário com prévia da espécie selecionada, reforço da regra Shiny, cards com tipo/natureza/sexo, filtro por nome, treinador e Shiny. As ações de atribuição à Box e remoção permanecem exatamente as mesmas. A prévia **não** anuncia o Shiny antes de gerar, pois o sorteio é realizado no servidor ao salvar.

**Interface do jogador:** carrossel responsivo com sprite em destaque, nome, tipos, encontrado por, selo Shiny, setas, contador, miniaturas clicáveis e seleção direta. Na abertura, o carrossel filtra automaticamente os encontros do personagem logado; na falta deles mostra todos. O filtro permite alternar entre os próprios, todos ou outro treinador. Os dados são renderizados no servidor para manter a navegação acessível mesmo sem JavaScript (nesse caso, todos os cards ficam visíveis). Jogadores não recebem controles de mestre, nem veem rolagem interna, natureza ou sexo nessa tela.

**Arquivos:** `app/services/capturaveis_service.py`, `app/routes/capturas.py`, `templates/capturas/{mestre,jogador}.html`, `static/css/capturaveis.css`, `static/js/capturaveis.js` e os testes `tests/test_capturaveis_shiny_carrossel.py`, `tests/test_capturaveis_ui.js`.

**Validação** (executar no ambiente instalado):

```powershell
python -m pytest -q tests/test_capturaveis_campo.py tests/test_capturaveis_atribuicao.py tests/test_capturaveis_shiny_carrossel.py
node --test tests/test_capturaveis_ui.js
```

Não há migration na Etapa 08: `Personagem.numeros_shiny`, `PokemonCapturavel.shiny` e o histórico já existem. Faça backup antes das atualizações e confirme visualmente os temas claro e escuro e o layout móvel.


## Correção 09.3 — Visibilidade inicial do carrossel (26/10/2026)

- A tela de jogadores passa a abrir com o filtro **Todos os Pokémon** selecionado, mesmo quando o jogador possui encontros próprios.
- O primeiro encontro encontrado pelo personagem logado recebe o foco inicial; se não houver nenhum, começa no primeiro encontro geral.
- Desde a abertura, todas as miniaturas e a navegação entre todos os capturáveis permanecem acessíveis; **Meus encontrados** e os filtros por treinador continuam disponíveis como opções manuais.
- O ajuste é exclusivamente de interface (`templates/capturas/jogador.html` e `static/js/capturaveis.js`). Não altera sorteios Shiny, atribuições, imagens HD, permissões ou o banco de dados.
- Verificações: `node --test tests/test_capturaveis_ui.js` e `python -m pytest -q tests/test_capturaveis_shiny_carrossel.py`.
