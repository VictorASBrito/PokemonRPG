# Ankar — Auditoria das planilhas oficiais (Etapa 10A.1.1)

**Estado:** implementação preparada em 27/10/2026 sobre o commit `871cfaefbb1b6c59a0b001d1f9fa172d38cb1529` (`main` e `feature/att-frontend` equivalentes nessa revisão). Validação local pelo mestre ainda necessária.

## Escopo e segurança

O comando `flask --app app.py ankar auditar-planilhas` **somente lê** dois arquivos XLSX com `openpyxl`, localizando cabeçalhos por conteúdo (`d100`), e emite um relatório. **Não há conexão a PostgreSQL no serviço/comando, migração, importação, sorteio, alteração de arquivos ou correção automática.** Executar o comando não consome encontros, não atribui Pokémon e não automatiza captura.

Os dados são organizados em **local** (aba), **zona** (marcador `ZONA` da planilha, quando presente) e **terreno** (nome da coluna do cabeçalho d100). Para pontos de interesse com zonas lado a lado, a coluna do cabeçalho é considerada no vínculo com a zona. O serviço também lê como referência, quando presentes, habitat principal/secundário, terrenos informados, acessos e tempo de viagem ou tamanho. Não normaliza nomes de espécies ou formas.

## Instalação e execução (PowerShell, a partir da raiz do projeto)

```powershell
python -m pip install -r requirements-dev.txt
python scripts/aplicar_documentacao_10a1.py
python -m pytest -q tests/test_auditoria_ankar.py
flask --app app.py ankar auditar-planilhas `
  --rotas "Região de Ankar - Rotas - PokéRPG.xlsx" `
  --cidades "Ankar - Cidades e Pontos de Interesse - PokéRPG.xlsx" 
```

Por padrão, o relatório mostra os primeiros 50 achados. `--todos` exibe todos e `--formato json` gera JSON no terminal (sem escrever arquivos). Para guardar JSON no disco, pode-se redirecionar a saída **voluntariamente**:

```powershell
flask --app app.py ankar auditar-planilhas `
  --rotas "Região de Ankar - Rotas - PokéRPG.xlsx" `
  --cidades "Ankar - Cidades e Pontos de Interesse - PokéRPG.xlsx" `
  --formato json > auditoria-ankar.json
```

**Códigos de saída:** `0` sem erros (avisos permitidos); `1` se houver erros d100 ou falhas de leitura; `2` normalmente indica argumentos inválidos ou arquivos não encontrados no processamento das opções. Um código `1` é esperado na revisão atual das planilhas: indica dados que o mestre deve revisar, não falha de execução do programa. JSON pode ser lido mesmo com código `1` por inconsistências; falhas de abertura são mensagens de erro no terminal.

Se as planilhas estiverem fora da raiz do projeto, use os caminhos absolutos nos argumentos. O ZIP não contém as planilhas originais.

## Validações realizadas

- Faixas d100 simples ou intervalos inclusivos `1-10`, `1–10`, `1—10` (e valores inteiros isolados).
- Erro: formato inválido, faixa invertida, fora de `1..100`, d100 em branco, nomes Pokémon em branco, cabeçalhos incompletos, tabelas sem entradas, intervalos sobrepostos.
- Aviso: lacunas na cobertura d100 (podem ser intencionais; se houver d100 inválido, a lacuna pode ser apenas aparente), espécie repetida na mesma tabela, percentual de captura ausente, campo de espécie com marcador não identificado, aba sem tabelas.
- Datas convertidas pelo Excel: `data_excel` é erro de leitura semântica; conserva a representação recebida de `openpyxl`, a aba, a coluna/célula, o terreno e a zona. **Não** converte `2020-05-01` para `1-5` ou qualquer outra interpretação.
- O marcador `x` recebe `marcador_x` (aviso), **sem pressupor** que seja um encontro vazio.
- `% Captura` é lido e validado como valor declarado de captura (0–100), **nunca usado como peso ou chance de aparecimento**.

## Auditoria exploratória das planilhas fornecidas

Execução direta do serviço com as duas planilhas originais fornecidas para este chat, em ambiente isolado do aplicativo:

| Indicador | Valor |
| --- | ---: |
| Abas / locais lidos | 120 (73 rotas + 47 abas de cidades/pontos, incluindo 1 apresentação regional) |
| Tabelas d100 encontradas | 352 |
| Entradas lidas | 2.683 |
| Erros registrados | 313 |
| Avisos registrados | 626 |

Esta contagem inclui linhas incompletas e marcadores `x`, não significa que existam 2.683 encontros utilizáveis. Dentre os problemas detectados: Pyukumuku `C10` (`56-60`) e Skrelp `C11` (`60-75`) em `ROTA 1`, sobrepostos no resultado 60; datas Excel nos terrenos e locais correspondentes; diversos d100 em branco em pontos de interesse. Há `x` e entradas rotuladas `Random` cujo significado precisa de decisão do mestre. O relatório completo está em `docs/RELATORIO_AUDITORIA_ANKAR_2026-10-27.txt`.

**Não aplicar correções automáticas**. Recomenda-se revisar primeiro as datas Excel, sobreposições e faixas inválidas, registrando decisões de forma rastreável, antes de qualquer importação.

## Arquivos desta etapa

- `app/services/auditoria_ankar_service.py`: parser e auditoria, independente de Flask e do ORM.
- `app/commands/ankar.py`: grupo de comandos e saída de texto/JSON.
- `app/commands/__init__.py` e `app/__init__.py`: registro Flask CLI.
- `requirements.txt`: nova dependência `openpyxl`.
- `tests/test_auditoria_ankar.py`: fixtures XLSX e verificações de regressão.
- `docs/AUDITORIA_PLANILHAS_ANKAR.md`, `docs/RELATORIO_AUDITORIA_ANKAR_2026-10-27.txt`: documentação e resultado observado.
- `scripts/aplicar_documentacao_10a1.py`: acrescenta notas de continuidade e diário preservando integralmente o texto anterior.

**Sem migrations. Sem novas tabelas. Sem alteração de dados do jogo.**

## Próxima entrega

Após execução e validação do mestre, tratar a etapa de persistência e aprovação dos dados auditados. Definir primeiro o significado de `x`, esclarecer datas ambíguas e revisar sobreposições; não avançar automaticamente para banco ou gerador de encontros.
