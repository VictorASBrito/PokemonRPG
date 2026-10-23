# Pokémon, equipe e Box no PostgreSQL

Nesta etapa, o PostgreSQL passa a ser a fonte oficial para:

- Pokémon pertencentes aos jogadores;
- equipe ativa;
- Box única de 100 espaços;
- ordem dos Pokémon na equipe e na Box;
- espécie ou forma;
- apelido, gênero e variação Shiny;
- natureza e seus modificadores;
- status ativos;
- item carregado;
- PV atual;
- bônus individuais de atributos;
- golpes equipados;
- dashboard do jogador;
- histórico de criação, edição, movimentação e remoção.

Os arquivos JSON não são mais consultados pelas telas de Pokémon, equipe, Box ou
dashboard. Eles devem ser preservados apenas como backup e fonte de importação
legada.

O item carregado é exibido na ficha do Pokémon, mas sua alteração ocorre pela
tela oficial de inventário para manter as quantidades consistentes. Consulte
`ITENS_INVENTARIO.md`.

## 1. Preserve os dados locais

Antes de substituir o projeto, mantenha:

```text
.env
data/
```

A pasta `data/` não é mais a fonte oficial da aplicação, mas ainda é importante
como cópia de segurança da carga original.

## 2. Aplique a migration

Esta versão adiciona a migration:

```text
f20c9d44a1b7_simplificar_posicoes_pokemon.py
```

Ela recria a restrição de posição dos Pokémon sem o modo `DEFERRABLE`. A
reordenação agora é feita pelo serviço com posições temporárias positivas, o que
mantém a regra compatível com PostgreSQL e simplifica os testes automatizados.

Execute:

```powershell
flask --app app.py db upgrade
```

Confira:

```powershell
flask --app app.py db current
```

Resultado esperado:

```text
f20c9d44a1b7 (head)
```

Não execute novamente `dados importar`. Os Pokémon já carregados continuam nas
mesmas tabelas e não são recriados por esta migration.

## 3. Valide os Pokémon

Execute:

```powershell
flask --app app.py pokemon verificar
```

O comando confere:

- quantidade de formas, golpes e tipos ativos;
- quantidade de Pokémon na equipe e na Box;
- limite atual da equipe;
- capacidade atual da Box;
- localizações inválidas;
- posições repetidas ou não sequenciais;
- jogadores acima dos limites configurados.

Resultado esperado no final:

```text
Pokémon, equipes e Boxes estão consistentes no PostgreSQL.
```

## 4. Reinicie e teste

```powershell
python app.py
```

Saia de uma sessão antiga e entre novamente. Depois valide:

1. dashboard do jogador;
2. tela da equipe;
3. tela da Box;
4. criação de Pokémon por um espaço vazio da Box;
5. edição de espécie, natureza, status, bônus e golpes;
6. entrega e retirada do item carregado pela tela de inventário;
7. inclusão do Pokémon no final da equipe;
8. retirada do Pokémon para o final da Box;
9. pesquisa dinâmica da Box;
10. alteração do nível do jogador e recálculo de toda a equipe.

## Tabelas principais

```text
pokemons
pokemon_golpes
pokemon_status
pokemon_bonus_atributos
formas_pokemon
forma_pokemon_atributos
forma_pokemon_tipos
golpes
naturezas
natureza_modificadores
status_condicoes
itens
personagens
historico_alteracoes
```

## Regras preservadas

- o nível do Pokémon é sempre o nível do personagem;
- novos Pokémon são criados somente na Box;
- a equipe possui o limite configurável, atualmente seis;
- existe uma única Box, atualmente com 100 espaços;
- ao entrar na equipe, o Pokémon vai para o final dela;
- ao sair da equipe, o Pokémon vai para o final da Box;
- PP, experiência, amizade, taxa de captura e Struggle permanecem fora dos
  cálculos da campanha;
- alterações de catálogo são lidas diretamente das tabelas administráveis.

## JSON legado

Os serviços antigos baseados em JSON permanecem no repositório somente para:

- importação inicial;
- comparação de dados históricos;
- preparação pontual de configurações antigas ainda não cadastradas.

As rotas normais de autenticação, ficha, dashboard, Pokémon, equipe e Box não
dependem mais deles.
