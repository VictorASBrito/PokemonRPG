# Pokémon RPG — Regras personalizadas da campanha

Aplicação Flask para gerenciamento da campanha. Autenticação, ficha, dashboard, Pokémon, equipe e Box usam o PostgreSQL como fonte oficial. Os JSON permanecem somente como backup e fonte de importação legada.

## O que já funciona

### Acesso e campanha

- login e logout por sessão;
- perfis separados de mestre e jogador;
- cadastro de jogadores pelo mestre;
- criação automática de usuário e personagem no PostgreSQL;
- listagem dos jogadores da campanha pelo banco;
- ficha, inventário, insígnias e histórico de alterações no PostgreSQL;
- Pokémon, equipe e Box armazenados integralmente no PostgreSQL;
- painel administrativo para espécies e formas Pokémon.

### Dashboard do jogador

- painel em duas colunas, separando personagem e equipe;
- foto do personagem por URL, com avatar de inicial como alternativa;
- nome do jogador e nome do personagem exibidos separadamente;
- nível, PV, idade, números shiny, pokédolares e atributos sempre visíveis;
- equipe ativa em grade de duas colunas;
- cartões com foto, apelido, espécie, nível compartilhado, barra de vida, atributos base e golpes;
- espaços vazios da equipe usados como atalho para abrir a Box;
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

### Box Pokémon

- uma única Box com 100 espaços;
- novos Pokémon só podem ser criados por um espaço vazio da Box;
- espaços vazios da equipe não criam Pokémon diretamente;
- ao sair da equipe, o Pokémon é colocado no final da Box;
- ao sair da Box, o Pokémon é colocado diretamente no final da equipe, caso exista vaga;
- pesquisa dinâmica por nome, apelido ou espécie, priorizando correspondências no início;
- filtros adicionais por tipo e Shiny;
- renomeação da Box;
- acesso completo pelo jogador e pelo mestre;
- sistema de compra, criação e exclusão de Boxes removido.

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

## Configurações e dados

A ficha do personagem, o inventário, as insígnias e suas configurações agora
são lidos e gravados no PostgreSQL. As opções de origem, classe, estilo de
combate e limites de atributos ficam em `regras` e `regra_valores`.

Os arquivos abaixo permanecem apenas como fonte de importação e backup legado:

```text
data/catalogo/regras_treinador.json
data/catalogo/regras_pokemon.json
data/catalogo/pokemons.json
data/catalogo/golpes.json
```

Eles não são consultados pelas rotas normais da aplicação. Consulte
`FICHA_POSTGRESQL.md` e `POKEMON_POSTGRESQL.md` para a implantação.

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
- criação de Pokémon exclusivamente pela Box;
- seleção de golpes sem contagem de usos;
- limite máximo de seis Pokémon na equipe;
- movimentação entre equipe e Box com preservação da ordem;
- migração para uma Box única de 100 espaços;
- pesquisa dinâmica e renomeação da Box;
- renderização do dashboard;
- gerenciamento administrativo de espécies, formas e golpes;
- editor visual de efeitos e vínculos de aprendizado.

## PostgreSQL

O banco relacional é a fonte oficial das funcionalidades principais do sistema.

Consulte [BANCO_DE_DADOS.md](BANCO_DE_DADOS.md) para configurar o `.env`, validar a conexão e aplicar a primeira migration.

## Autenticação PostgreSQL

Depois da importação inicial, a autenticação e o cadastro de jogadores passam a
usar o PostgreSQL. Consulte `AUTENTICACAO_POSTGRESQL.md` e valide os vínculos com:

```powershell
flask --app app.py usuarios verificar
```

## Ficha e dashboard PostgreSQL

A ficha, o dashboard, os atributos, o inventário e as insígnias já usam o
PostgreSQL. Para aplicar esta etapa:

```powershell
flask --app app.py db upgrade
flask --app app.py ficha preparar
flask --app app.py ficha verificar
```

Consulte `FICHA_POSTGRESQL.md` para os detalhes.

## Pokémon, equipe e Box PostgreSQL

Para aplicar a etapa que remove a ponte JSON das telas de Pokémon:

```powershell
flask --app app.py db upgrade
flask --app app.py pokemon verificar
```

A migration atual esperada é `a31d7e8c4f20 (head)`. Consulte
`POKEMON_POSTGRESQL.md` para os testes manuais e detalhes da estrutura.

## Painel administrativo do catálogo

O mestre pode pesquisar, criar, editar, duplicar, desativar e simular espécies
e formas Pokémon diretamente no PostgreSQL. Esta etapa não cria migration nova.
Valide com:

```powershell
flask --app app.py catalogo verificar
```

Consulte `CATALOGO_ADMIN.md` para espécies e formas, e
`CATALOGO_GOLPES.md` para golpes, efeitos e vínculos de aprendizado.
