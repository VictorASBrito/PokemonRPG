# Pokémon RPG — Ankar

Aplicação web de apoio à campanha **Pokémon RPG em Ankar**, com fichas de treinadores, Pokémon, equipes, Boxes, Catálogo, Inventário, Capturáveis e gestão de NPCs. O projeto usa **Flask + Jinja2 + JavaScript/CSS nativos**; os dados operacionais persistem no **PostgreSQL**.

> **Importante:** a campanha possui regras próprias. Leia [Adaptações de Ankar](docs/ALTERACOES_CAMPANHA.md) antes de modificar cálculos ou ações.

## Começar

Requisitos: Python 3.10+ e PostgreSQL configurado.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
```

Copie `.env.example` para `.env` e configure `DATABASE_URL` e uma `POKEMON_RPG_SECRET_KEY` segura. **Não publique o .env.** Com o banco preparado, execute:

```bash
python -m pytest -q
python app.py
```

A aplicação local é servida em `http://127.0.0.1:5000`. O arquivo `servidor_teste.py` é reservado ao teste remoto via túnel descrito em [docs/TESTES_REMOTOS_CLOUDFLARE.md](docs/TESTES_REMOTOS_CLOUDFLARE.md); não exponha o debugger Flask à Internet.

**Migrations:** conferir `flask --app app.py db current` e fazer backup antes de qualquer `db upgrade`. Scripts de instalação antigos por cópia de arquivos não devem ser executados sobre a `main` atual.

## Testes visuais reais com Playwright (10F.6)

A suíte `tests/visual/` utiliza **Chromium** com um servidor Flask local temporário, banco **SQLite isolado** e dados fictícios do jogador/Pokémon. **Não** acessa o túnel Cloudflare nem o PostgreSQL da campanha. Ao contrário dos contratos CSS estáticos, mede posições e dimensões que o navegador realmente calculou.

Instale as dependências de desenvolvimento e o navegador:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

Execute os testes de forma automática (headless):

```bash
python -m pytest -q tests/visual --browser chromium --tracing retain-on-failure --screenshot only-on-failure --output test-results
```

Para observar o navegador na sua máquina, acrescente `--headed`. Os casos cobrem a página inicial nas resoluções 390×844 e 1366×768, o sprite que abre a ficha, a altura dos atributos ao expandir/recolher um Pokémon e as categorias da Bag em 390px. Prints das telas fictícias são gerados em `test-results/screenshots/`, ignorado pelo Git. A variável opcional `POKEMON_RPG_TEST_URL` só modifica o destino do **smoke público**; os testes autenticados sempre usam o Flask temporário com SQLite e não precisam de credenciais reais.

O workflow `.github/workflows/test-playwright-ui-10f6.yml` instala Chromium no GitHub Actions, executa essa suíte em PRs para `main` e publica screenshots/traces como artefatos da execução. A automação é independente do ChatGPT Work e do TinyFish. Falhas visuais exigem inspeção das evidências antes de qualquer merge.

## Mapa do repositório

| Diretório | Responsabilidade |
| --- | --- |
| `app/routes/` | Endpoints HTTP, autenticação e autorização |
| `app/services/` | Regras da campanha, validação, cálculos e transações |
| `app/models/db/` | Modelos relacionais SQLAlchemy |
| `app/commands/`, `app/seed/` | Diagnóstico e preparação controlada de dados |
| `templates/` | Páginas Jinja2 e componentes |
| `static/css/`, `static/js/` | Apresentação e comportamento |
| `static/img/` | Imagens do site, itens e sprites de Pokémon **necessários** |
| `data/` | Fontes de catálogo e dados da região **não apagar** |
| `migrations/versions/` | Histórico do esquema do PostgreSQL **não apagar** |
| `scripts/` | Ferramentas operacionais/importação e testes locais |
| `tests/` | Regressões automatizadas |
| `docs/` | Arquitetura, regras, decisões e histórico |
| `relatorios/` | Auditorias e diagnósticos, quando pertinentes |

## Frontend: onde alterar

- **Estrutura do site:** `templates/base.html`.
- **Tokens e componentes globais:** `static/css/sistema-ui.css`.
- **Cores dos temas:** `static/css/geral.css` (base) e `static/css/tema.css` (escuro).
- **Navegação/visão responsiva:** `static/css/visual-global-10c5.css` e `static/css/padrao-visual-10d1.css`.
- **Layout de Pokémon:** `static/css/dashboard.css`, reutilizado também por `static/css/npc-painel.css` (somente estilos específicos).
- **Telas especializadas:** demais arquivos CSS de nome correspondente ao módulo.

Consulte o [guia de arquitetura visual](docs/ARQUITETURA_FRONTEND.md) antes de acrescentar regras globais. Não criar mais uma folha de “correções finais” se a alteração pode ser feita no componente/arquivo responsável.

## Documentação e manutenção

- [Arquitetura visual e padrões](docs/ARQUITETURA_FRONTEND.md)
- [Organização e política de limpeza](docs/ORGANIZACAO_REPOSITORIO.md)
- [Orientações para desenvolvimento](docs/AGENTS.md)
- [Contexto de continuidade](docs/CONTINUIDADE_PROJETO.md)
- [Diário de desenvolvimento](docs/DIARIO_DESENVOLVIMENTO.md)
- [Arquivos históricos](docs/historico/)
- [Regras especiais da campanha](docs/ALTERACOES_CAMPANHA.md)

A `main` é a base de referência. Para alterações estruturais, trabalhar em branch e abrir PR com testes. Não modificar banco real, uploads dos jogadores ou arquivos de campanha como “limpeza”.
