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

É permitido atribuir o Pokémon a um personagem diferente do que o encontrou, exclusivamente por decisão do mestre. A tela do jogador é somente leitura. A atribuição **não** consome Pokébolas nem resolve chance de captura; a mecânica de tentativa de captura permanece futura.

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
