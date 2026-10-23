# Implantação do PostgreSQL — etapa inicial

Nesta etapa o projeto continua usando os arquivos JSON nas telas atuais. O PostgreSQL foi conectado e a estrutura relacional foi criada para a migração gradual.

## 1. Criar o arquivo `.env`

No PowerShell, na raiz do projeto:

```powershell
Copy-Item .env.example .env
```

Edite o arquivo `.env` e substitua `SUA_SENHA` pela senha do usuário `pokemon_rpg`:

```env
DATABASE_URL=postgresql+psycopg://pokemon_rpg:SUA_SENHA@localhost:5432/pokemon_rpg
POKEMON_RPG_SECRET_KEY=coloque-uma-chave-grande-e-aleatoria
POKEMON_RPG_CAMPANHA=ankar
```

O arquivo `.env` já está ignorado pelo Git.

## 2. Instalar as dependências

Com o ambiente virtual ativado:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Preparar as extensões do PostgreSQL

Execute `scripts/preparar_postgresql.sql` no DBeaver conectado ao banco `pokemon_rpg`.

O script:

- configura o banco em UTC;
- instala `pg_trgm`;
- instala `unaccent`;
- mostra o banco, o usuário e as extensões.

## 4. Validar a conexão

```powershell
flask --app app.py banco verificar
```

Resultado esperado:

```text
Conexão com o PostgreSQL realizada com sucesso.
Banco: pokemon_rpg
Usuário: pokemon_rpg
Timezone: UTC
Extensões: pg_trgm e unaccent instaladas.
```

## 5. Aplicar a migration inicial

A pasta `migrations` já está incluída. Não execute `flask db init` novamente.

```powershell
flask --app app.py db upgrade
```

Esse comando cria as 32 tabelas e registra a revisão na tabela `alembic_version`.

## 6. Conferir as tabelas

```powershell
flask --app app.py banco tabelas
```

Também é possível conferir pelo DBeaver:

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

Para conferir a versão da migration:

```sql
SELECT version_num
FROM alembic_version;
```

## 7. Executar os testes

```powershell
pip install -r requirements-dev.txt
pytest -q
```

## Estrutura criada

A migration inicial cria grupos de tabelas para:

- usuários, campanhas e personagens;
- atributos configuráveis;
- tipos e efetividades;
- espécies, formas e evoluções;
- golpes, categorias e aprendizagem;
- naturezas e modificadores;
- condições de status;
- itens, inventário e insígnias;
- Pokémon individuais, equipe, Box e golpes equipados;
- conjuntos de regras versionados;
- histórico de alterações.

## O que ainda não mudou

As rotas atuais continuam usando JSON. Ainda não foram migrados:

- login;
- criação de jogadores;
- ficha do personagem;
- Pokémon da equipe;
- Box;
- inventário.

A próxima etapa será criar um importador dos JSON atuais para as tabelas e validar os totais antes de trocar qualquer rota.

## Carga inicial dos arquivos JSON

Com as migrations aplicadas, use os comandos abaixo na ordem:

```powershell
flask --app app.py dados analisar
flask --app app.py dados importar --dry-run
flask --app app.py dados importar
flask --app app.py dados validar
```

- `dados analisar` lê somente os arquivos e apresenta as quantidades encontradas.
- `dados importar --dry-run` executa a carga dentro de uma transação e faz rollback ao final.
- `dados importar` grava os dados no PostgreSQL de forma idempotente.
- `dados validar` compara as quantidades do banco com as fontes JSON.

Os relatórios são gravados em `logs/`. A pasta não contém credenciais e pode ser
mantida localmente para auditoria da migração.

A importação mantém identificadores estáveis por meio de UUIDs determinísticos,
permitindo executar o comando novamente sem duplicar registros. Os catálogos JSON
continuam no projeto apenas como fonte de transição até que todas as telas passem a
usar o banco.
