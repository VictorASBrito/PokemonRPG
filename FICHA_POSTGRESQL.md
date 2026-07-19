# Ficha e dashboard no PostgreSQL

Nesta etapa, o PostgreSQL passa a ser a fonte oficial para:

- informações do personagem;
- nível do jogador;
- PV atual;
- números Shiny;
- Pokédolares;
- atributos do personagem;
- benefícios, habilidades e anotações;
- inventário;
- insígnias;
- configurações exibidas na ficha;
- histórico de edições.

Os arquivos JSON ainda são mantidos temporariamente apenas como ponte para as
telas de Pokémon, equipe e Box. A ficha não lê mais o JSON como fonte oficial.

## 1. Atualizar o projeto

Preserve os arquivos locais antes de substituir a versão:

```text
.env
data/
```

Faça também um commit ou cópia de segurança.

## 2. Aplicar a migration

A nova migration remove a restrição que impedia PV negativo no personagem. Isso
mantém a regra da campanha que permite o personagem ficar abaixo de zero até o
limite negativo dos PV máximos.

```powershell
flask --app app.py db upgrade
```

Confira:

```powershell
flask --app app.py db current
```

Resultado esperado:

```text
7c4b1f91a2d3 (head)
```

## 3. Preparar as configurações da ficha

O comando abaixo usa o antigo JSON somente como carga inicial e grava no conjunto
de regras ativo:

- nível inicial;
- limites dos atributos;
- origens;
- classes;
- estilos de combate.

```powershell
flask --app app.py ficha preparar
```

O comando não sobrescreve valores já existentes. Para refazer deliberadamente a
carga inicial, use:

```powershell
flask --app app.py ficha preparar --forcar
```

Não use `--forcar` depois de começar a editar essas configurações diretamente no
banco, pois ele restaura os valores do arquivo legado.

## 4. Verificar a configuração

```powershell
flask --app app.py ficha verificar
```

Resultado esperado:

```text
Configurações encontradas: 10/10
A ficha está pronta para usar exclusivamente o PostgreSQL.
```

## 5. Iniciar e testar

```powershell
python app.py
```

Saia de qualquer sessão antiga e entre novamente. Depois valide:

1. abertura do dashboard do jogador;
2. abertura da ficha;
3. alteração do nome, nível ou atributos;
4. inclusão de um item e uma insígnia;
5. salvamento e recarregamento da página;
6. conferência dos dados no dashboard.

## Tabelas utilizadas

```text
personagens
atributos
personagem_atributos
categorias_item
itens
personagem_itens
insignias
personagem_insignias
conjuntos_regras
regras
regra_valores
historico_alteracoes
```

## Ponte temporária

Ao salvar a ficha, o sistema também atualiza uma cópia temporária no JSON do
jogador. Essa cópia é usada somente porque os cálculos e as telas dos Pokémon
ainda não foram convertidos. Uma falha nessa ponte não desfaz a gravação válida
no PostgreSQL.

A próxima conversão deve mover Pokémon, golpes equipados, equipe e Box para o
banco, permitindo remover definitivamente essa compatibilidade.
