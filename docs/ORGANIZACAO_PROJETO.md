# Organização técnica antes das próximas etapas

## Fonte oficial do projeto

- PostgreSQL é a fonte oficial dos dados persistentes.
- Os JSON em `data/` permanecem apenas como legado, importação e referência.
- Arquivos enviados pela interface ficam em `static/uploads/` e não são armazenados no banco; o banco guarda apenas a URL relativa.
- `.env`, `.venv/`, caches, logs de execução e uploads não devem ser commitados.

## Backups

Um backup completo precisa conter dois componentes:

1. dump do PostgreSQL;
2. conteúdo de `static/uploads/`.

Sem a pasta de uploads, os registros continuam no banco, mas imagens enviadas localmente deixam de existir.

## Organização que vale fazer antes de módulos grandes

### 1. Consolidar o Git

Criar um commit estável depois de aplicar migrations e executar os diagnósticos. Evite guardar versões completas do projeto dentro do próprio repositório.

### 2. Separar as rotas do catálogo

`app/routes/catalogo_admin.py` já concentra espécies/formas, golpes e itens. Antes de acrescentar muitos novos módulos, a próxima refatoração estrutural recomendada é dividi-lo em blueprints menores, mantendo as URLs atuais.

Estrutura sugerida:

```text
app/routes/catalogo/
├── __init__.py
├── dashboard.py
├── pokemons.py
├── golpes.py
└── itens.py
```

Essa mudança é de organização e não precisa alterar o comportamento do site.

### 3. Isolar o legado JSON

As rotas atuais de jogador, Pokémon e Box já usam os serviços PostgreSQL. Ainda existem módulos antigos como `jogador_service.py`, `pokemon_service.py`, `box_service.py`, `compatibilidade_legado.py` e os modelos JSON em `app/models/jogador.py` e `app/models/pokemon.py`. Eles devem ser movidos para uma área `app/legacy/` ou removidos depois de confirmar que os comandos de importação e testes antigos não dependem mais deles.

Não é recomendável apagar esses arquivos no mesmo commit de uma funcionalidade nova; faça essa limpeza em uma etapa isolada.

### 4. Dividir serviços que cresceram demais

Os maiores pontos de concentração atuais são `pokemon_db_service.py`, `golpe_admin_service.py`, `personagem_service.py` e os serviços administrativos do catálogo. Antes do assistente de combate, vale dividir leitura, escrita, cálculos e sincronização em módulos menores para reduzir regressões.

### 5. Manter serviços por domínio

O padrão atual deve continuar:

- rota: HTTP, sessão, mensagens e redirecionamentos;
- serviço: regras de negócio e transações;
- modelo: estrutura persistida;
- template/JS: interface.

Uploads agora ficam centralizados em `app/services/upload_service.py` para evitar lógica de arquivos espalhada pelas rotas.

### 6. Diagnósticos antes de cada nova etapa

Execute:

```powershell
flask --app app.py db current
flask --app app.py catalogo verificar
flask --app app.py inventario verificar
flask --app app.py midia verificar
pytest -q
```

### 7. Segurança antes de publicar na internet

Antes de hospedar o sistema fora da rede local, ainda será necessário consolidar CSRF, limites globais de requisição, tratamento de erros de produção, política de cookies/HTTPS e estratégia automatizada de backups.

## Uploads de imagens

Os formulários administrativos de itens e formas Pokémon aceitam:

- PNG;
- JPG/JPEG;
- WEBP;
- GIF;
- até 8 MB por arquivo por padrão.

O nome original do arquivo não é reutilizado. O sistema gera um UUID para cada upload e valida a assinatura básica do arquivo antes de gravá-lo.

Diretórios atuais:

```text
static/uploads/itens/
static/uploads/pokemons/
```

URLs externas `http` e `https` continuam aceitas. Quando um upload e uma URL são enviados juntos, o upload tem prioridade.
