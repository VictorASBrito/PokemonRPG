# 10E.2.1.2 — Saneamento controlado da Pokédex de Ankar

**Status:** implementação em branch, sem execução sobre o banco real.
**Pré-requisito:** PR #11 incorporado à `main`; PR #12 (Unicode/cp1252)
pode ser incorporado separadamente. Nenhuma alteração de esquema.

## Base factual: auditoria enviada pelo mestre

O arquivo `auditoria-pokedex.json` anexado ao repositório registra:

| Medida | Valor |
|---|---:|
| Espécies na fonte | 898 |
| Formas na fonte | 1.064 |
| Espécies no PostgreSQL | 897 |
| Formas no PostgreSQL | 1.066 |
| Formas oficiais presentes | 1.064 |
| Erros | 2 |
| Avisos | 897 |

Os dois erros são o mesmo problema de origem: a forma `nidoran-2`
(Nidoran♂, #032) está ligada à espécie `nidoran` (Nidoran♀, #029);
a espécie masculina não foi cadastrada separadamente. Há 897 espécies
oficiais com `numero=NULL`. Existem duas formas adicionais que **não**
podem ser deletadas. A auditoria registrou zero Pokémon ativos na forma
`nidoran-2`, mas esse número não substitui a conferência ao aplicar.

O relatório antigo tem sinais de caracteres corrompidos pelo terminal
Windows. O saneador **não usa esse JSON como fonte para gravar dados**:
consulta o banco atual e `data/catalogo/pokemons.json` versionado.

## O que será alterado após autorização

O único reparo permitido é:

1. Criar a espécie oficial `nidoran-m` com nome Nidoran♂ e número #032,
   se ainda não existir.
2. Vincular `FormaPokemon.codigo = nidoran-2` à espécie masculina,
   **mantendo o ID da forma**; não recriar Pokémon dos jogadores.
3. Preencher apenas números `NULL` das espécies oficiais da fonte:
   #001–#898, sem confundir os 1.064 índices de formas com números
   nacionais e sem sobrescrever números existentes.

A importação futura também passa a distinguir os dois Nidoran por meio
da função `codigo_especie_oficial` compartilhada em
`app/services/importacao/utils.py` — por isso o erro não reaparece
numa nova importação.

As duas formas extras, espécies personalizadas, Pokémon capturados,
itens, níveis, PV, habilidades e demais dados da campanha permanecem
intocados. O comando grava histórico individual dos valores alterados e
confere a auditoria **antes do commit**; em caso de erro faz rollback.

## Execução segura no PowerShell (somente depois de incorporar o PR)

**1. Atualize o código e realize backup real do PostgreSQL**, fora
do repositório. Valide que o backup pode ser restaurado; o comando não
faz `pg_dump` automaticamente. Não confunda o arquivo JSON de auditoria
com um backup de banco. Os parâmetros `--backup-confirmado` e
`--confirmar` são declarações humanas, não validação técnica do dump.

**2. Simule; o padrão não grava nada:**

```powershell
flask --app app.py catalogo sanear-pokedex
```

O comando imprime contagens, forms extras preservadas, lista de bloqueios,
o total de operações e `Assinatura do plano: <64 caracteres hexadecimais>`.

**3. Confira o esperado para o relatório anterior:** 897 números
preenchidos, 1 espécie masculina criada, 1 vínculo corrigido, 2 formas
extras preservadas, 899 operações registradas. Se o banco tiver mudado
desde a auditoria, os totais podem ser menores. Qualquer divergência
ou bloqueio exige revisão antes de prosseguir.

**4. Após backup e revisão, execute com a assinatura copiada literalmente:**

```powershell
flask --app app.py catalogo sanear-pokedex --aplicar --plano ASSINATURA_DA_SIMULACAO --backup-confirmado --confirmar SANEAR-POKEDEX-ANKAR
```

A assinatura é um SHA-256 calculado sobre o catálogo versionado e o
estado relevante das espécies e formas persistidas. Se algo mudar
entre a simulação e a aplicação, a assinatura diverge e **nenhuma
alteração é confirmada**. No PostgreSQL, as linhas consultadas são
bloqueadas durante a etapa de aplicação.

**5. Valide o resultado:**

```powershell
flask --app app.py catalogo auditar-pokedex
flask --app app.py catalogo sanear-pokedex
```

O resultado esperado é **0 erros e 0 avisos de números ausentes**,
e a simulação seguinte deve apresentar `Operacoes propostas: 0`
(caso o banco e a fonte não tenham sido modificados por outro processo).

## Condições de bloqueio deliberadas

- Fonte com quantidade de espécies ou formas diferente da versão
  congelada (898/1.064).
- Número já preenchido mas incompatível: não sobrescrever.
- Códigos, nomes, vínculos ou ordens oficiais divergentes do catálogo.
- Nidoran♂ com vínculos fora do caso histórico conhecido ou UUID ocupado.
- Espécie oficial ausente além de Nidoran♂, ou duplicada.
- Assinatura antiga, falta de backup confirmado ou frase incorreta.

O saneamento não atende problemas além do diagnóstico atual; eles
exigem uma alteração explícita, revisada e documentada.

## Arquivos e regressões

- `app/services/importacao/utils.py`
- `app/services/importacao/catalogo_importer.py`
- `app/services/saneamento_pokedex_service.py`
- `app/commands/catalogo.py`
- `tests/test_saneamento_pokedex_10e2_1_2.py`
- `.github/workflows/test-saneamento-pokedex-10e2.yml`

Teste sugerido:

```powershell
python -m pytest -q tests/test_saneamento_pokedex_10e2_1_2.py tests/test_auditoria_pokedex_10e2_1.py tests/test_ordenacao_pokedex_10e1.py tests/test_importacao_fontes.py tests/test_catalogo_admin.py
```

**Próximo incremento:** depois de verificar o relatório pós-saneamento
do PostgreSQL de Ankar, iniciar a **10E.2.2 — Editor de relações**
(evoluções permanentes, formas alternativas reversíveis, Megas e variantes
regionais vinculadas sem transformação livre). A regra de nível segue
compartilhada com o treinador, sem experiência individual.
