# Etapa 09 — Imagens Pokémon em alta qualidade

## Origem do problema

A fonte inicial do catálogo é `img.pokemondb.net/sprites/home/...`. Algumas telas aplicavam `image-rendering: pixelated` e exibiam essas imagens em dimensões maiores, principalmente no carrossel de capturáveis. A regra foi substituída por suavização nas ilustrações Pokémon (mantendo o estilo de itens do inventário).

**Ajustar o CSS melhora a interpolação, mas não cria detalhes ausentes no arquivo original.** Para garantir uma fonte maior e armazená-la localmente, existe uma sincronização opcional via linha de comando, que usa Pokémon HOME (512x512) ou official-artwork (475x475) fornecidos pela PokéAPI. Nem todas as formas do catálogo possuem correspondência nessa fonte.

## Primeiro passo: apenas CSS

Após instalar o pacote desta etapa e reiniciar o servidor, recarregue a página ignorando o cache (Ctrl+F5). Examine `Capturáveis`, `Campo`, `Equipe`, `Box`, `Dashboard` e catálogo Pokémon. Não há migration.

## Sincronização local de imagens HD (opcional)

A sincronização usa **a conexão com a internet da sua máquina**, não é executada automaticamente e nunca altera o banco na simulação.

```powershell
flask --app app.py midia pokemon-hd --limite 10
```

Executar primeiro para um Pokémon específico:

```powershell
flask --app app.py midia pokemon-hd --aplicar --codigo bulbasaur
```

Depois de inspecionar a arte na interface, baixar um lote de 30:

```powershell
flask --app app.py midia pokemon-hd --aplicar --limite 30
```

Para percorrer todas as formas elegíveis de uma vez:

```powershell
flask --app app.py midia pokemon-hd --aplicar
```

Repetir lotes é seguro: imagens já convertidas para arquivos locais não são selecionadas novamente. O comando continua mesmo quando determinada forma falha/está ausente na PokéAPI e registra cada ocorrência no terminal.

## O que é preservado

- URLs de imagens personalizadas e uploads do projeto não são alteradas.
- Só são substituídas URLs originais do catálogo `img.pokemondb.net/sprites/home/...`.
- O comando busca a forma exata (`charizard-mega-x`, por exemplo), **sem usar a arte da espécie base como substituta** caso a variante não exista.
- Não se altera nenhum atributo de Pokémon, captura, Box, treinador ou resultado Shiny.
- Não se introduzem novas tabelas ou migrations.
- A imagem é validada como PNG, resolução mínima de 256 px, máximo de 8 MB, antes de alterar a referência.
- Arquivos ficam em `static/img/pokemon-hd/`. Faça backup antes de aplicar um grande lote e inclua esse diretório em versões publicadas/deploys.
- O arquivo `static/img/pokemon-hd/historico-sincronizacao.jsonl` documenta URLs anteriores e novas, para permitir revisão/recuperação manual.

## Limitações e manutenção

- O comando depende da PokéAPI e do acesso ao GitHub para obter as imagens; **nenhuma imagem externa é baixada no pacote distribuído nesta etapa**.
- Nem toda forma regional, Mega ou alternativa do catálogo tem um identificador idêntico ao da PokéAPI. Essas formas são preservadas e relatadas como não disponíveis.
- Alguns Shinies podem não possuir versão HD correspondente; nesse caso o campo Shiny mantém a URL anterior.
- **Uma reimportação posterior do catálogo legado pode substituir as URLs HD locais pelos links antigos.** Execute a sincronização novamente se reimportar o catálogo; os arquivos baixados permanecem na pasta local.
- O downloader não modifica arquivos carregados manualmente, nem tenta ampliar sprites pequenos para fingir maior resolução.
- Veja o repositório de imagens: https://github.com/PokeAPI/sprites e confira direitos de uso antes de distribuir as artes publicamente.

## Validação

```powershell
python -m pytest -q tests/test_imagens_pokemon_hd.py
flask --app app.py midia verificar
```

`midia verificar` permanece responsável pelos uploads da aplicação; a pasta de imagens HD é gerenciada pelo sincronizador da Etapa 09.

## Etapa 09.1 — Reprocessamento das imagens que falharam (25/10/2026)

**Resultado informado pelo usuário após a Etapa 09:** 953 formas atualizadas e 110 ignoradas/com falha. Nas linhas explicitamente anexadas há 88 erros HTTP 404, um timeout (Beautifly) e um limite de resposta (Mew). O relatório começa em Armaldo: pelas 54 formas anteriores do catálogo, 34 atualizadas e 20 restantes, estas últimas provavelmente correspondem às 18 variantes de Arceus e às duas de Aegislash. A lista descritiva completa está em `docs/FALHAS_SINCRONIZACAO_HD_09_1.md`.

Correções do sincronizador:

