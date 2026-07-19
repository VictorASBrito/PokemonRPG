# Ajustes de regras da campanha

## Nível compartilhado

- O nível agora pertence ao jogador, no campo `treinador.nivel`.
- Todos os Pokémon usam esse valor nos cálculos, incluindo os que estão nos Boxes.
- O campo `nivel` foi removido da estrutura individual dos Pokémon.
- Na migração de fichas antigas, quando o jogador ainda não possuir nível, o sistema aproveita o maior nível encontrado entre seus Pokémon antigos.

## Mecânicas desativadas

Foram removidos da ficha e dos cálculos automáticos dos Pokémon:

- experiência;
- amizade;
- taxa de captura;
- controle de recurso dos golpes;
- contagem de usos dos golpes;
- golpe de emergência por esgotamento de recurso.

## Migração dos JSON

A estrutura atual usa `schema_version: 5`.

Ao abrir ou salvar fichas antigas, o sistema remove de cada Pokémon:

- `nivel`;
- `experiencia`;
- `amizade`;
- bônus de recurso;
- contagem de usos dos golpes.

Os golpes passam a ser armazenados apenas desta forma:

```json
{
  "golpe_id": "arranhao"
}
```

## Arquivos principais alterados

- `app/models/jogador.py`
- `app/models/pokemon.py`
- `app/services/jogador_service.py`
- `app/services/pokemon_service.py`
- `app/services/calculo_atributos.py`
- `app/services/box_service.py`
- `app/routes/jogadores.py`
- `app/routes/mestre.py`
- `app/routes/pokemons.py`
- `templates/jogador/ficha.html`
- `templates/jogador/dashboard.html`
- `templates/jogador/pokemon.html`
- `templates/jogador/equipe.html`
- `templates/jogador/boxes.html`


## Reformulação da Box

- A campanha agora utiliza uma única Box com 100 espaços.
- O sistema de compra, criação e exclusão de Boxes foi removido.
- Novos Pokémon só podem ser criados a partir de um espaço vazio da Box.
- Espaços vazios da equipe apenas direcionam o jogador para a Box.
- Ao retirar um Pokémon da equipe, ele é acrescentado no fim da Box.
- Ao adicionar um Pokémon da Box à equipe, ele é acrescentado diretamente no fim da equipe, caso haja vaga.
- A pesquisa por nome, apelido ou espécie reorganiza dinamicamente os cartões e coloca as correspondências no início.
- Fichas antigas com várias Boxes são unificadas automaticamente, preservando a ordem dos Pokémon armazenados.
