# Pokémon RPG — Regras personalizadas da campanha

Aplicação Flask para gerenciamento da campanha, utilizando arquivos JSON como armazenamento.

## O que já funciona

### Acesso e campanha

- login e logout por sessão;
- perfis separados de mestre e jogador;
- cadastro de jogadores pelo mestre;
- criação automática de usuário e ficha JSON individual;
- listagem dos jogadores da campanha;
- gravação atômica em JSON e backup antes de alterações.

### Dashboard do jogador

- painel em duas colunas, separando personagem e equipe;
- foto do personagem por URL, com avatar de inicial como alternativa;
- nome do jogador e nome do personagem exibidos separadamente;
- nível, PV, idade, números shiny, pokédolares e atributos sempre visíveis;
- equipe ativa em grade de duas colunas;
- cartões com foto, apelido, espécie, nível compartilhado, barra de vida, atributos base e golpes;
- espaços vazios da equipe usados como atalho para cadastrar novos Pokémon;
- layout responsivo para computador, tablet e celular.

### Ficha do treinador

- dados pessoais, foto, nível, origem, classe e estilo de combate;
- seis atributos do treinador;
- cálculo automático dos PV máximos a partir de Saúde;
- números shiny, pokédolares, benefícios e anotações;
- inventário e insígnias editáveis.

### Equipe Pokémon

- equipe com até seis Pokémon;
- acesso à equipe pelo jogador e pelo mestre;
- catálogo com 1.064 espécies e formas;
- catálogo com 687 golpes;
- cadastro, edição e remoção de Pokémon;
- espécie, apelido, gênero, Shiny, natureza e status;
- item carregado e anotações individuais;
- até quatro golpes, sem controle de recurso ou quantidade de usos;
- imagem normal ou Shiny carregada a partir do catálogo;
- mudança de espécie para representar evoluções e formas diferentes.

### Nível compartilhado

O nível pertence ao jogador e é definido na ficha do treinador. Todos os Pokémon, estejam na equipe ou nos Boxes, usam automaticamente esse mesmo nível nos cálculos.

Exemplo: um jogador de nível 48 possui todos os seus Pokémon no nível 48. O nível não é armazenado individualmente dentro de cada Pokémon.

### Boxes Pokémon

- um Box inicial com dez espaços;
- compra de novos Boxes por 100 pokédolares;
- custo, capacidade e quantidade inicial configuráveis;
- renomeação e exclusão de Boxes vazios;
- movimentação entre equipe e Boxes;
- cadastro de novos Pokémon diretamente em um Box;
- filtros por nome, espécie, tipo e Shiny;
- acesso completo pelo jogador e pelo mestre;
- migração automática dos dados para o `schema_version` 4.

### Cálculos automáticos atuais

- PV e atributos usando o nível do jogador;
- tabela própria de progressão para PV;
- tabela própria de progressão para Ataque, Defesa, Ataque Especial, Defesa Especial e Velocidade;
- bônus de Pokémon Shiny;
- bônus do estilo de combate do treinador;
- modificadores de natureza;
- efeitos de Queimando, Paralisado e Dormindo nos atributos aplicáveis;
- dados de defesa pela Velocidade;
- bônus manuais para regras próprias da campanha.

Não fazem parte das regras atuais da campanha:

- experiência individual;
- amizade;
- taxa de captura automática;
- recurso e consumo dos golpes;
- golpe de emergência por esgotamento de recurso.

## Requisitos

- Python 3.10 ou superior;
- pip.

## Instalação

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse `http://127.0.0.1:5000`.

## Usuário inicial

- usuário: `mestre`
- senha: `mestre123`

Troque a senha e a chave secreta antes de publicar o projeto na internet.

## Arquivos de balanceamento

As regras do treinador estão em:

```text
data/catalogo/regras_treinador.json
```

Esse arquivo controla, entre outros valores, o nível mínimo, máximo e inicial do jogador.

As regras dos Pokémon estão em:

```text
data/catalogo/regras_pokemon.json
```

Esse arquivo concentra:

- limite de golpes e tamanho da equipe;
- bônus Shiny;
- faixas de progressão dos atributos;
- efeitos dos estilos de combate;
- naturezas;
- status disponíveis;
- regra de arredondamento;
- capacidade, quantidade inicial, custo e limite dos Boxes.

## Catálogos importados

```text
data/catalogo/pokemons.json
data/catalogo/golpes.json
```

Os arquivos foram extraídos da **Ficha Editável v2.5**. Para gerar novamente os catálogos após atualizar a planilha, execute:

```bash
python scripts/importar_catalogos.py "C:\caminho\Ficha Editável v2.5.xlsx" --destino data/catalogo
```

O importador ignora experiência base, taxa de captura e o custo de recurso dos golpes. Descrições cujo efeito dependia exclusivamente desse recurso são neutralizadas.

## Estrutura resumida do JSON

```json
{
  "schema_version": 4,
  "treinador": {
    "nivel": 48
  },
  "pokemons": [
    {
      "id": "pkm_exemplo",
      "especie_id": "bulbasaur",
      "golpes": [
        { "golpe_id": "arranhao" }
      ]
    }
  ],
  "equipe": ["pkm_exemplo"],
  "boxes": []
}
```

Os Pokémon não armazenam nível, experiência, amizade ou contagem de usos. O nível é lido diretamente da ficha do treinador.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes cobrem:

- cadastro e edição da ficha do treinador;
- nível compartilhado entre jogador e Pokémon;
- progressão de atributos;
- remoção dos campos desativados;
- inclusão e edição de Pokémon;
- seleção de golpes sem contagem de usos;
- limite máximo de seis Pokémon;
- movimentação entre equipe e Box;
- compra, renomeação e exclusão de Box vazio;
- renderização do dashboard.