- Tradução explícita de códigos de formas locais para identificadores da PokéAPI (por exemplo, `rotom-geladeira` → `rotom-frost` e `aegislash-escudo` → `aegislash-shield`). As variantes continuam distintas; não converter automaticamente para a espécie base.
- Consulta ao endpoint `pokemon-form` quando a variante não possui arte HD no endpoint `pokemon`; cobre variações cosméticas como as placas de Arceus quando houver arte HD própria.
- Para cada visual normal/Shiny: preferir HOME, tentar official-artwork quando HOME estiver inacessível e **salvar separadamente** a imagem válida, mesmo quando a outra falhar.
- Até três tentativas com espera curta para erros de rede temporários, timeouts e respostas 408/429/5xx; erros 404 seguem para a próxima fonte/variante sem repetir a mesma URL.
- Limite de tamanho do **JSON da API** ampliado para 5 MB; arquivos PNG continuam limitados a 8 MB e com tamanho mínimo de 256 px.
- Grava `static/img/pokemon-hd/relatorio-ultima-sincronizacao.json` com pendências por forma e por variante normal/Shiny, inclusive o motivo. O manifesto histórico continua registrando cada alteração.
- `minior-nucleo` não recebe arbitrariamente a imagem de uma cor específica. Se a fonte HD não especificar forma apropriada, a imagem original é preservada.

**Primeiro veja exatamente o que ainda falta no banco atual:**

```powershell
flask --app app.py midia pokemon-hd-pendentes
```

**Rode a simulação, depois aplique apenas às pendências:**

```powershell
flask --app app.py midia pokemon-hd
flask --app app.py midia pokemon-hd --aplicar
flask --app app.py midia pokemon-hd-pendentes
```

Imagens já locais não são baixadas novamente. Se quiser validar antes em poucos casos:

```powershell
flask --app app.py midia pokemon-hd --aplicar --codigo mew
flask --app app.py midia pokemon-hd --aplicar --codigo rotom-geladeira
flask --app app.py midia pokemon-hd --aplicar --codigo arceus-agua
```

**Importante:** mesmo que o comando reduza bastante as 110 pendências, não há garantia de 100% das formas **em HD normal e Shiny** em fontes públicas. Formas sem arte HD válida preservam as URLs anteriores; isso evita representar uma forma diferente por engano. Essas pendências podem exigir artes dedicadas adicionadas manualmente, respeitando direitos de uso. Este pacote **não traz novos downloads** e **não modifica o banco automaticamente**. Não há migration.


## Etapa 09.2 — Resgate das oito imagens restantes (25/10/2026)

**Relatório recebido após 09.1:** 8 formas com ao menos uma arte pendente:

| Forma | Variante(s) pendente(s) | Estratégia 09.2 |
|---|---|---|
| `eevee-parceiro` | Shiny | Em modo `--representativas`: Shiny da espécie Eevee; não é uma arte exclusiva do parceiro |
| `frillish` | Normal + Shiny | HOME/official-artwork e reserva WebP 512 da espécie nº 592 |
| `jellicent` | Normal + Shiny | HOME/official-artwork e reserva WebP 512 da espécie nº 593 |
| `minior-nucleo` | Normal + Shiny | Em modo `--representativas`: núcleo vermelho de Minior, apenas cor representativa |
| `pikachu-parceiro` | Shiny | Em modo `--representativas`: Shiny da espécie Pikachu; não é uma arte exclusiva do parceiro |
| `pyroar` | Normal + Shiny | HOME/official-artwork e reserva WebP 512 da espécie nº 668 |
| `zacian-heroi` | Normal + Shiny | IDs da forma Hero, nº 888, sem substituição por Crowned |
| `zamazenta-heroi` | Normal + Shiny | IDs da forma Hero, nº 889, sem substituição por Crowned |

**O que mudou**: o sincronizador examina também as referências WebP de geração VIII/IX retornadas pela PokéAPI e, para as cinco espécies listadas, caminhos numéricos explícitos do repositório de sprites da PokéAPI. O arquivo pode ser salvo localmente como PNG ou WebP, conforme os bytes de origem; imagens WebP passam por verificação de cabeçalho, comprimento e dimensões. Continua exigindo mínimo de 256 × 256 e máximo de 8 MB.

**Aproximações não automáticas:** Pikachu Parceiro e Eevee Parceiro podem não ter uma arte Shiny exclusiva, e Minior Núcleo cobre várias cores. Para não alterar a representação sem consentimento, esses três casos só usam uma imagem representativa quando o mestre acrescenta `--representativas`. O relatório JSON identifica essas atualizações pelo campo `representativa: true`. Não é garantido que tais aproximações sejam idênticas à forma original.

### Instalação e repetição apenas das pendências

Aplique o pacote incremental sobre a versão com 09.1, faça backup do banco e instale somente os arquivos modificados. **Sem migration nem novas dependências Python.**

```powershell
python -m pytest -q tests/test_imagens_pokemon_hd.py
flask --app app.py midia pokemon-hd-pendentes
flask --app app.py midia pokemon-hd --aplicar
flask --app app.py midia pokemon-hd-pendentes
```

Se o objetivo for ter uma imagem local também para as variantes sem arte exclusiva (representações aproximadas), execute **se concordar com as aproximações**:

```powershell
flask --app app.py midia pokemon-hd --aplicar --representativas
flask --app app.py midia pokemon-hd-pendentes
```

O comando pula imagens já locais e artes personalizadas. Se uma fonte retornar 404, timeout, tamanho insuficiente ou erro de formato, mantém-se o link anterior. **Sem acesso ao PostgreSQL nem à rede remota do usuário nesta entrega, a recuperação das oito não pode ser confirmada antes de executar esses comandos.** Os arquivos `static/img/pokemon-hd/` gerados durante o download devem acompanhar a publicação do site.
