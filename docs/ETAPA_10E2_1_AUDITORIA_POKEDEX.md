# 10E.2.1 — Auditoria de integridade da Pokédex (somente leitura)

**Status:** implementada em branch; validação em CI e revisão dos resultados reais
do PostgreSQL são etapas separadas. Nenhuma correção automática de dados.

## Objetivo e fonte
A 10E.1 ordena as 1.064 **formas** usando `configuracoes.ordem_catalogo`.
A 10E.1.1 exibe o número nacional da **espécie** calculado da fonte
`data/catalogo/pokemons.json`. O banco histórico ainda pode ter
`EspeciePokemon.numero = NULL` e vínculos de forma com espécie incorreta.

Esta auditoria usa a fonte versionada, deduz 898 espécies distintas pela
primeira ocorrência de cada nome-base e compara os dados persistidos,
**sem preencher números, mexer em FKs, importar formas ou alterar Pokémon**.

## Como executar

Na instalação com o banco de dados configurado:

```bash
flask --app app.py catalogo auditar-pokedex
flask --app app.py catalogo auditar-pokedex --todos
flask --app app.py catalogo auditar-pokedex --json > auditoria-pokedex.json
```

- Sem opções: imprime resumo (quantidades da fonte e banco), contagens por
  categoria e os primeiros **50 achados**, com erros antes de avisos.
- `--todos`: imprime **todos** os achados em texto.
- `--json`: emite JSON completo no stdout (adequado para arquivo privado de
  trabalho). Se houver erros, o processo encerra com código diferente de zero.
  O aviso de erro do Click pode aparecer no stderr, separado do JSON.
- O comando **não possui `--aplicar`**. A opção `--json` grava apenas no
  destino escolhido pelo shell; a aplicação não salva nem modifica dados.
- O relatório apresenta apenas contagens de Pokémon ativos associados à
  forma com problema, sem dados pessoais dos jogadores.

## Critérios

| Tipo | Severidade | Por que importa |
|---|---|---|
| `vinculo_especie_incorreto` | Erro | Nome da espécie na FK da forma não coincide com a referência |
| `vinculo_sem_especie` | Erro | Forma aponta para espécie não encontrada |
| `especie_oficial_ausente` | Erro se houver forma presente; senão aviso | Espécie oficial não existe separadamente no banco |
| `numero_nacional_incorreto` | Erro | Número preenchido diverge da posição nacional de referência |
| `especie_oficial_duplicada` | Erro | Mais de um registro não personalizado para o mesmo nome oficial |
| `forma_ativa_especie_inativa` | Erro | Forma utilizável aponta para espécie inativa |
| `numero_nacional_ausente` | Aviso | Número da espécie oficial ainda é NULL |
| `forma_oficial_ausente` | Aviso | Código de uma forma da fonte não foi encontrado no banco |
| `ordem_forma_divergente` | Aviso | Índice armazenado não corresponde à fonte versionada |
| `nome_forma_divergente` | Aviso | Nome da forma foi alterado em relação à origem |
| `forma_oficial_em_especie_personalizada` | Aviso | Forma original está vinculada a registro marcado como customizado |
| `numero_personalizado_colide_nacional` | Aviso | Número customizado coincide com 1–898; revisar convenção regional |

**Nidoran♀ e Nidoran♂ são espécies distintas:** a fonte possui a forma
`nidoran` com nacional #029 e `nidoran-2` com nacional #032.
A normalização legada pode reduzir ambos a `nidoran` e vincular o macho
à espécie da fêmea. O auditor verifica **nome exato** e código original
da forma; não corrige esse vínculo automaticamente. A reclassificação
de `nidoran-2` só poderá acontecer com cópia de segurança e revisão das
dependências, sem excluir Pokémon de jogadores.

A fonte não tem obrigação de conter formas próprias da região Ankar:
elas são preservadas. Espécies personalizadas sem número são aceitas;
quando o número customizado conflita com número nacional, é apenas um aviso.

## Testes automatizados

```bash
python -m pytest -q tests/test_auditoria_pokedex_10e2_1.py tests/test_ordenacao_pokedex_10e1.py tests/test_catalogo_admin.py
```

O workflow `test-auditoria-pokedex-10e2.yml` executa a regressão em SQLite,
testando referência de 1.064/898, Nidoran, numeração, formas ausentes,
associações inválidas, ausência de mutação e saídas texto/JSON do CLI.
**Testes em PostgreSQL de campanha real não são substituídos por SQLite.**

## Critérios para encerrar a auditoria

1. Rodar o comando contra a instalação do mestre, guardar relatório fora
   do repositório, anotar quantos erros e avisos existem.
2. Examinar primeiro `vinculo_especie_incorreto`, principalmente Nidoran♂,
   com as contagens de Pokémon associados.
3. Após backup de PostgreSQL, elaborar plano de saneamento **separado** e
   revisável (numeração oficial preenchida, respeito a personalizadas).
4. Somente então iniciar a **10E.2.2**, painel de relacionamentos
   de evolução, troca de forma, Mega e linhagens regionais.

**Nenhuma migration foi criada e nenhum reparo é executado por esta etapa.**
