# Pokémon RPG — Prompt mestre e contexto de continuidade

> **Fonte de verdade de contexto para os próximos chats e colaboradores.**  
> **Versão:** 1.1 — **Data da revisão:** 23/10/2026.  
> **Base examinada:** `PokemonRPG.zip`, ramo Git `feature/att-frontend`, commit `9517d8a` (23/10/2026).  
> **Escopo desta versão:** revisão incremental da validação de cadastro/edição de itens, testes de regressão e documentação. Correção ainda não validada com Flask em execução.

## 1. Missão e instrução para o próximo assistente

Você está continuando, **não recriando**, o site de gerenciamento da campanha Pokémon RPG da região fictícia de **Ankar**. Trabalhe incrementalmente no código existente, preservando dados, permissões, rotas e comportamentos que já funcionam. Use este documento como orientação inicial, porém **confirme os detalhes no código da cópia mais recente**: uma implementação posterior prevalece sobre descrições históricas.

Ao iniciar uma nova conversa:

1. Leia este documento, `docs/DIARIO_DESENVOLVIMENTO.md`, `docs/AGENTS.md` e os documentos de referência relevantes ao módulo trabalhado.
2. Confira a revisão atual do Git (`git status`, `git log -5`) e quais alterações locais ainda não foram commitadas; **não descarte mudanças do usuário**.
3. Identifique qual demanda está ativa e se uma correção anterior foi realmente aplicada. Nunca trate uma etapa planejada como concluída.
4. Antes de mudar esquema de dados, verifique as migrations e o estado real do banco, se houver acesso autorizado. Não execute alterações destrutivas nem importação de dados em produção sem plano de backup.
5. Implemente uma alteração por vez, com verificação correspondente. Registre arquivos alterados, mudanças de comportamento, comandos de teste e seus resultados reais.
6. **Após cada etapa concluída, atualize este documento e o diário**, incluindo a próxima tarefa recomendada, de modo que o contexto sobreviva a quebras de conversa.

> **Limitação operacional:** este documento só será atualizado quando o projeto/arquivo for disponibilizado e a atualização for feita de fato. Não há monitoramento autônomo de mudanças futuras no Git ou no servidor.

## 2. Propósito do sistema e fontes de regras

O site serve como plataforma de apoio a mestre e jogadores na campanha Ankar: fichas de treinador, equipes de Pokémon, Boxes, catálogo, inventário, gestão administrativa e futuras ferramentas de encontro e batalha.

**Fontes fornecidas para o projeto:**

- `pkmrpg-playtest-2_5.pdf` — manual base do Pokémon RPG v2.5 (Vinícius Ottoni).
- `Ficha Editável v2.5.xlsx` e `Utilitários v2.5.xlsx` — fichas e ferramentas do sistema original.
- `Ankar - Cidades e Pontos de Interesse - PokéRPG.xlsx` — locais da campanha.
- `Região de Ankar - Rotas - PokéRPG.xlsx` — rotas da campanha.
- `Mapa.jpg` — mapa da região.

**Hierarquia de decisões:** (1) decisões explícitas atuais da campanha e código validado, (2) documentação técnica atualizada do projeto, (3) manual PKMRPG 2.5, quando não houver adaptação específica. **Não restaurar automaticamente mecânicas do manual que foram retiradas de Ankar.**

### Adaptações obrigatórias da campanha

Confirmadas em `README.md`, `ALTERACOES_CAMPANHA.md` e implementação:

- **Nível compartilhado:** `personagens.nivel` governa os cálculos de todos os Pokémon do treinador, inclusive na Box; não há nível próprio na tabela `pokemons`.
- **Mecânicas retiradas do fluxo atual:** experiência individual de Pokémon, amizade, taxa de captura automática, recurso/consumo dos golpes, contagem de usos dos golpes e ataque de emergência por falta de recurso.
- **Equipe com até 6 Pokémon**; **uma Box por personagem, com 100 espaços**; novos Pokémon são criados por vagas na Box, respeitando as permissões.
- Cálculos atuais consideram estatísticas por nível, atributos base, Shiny, natureza, estilo de combate, alguns estados e bônus manuais.
- Golpes individuais: máximo de 4. Alteração de item carregado deve passar pelo inventário com movimentação de unidades.

**Consequência para os novos módulos:** “captura” é atualmente o nome de uma necessidade visual/narrativa de geração e **atribuição pelo mestre**; **não** presumir que se deva criar uma rolagem de taxa de captura, XP individual ou recursos de PP.

