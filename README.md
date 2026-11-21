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
