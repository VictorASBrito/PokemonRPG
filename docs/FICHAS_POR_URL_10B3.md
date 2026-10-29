# Etapa 10B.3 — Fichas por URL sem conflito de sessão

## Objetivo

O navegador deixa de ter um único "jogador ativo". Cada um dos nove personagens cadastrados na entrada circular passa a ter uma URL própria que identifica seu contexto em cada requisição. O Mestre continua usando o login tradicional.

Exemplos, usando **logins**, não nomes exibidos nem posições dos sprites:

- `/p/lucas/` → dashboard do personagem associado a `lucas`
- `/p/mari/jogador/ficha` → ficha do personagem associado a `mari`
- `/p/jao/jogador/equipe` → equipe de `jao`
- `/p/jao/jogador/inventario` → inventário de `jao`
- `/selecionar` → círculo de personagens, independentemente do login atual

O caminho permanece nos links e formulários internos graças à reescrita WSGI com `SCRIPT_NAME`. Cada `/p/<login>/` tem cookie com nome e caminho próprios, separado do cookie de login de Mestre. A conta e o personagem são **revalidados no PostgreSQL em cada requisição**.

## O que permanece igual

- Perfis, permissões no banco, ações de ficha, Pokémon, Box, inventário, campo e capturáveis.
- Os nove sprites, nomes, posições e seus logins em `data/entrada_personagens.json`.
- Login tradicional do Mestre e contas de teste, sem compartilhamento da sessão com links de jogador.
- Nenhuma migration, alteração dos dados ou remoção de senhas.

## Cuidados

**A URL funciona como entrada sem senha.** Quem possuir ou descobrir uma URL de jogador pode visualizar **e executar as ações de jogador** nessa ficha, inclusive alterações de equipe e inventário. O acesso administrativo permanece bloqueado no prefixo; esta é a mesma decisão de acesso direto da Etapa 10B.1, agora propagada a todas as páginas de jogador.

Apenas os nove logins configurados são elegíveis, e cada perfil continua sendo conferido contra o banco. Qualquer alteração na configuração de logins deve ser seguida de verificação das URLs antigas.

Se o site for publicado fora do grupo, a orientação é restringir o acesso por rede/VPN ou voltar a exigir autenticação individual.

## Instalação

1. Fazer backup local / `git status` antes de aplicar.
2. Extrair o ZIP incremental na raiz, mantendo os caminhos.
3. Rodar `python scripts/instalar_fichas_por_url.py` (patch idempotente; backups `*.antes_10b3.bak`).
4. Rodar `python -m pytest -q tests/test_fichas_por_url_10b3.py tests/test_fichas_por_url_10b3_flask.py`.
5. Reiniciar Flask, abrir `/selecionar` e copiar a URL de dois personagens em duas abas, verificando ficha, equipe e inventário.

## Arquivos

- `app/services/fichas_url_middleware.py`: retém `/p/<login>` como contexto URL.
- `app/services/fichas_url_service.py`: cookies independentes, resolução do jogador e autorização.
- `app/routes/fichas_url.py`: seleção de personagens, mesmo com login tradicional ativo.
- `scripts/instalar_fichas_por_url.py`: integração em `app/__init__.py`, `app/routes/entrada_personagens.py`, `templates/base.html` e documentação; não sobrescreve arquivos completos.
- `tests/test_fichas_por_url_10b3.py` e `tests/test_fichas_por_url_10b3_flask.py`.

## Limitações conhecidas

A solução cobre os endpoints atualmente existentes de jogador. Caso sejam criadas novas rotas de jogador no futuro, elas precisarão entrar em `ENDPOINTS_JOGADOR`, com teste de autorização. Clientes JavaScript que usem URLs absolutas fixas, sem `url_for`/`data-*`, deverão ser adaptados. As rotas atuais do campo e de consulta de catálogo usam URLs geradas no servidor.


## Correção 10B.3.1 — Compatibilidade com alterações locais (28/10/2026)

O instalador original procurava um bloco literal em `app/routes/auth.py` e falhava caso o usuário tivesse personalizado a rota de saída. Isso impedia toda a instalação (sem escrita parcial), ocasionando 404 em `/p/<login>/...` e `/selecionar`.

Agora `auth.py` **não é modificado**. O logout de `/p/<login>/logout` é interceptado e tratado pelo `before_request` do módulo de URLs, após a validação do jogador. O cookie independente desse jogador é esvaziado e o navegador retorna para `/selecionar`. O cookie do Mestre mantém seu conteúdo. O logout normal `/logout` não muda.

As chaves retornadas pelo instalador agora são normalizadas em formato POSIX (`app/__init__.py`) em todos os sistemas, eliminando o falso negativo no Windows. O instalador preserva backups e a idempotência; nenhuma migration ou edição de dados foi realizada.

**Para aplicar:** substituir `scripts/instalar_fichas_por_url.py`, `app/services/fichas_url_service.py` e `tests/test_fichas_por_url_10b3.py`; executar o instalador e a suíte. As outras peças da 10B.3 precisam estar presentes.
