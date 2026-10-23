# Pokémon RPG — Diário de desenvolvimento e transferência entre chats

Este arquivo registra **eventos verificáveis**, decisões e pendências. Não substitui commits Git, migrações, backups ou testes. Sua finalidade é impedir perda de contexto quando uma conversa atinge o limite.

## Como registrar cada etapa

Copie este modelo ao concluir uma mudança:

```markdown
### AAAA-MM-DD — Título da etapa
- **Objetivo:** ...
- **Status:** CONCLUÍDO E TESTADO | DOCUMENTADO (NÃO TESTADO) | PARCIAL | BLOQUEADO
- **Branch/commit:** ...
- **Arquivos modificados:** ...
- **Esquema/migrations:** ... (ou nenhuma)
- **Decisões tomadas:** ...
- **Testes executados e resultados:** comando → passou/falhou/não executado
- **Riscos/pendências:** ...
- **Próxima ação:** ...
```

## Histórico recuperado

### 2026-10-23 — Validação de criação e edição de itens (correção incremental)
- **Objetivo:** iniciar a revisão do catálogo de itens, com foco em validação confiável e manutenção do estado do formulário ao corrigir erros.
- **Status:** PARCIAL — CÓDIGO IMPLEMENTADO; TESTES DE INTEGRAÇÃO BLOQUEADOS.
- **Base:** ZIP atualizado enviado pelo usuário com a documentação reunida em `docs/`.
- **Arquivos modificados:** `app/services/item_admin_service.py`, `app/routes/catalogo_admin.py`, `tests/test_itens_inventario.py`, `docs/CONTINUIDADE_PROJETO.md`, `docs/DIARIO_DESENVOLVIMENTO.md`, `docs/ITENS_INVENTARIO.md`, `docs/AGENTS.md`.
- **Esquema/migrations:** nenhuma alteração.
- **Alterações:** (1) preço inválido/decimal deixa de ser silenciosamente transformado em zero; preço máximo do formulário passa a ser verificado no servidor; (2) remoção de todos os efeitos é preservada no formulário de edição mesmo quando outro campo falha na validação.
- **Testes executados:** 7 casos isolados da função de preço (passaram); `python -m compileall` dos arquivos Python modificados (passou); `node --check static/js/itens-admin.js` (passou); tentativa `pytest -q tests/test_itens_inventario.py -x` (bloqueada por ausência de `flask`); tentativa de instalar dependências (bloqueada por indisponibilidade de rede).
- **Testes acrescentados, não executados:** regressão de preços inválidos e manutenção da remoção de efeitos após falha de validação.
- **Banco/produção:** nenhum banco real foi conectado ou alterado; sem confirmação de execução no navegador.
- **Próxima ação:** instalar dependências na máquina de desenvolvimento, executar os testes de integração e validar manualmente criação/edição/upload; obter erro real do usuário se persistir; então iniciar auditoria do catálogo PostgreSQL.

### 2026-10-23 — Introdução da documentação de continuidade
- **Objetivo:** reconstruir contexto técnico a partir do código fornecido e do resumo de conversa anterior; manter um prompt mestre dentro do repositório.
- **Status:** CONCLUÍDO (DOCUMENTAÇÃO); FUNCIONALIDADES NOVAS NÃO IMPLEMENTADAS.
- **Branch/commit de origem:** `feature/att-frontend` / `9517d8a` (ZIP fornecido pelo usuário).
- **Arquivos introduzidos:** `AGENTS.md`, `docs/CONTINUIDADE_PROJETO.md`, `docs/DIARIO_DESENVOLVIMENTO.md`.
- **Esquema/migrations:** nenhuma alteração.
- **Principais descobertas:** Flask/PostgreSQL/Jinja; nível compartilhado; cadastro de itens existente; geração e combate reservados; quatro perfis de acesso; Box única com 100 vagas.
- **Validação:** leitura estática da estrutura, documentação, rotas, serviços, modelos e migrations. Tentativa de coletar testes bloqueada porque Flask não está instalado no ambiente de inspeção. Não houve acesso ao banco real.
- **Proteção de dados:** o pacote de aplicação recomendado contém somente os novos documentos; não inclui `.env`, Git, backups ou uploads de usuário.
- **Pendências:** identificar/reproduzir eventual problema real no cadastro de itens; auditar dados existentes; planejar geração visual/atribuição; implementar painel compartilhado até 16 times.
- **Próxima ação:** examinar o defeito específico do formulário de cadastro de itens na instalação atual, com os dados e erros observados pelo usuário, antes de editar lógica existente.

### 2026-10-23 — Últimas mudanças preexistentes identificadas no repositório
- **Status:** HISTÓRICO RECUPERADO, NÃO VALIDADO EM EXECUÇÃO.
- **Commits recentes:** `9517d8a` — ajustes de inventário; `13ad161` — atualização na mochila; `7ab5a6e` — ajustes na tela de movimentos; `8d6438b` — seletores visuais e catálogos; `0bbe90b` — permissões de usuário.
- **Atenção:** a árvore de trabalho do ZIP inclui uma alteração local não commitada em arquivo JSON de jogador; não descartar ou sobrescrever.
- **Última documentação visual associada:** `ALINHAMENTO_INVENTARIO_UI2.md`.

## Quadro de trabalho atual

| Área | Estado | Próxima providência |
|---|---|---|
| Autenticação, ficha, Pokémon, equipe, Box, inventário | Implementado no código; produção não verificada nesta revisão | Evitar regressões |
| Criar item no catálogo | Código existe; defeito alegado ainda não reproduzido | Diagnóstico e correção pontual |
| Auditoria do catálogo de itens | Planejado | Validar dados após correção do cadastro |
| Gerador visual com natureza/sexo e atribuição pelo mestre | Planejado; serviço placeholder | Planejar integração ao modelo Pokémon e à Box |
| Campo compartilhado com até 16 times | Planejado; rota/serviço placeholder | Projetar arena e sincronização |
| Atualização de documentação a cada etapa | Procedimento estabelecido | Revisar ao terminar cada implementação |