## 3. Stack técnica e execução

Verificado na aplicação e dependências:

- **Backend:** Python 3.10+, Flask 3.x, Flask-SQLAlchemy, SQLAlchemy 2.x, Flask-Migrate/Alembic, psycopg 3, python-dotenv.
- **Banco persistente de referência:** PostgreSQL. JSONs em `data/` existem para importação/legado e alguns backups; não substituem o PostgreSQL para fichas, Pokémon e inventários atuais.
- **Frontend:** templates Jinja2 em `templates/`, CSS em `static/css/`, JavaScript vanilla em `static/js/`.
- **Servidor de testes remotos:** Waitress e scripts PowerShell com Cloudflare Quick Tunnel, conforme `TESTES_REMOTOS_CLOUDFLARE.md`.
- **Testes:** pytest, arquivos sob `tests/`, com fixtures de SQLite para parte dos testes; resultados atuais precisam ser obtidos no ambiente apropriado.
- **Inicialização:** `app.py` chama a fábrica Flask `create_app()` em `app/__init__.py`.
- **Configuração:** variáveis de ambiente em `.env` (arquivo **sensível**, não deve ser compartilhado/publicado). Referência segura: `.env.example`.

Procedimento documentado para ambiente Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
flask --app app.py db current
pytest -q
python app.py
```

Não execute `db upgrade` sem antes validar backup e revisar as migrations pendentes. Os comandos administrativos de diagnóstico incluem:

```powershell
flask --app app.py catalogo verificar
flask --app app.py inventario verificar
flask --app app.py pokemon verificar
flask --app app.py midia verificar
```

## 4. Estrutura atual de diretórios

```text
PokemonRPG/
├── app.py                       # Entrada Flask
├── servidor_teste.py           # Servidor de teste
├── app/
│   ├── __init__.py             # create_app, registro de blueprints e comandos
│   ├── config.py, extensions.py
│   ├── routes/                 # HTTP/controle de acesso/telas
│   │   ├── auth.py
│   │   ├── jogadores.py, mestre.py
│   │   ├── pokemons.py, boxes.py
│   │   ├── inventario.py, catalogo_admin.py
│   │   └── combates.py, utilitarios.py  # Reservados (placeholders)
│   ├── services/               # Negócios, validações, transações
│   │   ├── pokemon_db_service.py
│   │   ├── personagem_service.py, painel_mestre_service.py
│   │   ├── item_admin_service.py, inventario_service.py
│   │   ├── catalogo_admin_service.py, golpe_admin_service.py
│   │   ├── permissoes_service.py, calculo_atributos.py
│   │   ├── gerador_pokemon.py, calculo_combate.py, calculo_captura.py # Reservados
│   │   └── importacao/
│   ├── models/db/              # ORM PostgreSQL
│   ├── commands/               # Comandos Flask de diagnóstico/importação
│   └── seed/
├── migrations/versions/        # Migrations Alembic
├── templates/                  # Páginas mestre e jogador, componentes
├── static/css/, static/js/     # Estilos e scripts
├── static/uploads/             # Uploads locais: preservar/backup separado
├── data/                       # Dados locais, legado e backups
├── tests/                      # Testes automatizados
├── scripts/                    # Importação, utilitários, túnel de testes
└── docs/                       # Estes arquivos de continuidade
```

### Divisão de responsabilidades existente

- **Rota:** requisição, sessão, autorização, resposta/redirect e mensagens.
- **Serviço:** regra de negócio, validações, transações e cálculos.
- **Modelo:** entidade relacional e integridade de dados.
- **Template/JS/CSS:** apresentação e interação.
- **Migrations:** evolução explícita e versionada do esquema.

**Observação:** `app/routes/catalogo_admin.py` concentra vários módulos e é candidato a refatoração futura, mas **não** refatorar apenas para incluir documentação ou uma pequena correção.

## 5. Autenticação, perfis e permissões

Perfis no banco: `administrador`, `mestre`, `tester`, `jogador`; a validação atual consulta o perfil no PostgreSQL para evitar usar apenas controles de tela.

- **Mestre/administrador:** acesso administrativo, fichas de jogadores, catálogos, ajuste de inventário e criação/edição de Pokémon em Boxes dos personagens.
- **Tester:** telas pessoais, criação de Pokémon em espaços vazios da própria Box e edição completa dos próprios Pokémon; não pode criar/conceder itens.
- **Jogador:** consulta e administra seus Pokémon existentes (limitado nos campos de identidade); não pode criar Pokémon nem itens; usa inventário conforme permissões.

Regras detalhadas: `PERFIS_E_PERMISSOES.md`, `PERMISSOES_POKEMON_E_TIPOS.md` e `app/services/permissoes_service.py`.

Não ampliar permissões por meio de um botão no frontend; verificar autorização no servidor, vínculo de campanha e propriedade dos registros.

## 6. Principais entidades relacionais existentes

Verificadas em `app/models/db/`:

| Área | Tabelas principais | Notas |
|---|---|---|
| Identidade | `usuarios`, `campanhas`, `campanha_membros` | Perfil e vínculo de campanha |
| Treinador | `personagens`, `personagem_atributos`, `personagem_insignias` | Contém `personagens.nivel` |
| Pokémon | `especies_pokemon`, `formas_pokemon`, `pokemons`, `pokemon_golpes`, `pokemon_status`, `pokemon_bonus_atributos` | `pokemons.personagem_id` obrigatório; `localizacao` é `equipe` ou `box` |
| Mecânicas | `golpes`, `naturezas`, `natureza_modificadores`, `status_condicoes`, `tipos_pokemon`, `efetividades_tipo`, `forma_pokemon_golpes` | Catálogos e relacionamentos |
| Itens | `categorias_item`, `itens`, `personagem_itens` | `itens.efeitos` JSON versionado; quantidades por personagem |
| Configuração e auditoria | `regras`, `regra_valores`, `historico_alteracoes` | Regras e trilha de modificações |

O registro `pokemons` contém `forma_pokemon_id`, `genero`, `shiny`, `natureza_id`, `pv_atual`, `localizacao`, `posicao`, `item_equipado_id` e campos complementares. A estrutura **não comporta diretamente um Pokémon ainda não atribuído**, pois requer `personagem_id`. A nova tela de geração deve projetar claramente o estado temporário ou persistente dos encontros antes de conceder ao jogador, sem violar essa restrição.

O arquivo de migrations mais recente na cadeia do código inspecionado é `b72cf044e6ad_reconciliar_perfil_tester_postgresql.py`. **Isso não comprova que a base de dados real já foi atualizada até essa revisão.** Algumas documentações antigas citam heads anteriores; consultar sempre `flask --app app.py db current` na instalação correta.

## 7. Funcionalidades implementadas ou estruturadas

**Confirmado em rotas/modelos/documentação; o funcionamento em produção não foi testado nesta revisão:**

- Login/logout e gerenciamento de perfis (`app/routes/auth.py`).
- Ficha e dashboard do treinador (`app/routes/jogadores.py`, `app/routes/mestre.py`).
- Painel do mestre, gestão de jogadores e ajuste separado de nível (`app/routes/mestre.py`).
- Catálogos de espécies/formas, golpes, vínculos de aprendizado e itens (`app/routes/catalogo_admin.py`).
- Pokémon individual e equipe (`app/routes/pokemons.py`).
- Box única por treinador (`app/routes/boxes.py`).
- Inventário, transferências, consumo e equipamento (`app/routes/inventario.py`).
- Autocomplete e pesquisas dinâmicas (`static/js/` e endpoints de catálogo).
- Upload de imagens e controle de arquivos locais (`app/services/upload_service.py`).
- Testes automatizados presentes em `tests/`.

**Reservado/não implementado como funcionalidade ativa:**

- `app/services/gerador_pokemon.py` contém apenas uma indicação de módulo futuro.
- `app/services/calculo_combate.py`, `app/services/calculo_captura.py`, `app/routes/combates.py` e `app/routes/utilitarios.py` contêm placeholders.
- Os blueprints de combate/utilitários **não estão registrados** em `app/__init__.py`, embora existam templates relacionados. Um template isolado não significa uma funcionalidade utilizável.
- Não foi identificado painel multi-equipes ativo de até 16 times, nem a nova geração visual e atribuição de Pokémon para os jogadores.

## 8. Pendências e roteiro do produto

### Etapa A — Verificar a correção anterior e o cadastro de itens

A última conversa mencionou uma **primeira correção** não totalmente identificada pelo histórico disponível. O Git fornecido mostra alterações recentes no inventário (23/10/2026); não considerar que isso resolva necessariamente o problema de cadastro.

1. Reproduzir o defeito real de criação de item, com dados válidos e inválidos.
2. Examinar `templates/mestre/catalogo/item_form.html`, `static/js/itens-admin.js`, `app/routes/catalogo_admin.py` (rota `novo_item`) e `app/services/item_admin_service.py` (`criar_item_admin`).
3. Avaliar formulário, editor de efeitos, categoria, preço, upload, validação, rollback e mensagens de erro.
4. Corrigir de modo cirúrgico; testar criação, edição e persistência.
5. Partir de `tests/test_itens_inventario.py` e testes relacionados, ampliando cobertura quando necessário.

**Situação em 23/10/2026:** **PARCIAL — CORREÇÃO IMPLEMENTADA, TESTE INTEGRADO PENDENTE.** Revisão estática confirmou dois comportamentos defeituosos:

- Preço de item com valor textual ou decimal era silenciosamente transformado em `0` pelo helper de inteiro. `app/services/item_admin_service.py` agora rejeita valores não inteiros e valores acima de `999.999.999` (limite já definido no formulário). Preço em branco permanece `0`.
- No editor de itens, após remover todos os efeitos, caso outro campo fosse inválido, `app/routes/catalogo_admin.py` restaurava os efeitos anteriores na tela via fallback `or efeitos_iniciais`. Agora respeita a lista vazia enviada.

Novos testes de regressão estão em `tests/test_itens_inventario.py`. **Validações realmente executadas:** 7 casos isolados da função de preço, compilação dos arquivos Python alterados e verificação da sintaxe do JavaScript; todos passaram. **Bloqueio:** dependências Flask/Flask-SQLAlchemy ausentes no ambiente desta revisão e instalação online indisponível; testes de integração não executados. Banco PostgreSQL real não acessado.

**Próximo passo:** em ambiente com dependências instaladas, executar `pytest -q tests/test_itens_inventario.py`, reproduzir o fluxo real de criação e edição no navegador (inclusive upload e efeitos), e depois executar `flask --app app.py catalogo verificar` e `flask --app app.py inventario verificar` antes de auditar dados. Não houve migration.

### Etapa B — Auditar catálogo e banco de itens

Após estabilizar o formulário:

- Verificar consistência, duplicatas, categorias, imagens, preços, sinalizadores `consumivel`, `equipavel`, `uso_em_batalha` e formato de `efeitos`.
- Validar relacionamentos `personagem_itens` e `pokemons.item_equipado_id`.
- Confrontar categorias e itens com o capítulo 16 do manual e as adaptações Ankar, sem sobrescrever customizações.
- Executar diagnósticos do catálogo/inventário antes de aplicar qualquer correção em massa; proteger dados reais com backup e alterações reversíveis.

**Situação:** revisão prevista; dados reais do PostgreSQL não foram auditados.

### Etapa C — Geração visual de Pokémon / atribuição pelo mestre

**Objetivo:** permitir que o mestre gere Pokémon para exibição em uma tela compartilhada e os atribua a jogadores.

**Requisitos confirmados pela conversa:**

- Natureza e sexo devem ser gerados aleatoriamente quando aplicáveis.
- Os Pokémon gerados ficam visualmente disponíveis aos jogadores.
- O mestre decide a qual jogador atribuir cada Pokémon.
- Após atribuição, a instância deve aparecer no conjunto correto do jogador e ser persistida.

**Decisões de projeto a validar antes de codificar:**

- Definir se o encontro gerado vive somente na sessão ou necessita de tabela própria (`encontros_pokemon` ou equivalente); não inserir Pokémon sem dono na tabela atual, que exige `personagem_id`.
- Definir como selecionar espécie/forma e quais campos de configuração específica de sexo estão disponíveis no catálogo. Não presumir que o banco já guarda proporções por espécie.
- Reutilizar `app/services/pokemon_db_service.py` e respeitar Box única com 100 vagas; impedir duplicidade de atribuição.
- Diferenciar visualização pública de ações exclusivas do mestre.
- A geração deve seguir as adaptações atuais da campanha (sem XP/amizado/PP automáticos e sem cálculo automático de chance de captura).
- Se forem desejados vários encontros simultâneos, definir identificadores, validade e remoção.

**Situação:** planejado; implementação principal ainda ausente.

### Etapa D — Campo de batalha compartilhado

**Objetivo:** cada jogador posicionar Pokémon em uma página compartilhada, com **até 16 equipes** independentes.

**Requisitos confirmados:**

- Jogadores colocam Pokémon em campo e todos os participantes visualizam.
- Times distintos permitem PvP; um mesmo time pode reunir Pokémon de jogadores diferentes para cooperação contra outros adversários.
- Suportar vários participantes e equipes sem impor combate apenas 1x1.

**Decisões a validar:**

- Entidade para sessão/arena, membros e posições; independência entre estado da batalha e localização `equipe`/`box` do Pokémon.
- Autorizações de inclusão, movimentação, troca, remoção e encerramento, incluindo controle do mestre.
- Atualização compartilhada por polling ou tecnologia em tempo real ainda a escolher segundo infraestrutura existente; **não presumir Socket.IO já instalado**.
- Definir quais atributos são exibidos sem reintroduzir mecânicas desativadas.
- Combate automático, iniciativa, ataques, dano e efeitos são uma fase **separada** se não forem solicitados.

**Situação:** planejado; placeholders de combate disponíveis, sem implementação funcional.

## 9. Regra de atualização da documentação (obrigatória)

Sempre que uma etapa do projeto terminar, atualizar **no mesmo conjunto de alterações**:

1. `docs/CONTINUIDADE_PROJETO.md`: versão/data, estado da arquitetura, módulos alterados, novas decisões e roteiro/próxima tarefa.
2. `docs/DIARIO_DESENVOLVIMENTO.md`: adicionar entrada cronológica com motivo, arquivos alterados, migrations, comandos de teste **realmente executados**, falhas conhecidas e próximo passo.
3. `docs/AGENTS.md`: atualizar apenas se mudar a convenção principal de leitura/execução do projeto.
4. Manter as instruções de README e docs especializadas coerentes quando seus comportamentos mudarem.

**Formato de status:** `CONFIRMADO NO CÓDIGO`, `DOCUMENTADO (NÃO TESTADO)`, `PLANEJADO`, `BLOQUEADO` ou `CONCLUÍDO E TESTADO`. Não tratar um teste existente no repositório como prova de que passou nesta execução.

**Segurança:** nunca incluir `.env`, senhas, tokens, backups privados, registros identificáveis de jogadores ou dumps completos do banco em pacotes de documentação. Preservar `static/uploads/` e dados PostgreSQL separadamente. Nunca aplicar alterações destrutivas sem autorização e backup.

## 10. Restrições e incertezas desta leitura inicial

- Somente o código empacotado foi inspecionado; o PostgreSQL de execução não foi acessado.
- Não foram executadas as rotas no navegador real.
- `pytest --collect-only` foi tentado, mas falhou por ausência do módulo Flask neste ambiente; **não é um defeito confirmado do projeto**.
- O ramo Git do ZIP trazia uma alteração local não commitada sob `data/campanhas/ankar/jogadores/`; ela deve ser preservada.
- O projeto possui documentos antigos que citam revisões intermediárias e números históricos de testes; usar o estado mais recente do código, não uma contagem histórica, para novas verificações.

## 11. Texto curto para iniciar o próximo chat

> Quero continuar o desenvolvimento do meu site **Pokémon RPG — Ankar**, sem recomeçar. O ZIP do projeto contém `docs/AGENTS.md`, `docs/CONTINUIDADE_PROJETO.md` e `docs/DIARIO_DESENVOLVIMENTO.md`: leia esses arquivos e confronte-os com o código atual antes de qualquer mudança. A aplicação usa Flask + PostgreSQL, com nível compartilhado e algumas mecânicas oficiais desativadas. Preserve meus dados, minhas permissões e a arquitetura existente. Informe a etapa ativa e os arquivos envolvidos, implemente a tarefa solicitada com testes e **atualize os documentos de continuidade** ao final, registrando exatamente o que foi modificado e o que segue pendente.

---

**Documentos técnicos existentes úteis:** `README.md`, `ORGANIZACAO_PROJETO.md`, `ALTERACOES_CAMPANHA.md`, `BANCO_DE_DADOS.md`, `PERFIS_E_PERMISSOES.md`, `PERMISSOES_POKEMON_E_TIPOS.md`, `ITENS_INVENTARIO.md`, `CATALOGO_ADMIN.md`, `PAINEL_MESTRE.md`, `ALINHAMENTO_INVENTARIO_UI2.md`.
