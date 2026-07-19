# Pokémon RPG — Etapa 4

Aplicação Flask para gerenciamento da campanha, utilizando arquivos JSON como armazenamento.

## O que já funciona

### Acesso e campanha

- login e logout por sessão;
- perfis separados de mestre e jogador;
- cadastro de jogadores pelo mestre;
- criação automática de usuário e ficha JSON individual;
- listagem dos jogadores da campanha;
- gravação atômica em JSON e backup antes de alterações.

### Ficha do treinador

- dados pessoais, origem, classe e estilo de combate;
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
- espécie, apelido, gênero, nível, experiência, amizade, Shiny, natureza e status;
- item carregado e anotações individuais;
- até quatro golpes, com controle da quantidade de usos;
- cálculo do PP gasto e restante;
- imagem normal ou Shiny carregada a partir do catálogo;
- mudança de espécie para representar evoluções e formas diferentes.


### Boxes Pokémon

- um Box inicial com dez espaços;
- compra de novos Boxes por 100 pokédolares;
- custo, capacidade e quantidade inicial configuráveis;
- renomeação de Boxes;
- exclusão de Boxes vazios, mantendo sempre pelo menos um;
- movimentação entre equipe e Boxes;
- movimentação entre Boxes diferentes;
- bloqueio quando a equipe ou o Box de destino estiver cheio;
- cadastro de novos Pokémon diretamente em um Box;
- edição e remoção dos Pokémon guardados;
- filtros por nome, espécie, tipo, nível mínimo e Shiny;
- acesso completo pelo jogador e pelo mestre;
- migração automática da estrutura anterior para o `schema_version` 3.

### Cálculos automáticos atuais

- PV e atributos por nível;
- tabela própria de progressão para PV;
- tabela própria de progressão para Ataque, Defesa, Ataque Especial, Defesa Especial e Velocidade;
- bônus de Pokémon Shiny;
- bônus do estilo de combate do treinador;
- modificadores de natureza;
- efeitos de Queimando, Paralisado e Dormindo nos atributos aplicáveis;
- PP máximo, gasto e restante;
- dados de defesa pela Velocidade;
- dano do golpe Luta conforme o nível;
- experiência necessária para o próximo nível;
- bônus manuais para regras próprias da campanha.

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

As regras dos Pokémon estão em:

```text
data/catalogo/regras_pokemon.json
```

O segundo arquivo concentra:

- limites de nível, amizade, golpes e tamanho da equipe;
- PP base e crescimento por nível;
- bônus Shiny;
- faixas de progressão dos atributos;
- efeitos dos estilos de combate;
- naturezas;
- status disponíveis;
- regra de arredondamento;
- capacidade, quantidade inicial, custo e limite dos Boxes.

Isso permite que mudanças de balanceamento sejam realizadas sem espalhar valores fixos pelo HTML ou pelas rotas.

## Catálogos importados

```text
data/catalogo/pokemons.json
data/catalogo/golpes.json
```

Os arquivos foram extraídos da **Ficha Editável v2.5**. Para gerar novamente os catálogos após atualizar a planilha, execute:

```bash
python scripts/importar_catalogos.py "C:\caminho\Ficha Editável v2.5.xlsx" --destino data/catalogo
```

O importador usa apenas recursos da biblioteca padrão do Python e não depende do Excel instalado.

## Estrutura do JSON do jogador

Cada jogador possui um arquivo em:

```text
data/campanhas/ankar/jogadores/<jogador_id>.json
```

Estrutura resumida:

```json
{
  "schema_version": 3,
  "treinador": {},
  "inventario": [],
  "insigneas": [],
  "pokemons": [],
  "equipe": ["pkm_exemplo"],
  "boxes": [
    {
      "id": "box_exemplo",
      "nome": "Box 1",
      "limite": 10,
      "pokemon_ids": []
    }
  ],
  "pokedex": {}
}
```

`pokemons` armazena os dados completos de cada parceiro. `equipe` e `boxes[].pokemon_ids` guardam apenas identificadores, evitando duplicação da ficha do Pokémon durante as movimentações.

## Testes

Instale as dependências de desenvolvimento:

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes atuais cobrem:

- cadastro e edição da ficha do treinador;
- progressão de atributos por nível;
- aplicação do estilo de combate;
- inclusão e edição de Pokémon;
- seleção de golpes;
- limite máximo de seis Pokémon na equipe;
- movimentação entre equipe e Box;
- compra, renomeação e exclusão de Box vazio;
- cadastro direto em Box;
- bloqueio de movimentação quando a equipe está cheia.
