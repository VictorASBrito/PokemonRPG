# Pokémon RPG — Prompt mestre e contexto de continuidade

> **Fonte de verdade de contexto para os próximos chats e colaboradores.**  
> **Versão:** 1.2 — **Data da revisão:** 23/10/2026.  
> **Base examinada:** `PokemonRPG.zip`, ramo Git `feature/att-frontend`, commit `9517d8a` (23/10/2026).  
> **Escopo desta versão:** validação da correção anterior confirmada pelo usuário (9 testes passaram em 10,86 s); implantação de auditoria detalhada de catálogo **somente leitura**, com novos testes e documentação. A leitura do PostgreSQL real ainda depende da execução local.

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

### Resultado registrado da correção anterior — 23/10/2026

O usuário relatou **`9 passed in 10.86s`** após executar os testes recomendados para a revisão do cadastro de itens. Esse resultado veio da instalação do usuário; **não foi reexecutado neste ambiente de análise**. A execução manual no navegador e o catálogo PostgreSQL da campanha permanecem por conferir.

### Etapa B — Auditar catálogo e banco de itens

Após estabilizar o formulário:

- Verificar consistência, duplicatas, categorias, imagens, preços, sinalizadores `consumivel`, `equipavel`, `uso_em_batalha` e formato de `efeitos`.
- Validar relacionamentos `personagem_itens` e `pokemons.item_equipado_id`.
- Confrontar categorias e itens com o capítulo 16 do manual e as adaptações Ankar, sem sobrescrever customizações.
- Executar diagnósticos do catálogo/inventário antes de aplicar qualquer correção em massa; proteger dados reais com backup e alterações reversíveis.

**Situação (23/10/2026):** nova ferramenta de diagnóstico implementada no código, sem escrita no banco. A auditoria real dos registros continua **pendente** até que o usuário execute o comando no seu PostgreSQL e compartilhe o resultado.

**Novo comando:** `flask --app app.py catalogo auditar-itens` (usar `--todos` para listar todos os achados). Verifica estrutura/versionamento dos efeitos, referências internas, categorias, códigos equivalentes, preços e suspeitas de duplicatas. **Erros** produzem saída diferente de zero; **avisos** não bloqueiam o processo e exigem análise humana. Não faz update, delete, importação ou migration. Para a parte de inventário/equipamentos, executar também `flask --app app.py inventario verificar`.

**Arquivos desta entrega:** `app/services/auditoria_itens_service.py`, `app/commands/catalogo.py`, `tests/test_auditoria_itens.py`, documentação em `docs/`.

**Testes nesta revisão:** oito verificações isoladas da lógica de auditoria passaram; compilação Python passou. Testes integrados dependentes de Flask não executados neste ambiente (as dependências não estão disponíveis). Os seis novos cenários de pytest devem ser validados pelo usuário.

**Não inferir cobertura do manual:** o diagnóstico é de integridade de dados e estrutura, não certifica que todos os itens da edição 2.5 estão no catálogo nem que seus efeitos/preços correspondem ao livro. Comparação semântica exige os dados reais e critérios próprios de Ankar.

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

## 12. Andamento — 23/10/2026: importação de naturezas como equipamento

**Confirmado nos dados de origem:** a última saída da auditoria, enviada pelo mestre, apontou inúmeros avisos de itens `importado-ficha-*` sem categoria; `inventario verificar` confirmou 110 registros, 456 unidades e 48 itens equipados consistentes em termos referenciais. A análise do JSON das nove fichas identificou **49 referências preenchidas de `item` que são literalmente iguais à `natureza` do próprio Pokémon** (21 naturezas distintas). Essa é uma falha na preparação/importação de dados legados, não uma categoria que deva ser criada.

**Alterações disponíveis em pacote incremental:** o importador agora ignora `item == natureza` com aviso, e o comando `flask --app app.py catalogo revisar-naturezas-importadas` faz simulação de vínculos suspeitos exclusivamente na campanha Ankar. Somente `--aplicar` remove as referências elegíveis e registra histórico, sem alterar unidades de inventário e sem apagar itens do catálogo. Consulte `docs/ITENS_INVENTARIO.md` para os critérios restritivos de segurança e as instruções.

**Situação:** código preparado; 3 testes unitários puros passaram; testes integrados e execução em PostgreSQL pelo mestre PENDENTES. O número de 49 é do seed original e **não** deve ser confundido com os 48 vínculos atualmente relatados no banco. Não sugerir limpeza em massa, deleção de natureza ou categorização automática desses pseudoitens. Itens genuínos sem categoria continuarão exigindo revisão manual. Nenhuma migration nesta etapa.

**Próximo passo recomendado:** mestre executar `python -m pytest -q tests/test_reparo_natureza_importada.py tests/test_auditoria_itens.py` e `flask --app app.py catalogo revisar-naturezas-importadas` (SEM `--aplicar`) e enviar resultados. Só após confirmar os candidatos deve decidir pela aplicação. Em seguida, auditoria e classificação conservadora dos itens realmente válidos, antes do módulo de geração de Pokémon.


## Atualização — Capturáveis em campo

- Implementada a primeira versão do módulo de capturáveis em campo.
- O mestre pode registrar até 15 Pokémon capturáveis por campanha.
- Cada registro guarda a forma do Pokémon e qual personagem o encontrou.
- A tela do jogador exibe nome, sprite e tipos dos Pokémon disponíveis.
- A tela do mestre permite adicionar e remover capturáveis, preparando a futura etapa de atribuição/captura.

### Etapa 05.1 — Correção de auditoria dos capturáveis (23/10/2026)

O módulo de até 15 capturáveis foi adicionado na Etapa 05, usando a tabela `pokemons_capturaveis` (migration `6f355a4d5b2e`). O usuário executou `tests/test_capturaveis_campo.py`, obtendo `2 failed, 1 passed` devido à tentativa de criar `HistoricoAlteracao` com campos inexistentes `entidade_id`/`detalhes`. A correção alinha o serviço ao modelo vigente (`registro_id`, `dados_anteriores`, `dados_novos`) na criação e remoção de capturáveis e adiciona verificações de regressão do histórico. **Sem nova migration.** Sintaxe Python verificada neste ambiente; integração Flask pendente de reexecução na máquina do usuário.

**Próxima ação:** reexecutar `python -m pytest -q tests/test_capturaveis_campo.py`, confirmar funcionamento do campo do mestre/jogador; a atribuição definitiva à Box é etapa futura.


### Atualização 05.2 — Correção de seleção de espécie no campo

O autocomplete de formas tem dois valores distintos: `valor` (nome exibido, compatibilidade com formulários existentes) e `id` (UUID da forma, usado no campo oculto `forma_id` ao adicionar capturáveis). A UI compartilhada deve preencher o ID para `tipo === 'pokemon'` quando houver campo oculto; itens continuam usando `valor`. O serviço de criação mantém compatibilidade limitada com envios antigos em que `forma_id` e `forma_nome` continham o mesmo nome válido. Sem nova migration. A correção 05.1 do histórico continua necessária.

**Estado dos testes:** usuário relatou aprovação dos testes 05.1. Novos testes 05.2 aguardam execução no ambiente local. Próximos passos: confirmar adição real pela tela, revisar apresentação e evoluir para atribuição à Box.

### Atualização 05.3 — Remoção segura e renumeração (23/10/2026)

Com vários capturáveis, a remoção falhava por conflito da restrição UNIQUE `(campanha_id, ordem)` do PostgreSQL. A etapa 05.3 introduz renumeração em duas fases, ambas na mesma transação: liberar as posições sobreviventes com `NULL` e `flush`, depois definir `1..N` e `flush`. As mutações agora bloqueiam a campanha no PostgreSQL para reduzir conflitos concorrentes entre adicionar/remover. A remoção mantém inativo o registro retirado, o histórico e os dados do Pokémon. Nenhuma migration nova.

**Status:** pacote corretivo pronto; validação integrada e teste manual no PostgreSQL do usuário pendentes. **Verificar:** `python -m pytest -q tests/test_capturaveis_campo.py`, depois remover um capturável do meio da lista e conferir as posições.

### Validação confirmada pelo mestre — Etapa 05.3 (23/10/2026)

**Status: FUNCIONALIDADE DE EXIBIÇÃO/GERENCIAMENTO DE CAPTURÁVEIS VALIDADA NA INSTALAÇÃO DO USUÁRIO.** Após instalar a correção 05.3, o mestre confirmou: “Ótimo, está funcionando corretamente agora”. A confirmação sucede erros reais de seleção de espécie (corrigidos em 05.2), persistência de histórico (05.1) e remoção/reordenação sob restrição UNIQUE (05.3). Os capturáveis já apareciam em campo antes da correção 05.3. Não afirmar quantidade de testes da 05.3 sem receber nova saída do pytest, nem interpretar a confirmação como validação da atribuição à Box, que ainda não foi implementada.

**Próximo desenvolvimento:** atribuição pelo mestre de um capturável à Box de um jogador, preservando forma, natureza e gênero gerados, com garantia de não duplicidade, verificação de capacidade da Box, permissões e histórico. Usar ZIP atualizado para preservar quaisquer alterações locais. A experiência de tentativa de captura é uma fase distinta a definir.


## Etapa 06 — Atribuição de capturáveis à Box (23/10/2026)

**Status: IMPLEMENTADO NO CÓDIGO; TESTES INTEGRADOS PENDENTES NA MÁQUINA DO USUÁRIO.** Base: ZIP enviado após confirmação do funcionamento da Etapa 05.3.

- O mestre escolhe um capturável e um personagem destinatário ativo da campanha e aciona **Atribuir à Box**.
- O servidor usa autenticação e autorização já existentes (`perfil_obrigatorio("mestre")`), mais token de formulário dedicado. Jogadores apenas visualizam o campo.
- O serviço `atribuir_capturavel_box` em `app/services/capturaveis_service.py` bloqueia a campanha para serializar mutações, valida conta ativa de jogador/tester e capacidade da Box, cria um Pokémon na próxima posição e preserva forma/espécie, natureza, sexo e Shiny sem sortear novamente. PV segue o nível compartilhado e as regras do destinatário.
- A retirada do encontro é atômica com a criação na Box: faz a renumeração em duas fases sem conflito UNIQUE e grava históricos `pokemon` e `pokemon_capturavel` vinculados por IDs. Reenvio não duplica.
- Arquivos alterados: `app/services/capturaveis_service.py`, `app/routes/capturas.py`, `templates/capturas/mestre.html`, `static/css/capturaveis.css`, `tests/test_capturaveis_atribuicao.py` (novo), `docs/CAPTURAVEIS.md` (novo), e estes documentos de continuidade.
- **Nenhuma migration nova**; depende da tabela criada na Etapa 05.
- Verificações locais: compilação Python e análise de sintaxe Jinja; testes Flask integrados ainda não executados por ausência das dependências Flask/Flask-SQLAlchemy neste ambiente. Executar `python -m pytest -q tests/test_capturaveis_campo.py tests/test_capturaveis_atribuicao.py` na instalação do mestre.
- Atenção: `docs/CAPTURAVEIS.md` é a referência funcional atual; descrições históricas anteriores que chamam a atribuição de "planejada" refletem versões antigas.
- Próxima fase: testar transferência no PostgreSQL e confirmar na Box; depois decidir sobre tentativa de captura e/ou o painel de batalha de até 16 times.

## Etapa 07 — Painel compartilhado de batalha (23/10/2026)

Implementada a primeira versão do **campo compartilhado com até 16 times**. Jogadores colocam ou movem Pokémon da própria equipe; mestre administra todos, pode retirar Pokémon ou limpar a formação. Os times são compartilhados entre navegadores e atualizados por polling a cada 6 segundos. Cada Pokémon ocupa um único time; os registros são persistidos em `pokemons_em_campo`, com auditoria e validação de permissões no servidor. Enviar Pokémon à Box ou excluí-lo da ficha remove sua participação no campo. Arquivos de implementação, instalação, testes e limites: `docs/CAMPO_COMPARTILHADO.md`.

**Decisão expressa do usuário:** não implementar mecânica automática de tentativa de captura. A tentativa é narrativa entre os jogadores, e a atribuição efetiva é administrada pelo mestre.

**Validação:** sintaxe e integridade dos arquivos verificadas; testes integrados a executar no ambiente local. Nova migration `7a1f20d9c405` deve ser aplicada após backup. Próxima etapa opcional: evolução da interface de combate (HP, ações/turnos) e suporte a oponentes NPC independentes, conforme prioridade do usuário.

## Etapa 08 — Shiny automático e UX de capturáveis (2026-10-25)

- A geração de capturável agora consulta `numeros_shiny` do **personagem que encontrou** o Pokémon, realiza um **1d100 por encontro** e registra `shiny` se o resultado estiver nos números do treinador. Os números são valores **1–100**, não IDs ou números de espécies. Não reprocessar encontros antigos; Shiny é persistido e preservado ao atribuir à Box. O mestre consegue auditar o sorteio no histórico.
- O mestre tem métricas, prévia de espécie, filtros por nome/treinador/Shiny e cards mais legíveis. O jogador tem carrossel com foco nos próprios encontros, seleção de outro treinador ou de todos, miniaturas e setas. Fonte dos dados: mesmo PostgreSQL e endpoints de capturáveis existentes.
- Arquivos: `app/services/capturaveis_service.py`, `app/routes/capturas.py`, `templates/capturas/`, `static/css/capturaveis.css`, `static/js/capturaveis.js`, `tests/test_capturaveis_shiny_carrossel.py`, `tests/test_capturaveis_ui.js`.
- **Sem migration.** Regressões Python dependem da execução na máquina com Flask; o teste JS com Node.js passou (2/2). Tentativa de captura permanece narrativa, sem automação de rolagens de captura.


## Etapa 09 — Qualidade de imagens Pokémon

- Adicionado `static/css/pokemon-hd.css`, carregado por último no tema: interpola imagens de Pokémon suavemente, incluindo carrossel, Campo, Equipe, Box e painel do mestre; não altera artes dos itens.
- Novo comando administrativo `flask --app app.py midia pokemon-hd`: simulação padrão ou download HD de Pokémon HOME (512 px) em lotes, opcional, com atualização das URLs de imagem normal/Shiny quando disponíveis.
- Imagens personalizadas/locais são preservadas; fontes sem correspondência também. Arquivos baixados em `static/img/pokemon-hd/`. Não há migrations.
- Documentação completa em `docs/IMAGENS_POKEMON_HD.md`.
- Limitação atual: ambiente do assistente sem acesso à internet externa para os downloads; comando deve ser executado na instalação local após validação.

## Etapa 09.1 — Diagnóstico e retentativa de imagens HD (25/10/2026)

- O mestre executou a sincronização 09 em sua máquina: **953 formas atualizadas, 110 ignoradas/falhas** entre 1.063 processadas. Detalhes em `docs/FALHAS_SINCRONIZACAO_HD_09_1.md`.
- Da lista textual visível: 88 falhas 404, 1 timeout (Beautifly), 1 limite de resposta (Mew). As 20 entradas anteriores ao início da lista, em Armaldo, foram inferidas como 18 Arceus e 2 Aegislash, com confirmação pendente via PostgreSQL.
- Aprimorado `app/services/imagens_pokemon_hd.py`: aliases seguros para formas, endpoint `pokemon-form`, arte oficial como reserva, retry de rede e JSON até 5 MB.
- Aprimorado `app/commands/midia.py`: atualiza normal/Shiny de maneira independente, comando `pokemon-hd-pendentes`, relatório `relatorio-ultima-sincronizacao.json` e preservação das URLs originais enquanto não há substituto HD válido.
- Testes de regressão adicionados em `tests/test_imagens_pokemon_hd.py` para as falhas reportadas. Nenhuma migration. Testes Flask integrados pendentes de execução pelo mestre.
- A sincronização ocorre **apenas mediante execução manual com `--aplicar`**; não afirmar que as 110 imagens foram corrigidas até receber o novo resultado do comando.


### Etapa 09.2 — Recuperação de oito artes finais (25/10/2026)
O mestre informou oito pendências após a rotina 09.1: `eevee-parceiro` (Shiny), `frillish` (ambas), `jellicent` (ambas), `minior-nucleo` (ambas), `pikachu-parceiro` (Shiny), `pyroar` (ambas), `zacian-heroi` (ambas), `zamazenta-heroi` (ambas). O sincronizador passou a testar fontes WebP 512px além de PNGs, inclui IDs exatos de cinco espécies problemáticas e oferece `--representativas` para opções explicitamente aproximadas de parceiro/núcleo Minior. Nenhuma migration foi criada; nenhuma alteração é aplicada sem `--aplicar`; resultado de integração PostgreSQL/download pendente de validação do usuário. Ver `docs/IMAGENS_POKEMON_HD.md`.


### Etapa 09.3 — Visibilidade de todos os capturáveis no carrossel (26/10/2026)
- Ajustada a inicialização de `/jogador/capturaveis`: o filtro padrão agora é **Todos os Pokémon**; quando há encontro próprio, ele é apenas o slide inicial selecionado, sem esconder Pokémon de outros jogadores.
- Setas, miniaturas e opção de seleção direta abrangem todos desde a entrada. O filtro **Meus encontrados** continua disponível.
- Arquivos: `templates/capturas/jogador.html`, `static/js/capturaveis.js`, `tests/test_capturaveis_ui.js`, `tests/test_capturaveis_shiny_carrossel.py`. Querystring do JS alterada para evitar cache da versão antiga.
- Correção de interface, sem migration, sem impacto em imagens HD, capturas, Shiny ou Boxes. A validação real pelo mestre permanece pendente.


---

<!-- ANKAR-10A-1-1-2026-10-27 -->
## Versão 10 — Etapa 10A.1.1: auditor das planilhas de Ankar (27/10/2026)

- **Base de código conferida:** commit `871cfaefbb1b6c59a0b001d1f9fa172d38cb1529` (27/10/2026), `main` idêntica a `feature/att-frontend` nessa revisão. Preparada uma entrega incremental para instalação local; nenhuma alteração foi feita no GitHub.
- **Escopo entregue:** serviço `app/services/auditoria_ankar_service.py` e comando `flask --app app.py ankar auditar-planilhas --rotas ... --cidades ...` (texto ou JSON) em leitura exclusiva; separação de local, zona, terreno e entradas, sem deduzir significado dos dados ambíguos. Registrado em `docs/AUDITORIA_PLANILHAS_ANKAR.md`.
- **Planilhas reais analisadas somente leitura:** 73 rotas e 47 abas de cidades/pontos (120 no total); 352 tabelas e 2.683 entradas observadas, com 313 erros e 626 avisos de auditoria no estado atual. Relatório detalhado em `docs/RELATORIO_AUDITORIA_ANKAR_2026-10-27.txt`. Essas contagens não são conteúdo importado/validado.
- **Ocorrências importantes:** sobreposição Pyukumuku 56–60 / Skrelp 60–75 na Rota 1 Água; datas Excel indevidamente interpretadas; tabelas incompletas, intervalos inválidos, `x` e marcadores `Random`. Não converter datas ou `x` automaticamente.
- **Compatibilidade:** registrados novos comandos por Blueprint, `openpyxl>=3.1,<4.0` em `requirements.txt`; nenhum modelo ORM, migration, PostgreSQL, captura, combate ou regras Shiny alterado.
- **Testes neste ambiente:** 10 testes unitários passaram; 1 teste de CLI ficou ignorado por ausência de Flask, Flask-SQLAlchemy e Flask-Migrate no ambiente de trabalho. **Não afirmar integração Flask/PostgreSQL validada** até execução local.
- **Ação seguinte:** instalar, executar `python -m pytest -q tests/test_auditoria_ankar.py`, executar o comando sobre as planilhas reais, revisar erros e relatar resultados. Somente depois planejar aprovação/importação validada da geografia (10A.1.2). Etapas de NPCs, Campo e eventos continuam não implementadas nesta Versão 10.


<!-- ATLAS_ANKAR_V10A2 -->
### Etapa 10A.2 — Atlas visual de Ankar (28/10/2026)
- Entregue catálogo visual **somente leitura** com 119 locais: 73 rotas, 26 cidades e 20 pontos de interesse (352 tabelas, 2.683 entradas).
- Rotas em `/regiao/ankar`; detalhes em `/regiao/ankar/<slug>`; acesso restrito ao mestre para evitar spoilers aos jogadores.
- Fonte estática: `app/data/catalogo_ankar_visual.json`, gerada das duas planilhas originais pelo script `scripts/gerar_catalogo_ankar.py`; fontes não são necessárias em produção para a consulta.
- Habitats principal/secundário, terrenos, acessos, deslocamento/tamanho, descrições, zonas e encontros por terreno são exibidos. `% Captura` não é peso de encontro.
- Datas que o Excel gerou automaticamente a partir de d100 são apresentadas como faixas (dia-mês) mantendo o valor original no JSON. Marcadores `x`, sobreposições e dados incompletos não são alterados.
- Novos módulos: `app/routes/regiao.py`, `app/services/regiao_ankar_service.py`, `templates/regiao/`, `static/css/atlas-ankar.css`, `static/js/atlas-ankar.js`.
- Registro do blueprint e links da navegação inseridos por `scripts/instalar_atlas_ankar.py`, que preserva conteúdo local e é idempotente.
- Nenhuma migration, escrita no PostgreSQL, rolagem de encontros ou atribuição de capturáveis. Validar testes Flask com dependências instaladas e conferir UI local.
- Próxima etapa: revisão visual/conteúdo e só depois discussão do fluxo de encontros, permissões e dados persistidos.


<!-- ATLAS_ANKAR_V10A2_1_UTF8 -->
### Etapa 10A.2.1 — Correção dos testes no Windows (28/10/2026)
- Corrigido `tests/test_atlas_ankar.py`: todas as leituras de arquivos no teste de idempotência agora especificam `encoding='utf-8'`. A codificação padrão `cp1252` do Windows gerava `UnicodeDecodeError` ao ler o diário.
- O instalador, o Atlas visual, os JSON, a navegação, os acessos e as planilhas não sofreram mudanças nesta correção.
- Relato do usuário antes do patch: 9 testes passaram e 1 falhou; aguardar reexecução dos 10 testes no Windows para confirmar a correção no ambiente real.
- **Sem migrations ou escrita no PostgreSQL.**

<!-- ANKAR_10A3_REVISAO_VISUAL -->
### Etapa 10A.3 — Mapa interativo e revisão visual (28/10/2026)
- Integração **somente leitura** do `Mapa.jpg` original em `/regiao/ankar`: 119 marcadores manuais, 73 rotas, 26 cidades e 20 POIs vinculados aos slugs existentes.
- Filtros de pontos, zoom, toque, identificação e links de detalhe; acesso exclusivo do mestre, como na etapa 10A.2.
- CSS do Atlas harmonizado com as variáveis do design system; estilos globais e telas de jogador permanecem inalterados.
- Mapa em `static/img/ankar-mapa.jpg` e posições em `app/data/mapa_ankar_pontos.json`. Não representa caminhos calculados.
- Seis testes de mapa e verificações Chromium isoladas em 390/820/1440 px passaram. Validação integrada do Flask e do site real pendente no ambiente do mestre.
- Sem migration, acesso a PostgreSQL, alteração de planilha ou de contas.
- Detalhes: `docs/REVISAO_VISUAL_ANKAR_10A3.md`.

<!-- ATLAS_ANKAR_V10A4 -->
### 2026-10-28 — Etapa 10A.4: Atlas compacto e geração de capturáveis
- Mapa inteiro visível à esquerda com filtros e seleção à direita no desktop; responsivo em mobile/tablet, sem alteração nas demais páginas.
- Descrição narrativa abreviada na ficha, com conteúdo integral expansível em parágrafos; habitats, acessos e d100 preservados.
- Tabelas de Pokémon em cards com artes do catálogo. `x` indica sem encontro e não gera Pokémon.
- Com autorização de mestre e confirmação, o card escolhe treinador e delega ao serviço `criar_capturavel_campo` atual (natureza, sexo, Shiny, limite 15, histórico).
- Criada rota POST do atlas com CSRF e validação da entrada original, sem mutation de planilhas.
- Sem migration. Testes Python/Flask e revisão final no navegador do usuário pendentes de execução local.
- Próximo passo: validar navegação e geração real de um encontro; depois analisar espécies sem correspondência entre planilha e catálogo.



<!-- ATLAS_ANKAR_V10A4_1 -->
### Etapa 10A.4.1 — Compatibilidade da ficha do Atlas (28/10/2026)
- **Problema:** o teste `test_template_detalhe_aponta_para_mapa_sem_alterar_encontros` da Etapa 10A.3 renderizava `templates/regiao/detalhe.html` diretamente e não passava `formas`. A atualização 10A.4 introduziu `formas.get(...)` e causava `jinja2.exceptions.UndefinedError`, mesmo com o endpoint real fornecendo o contexto.
- **Correção:** valores padrão seguros para as variáveis opcionais `formas`, `encontrados_por`, `descricao_paragrafos` e `atlas_csrf`, apenas quando omitidas ou nulas. A página real permanece inalterada quando a rota fornece esses valores.
- **Arquivos:** `templates/regiao/detalhe.html`, `tests/test_atlas_10a4_1_template.py`, script e documentação desta correção.
- **Escopo:** sem migrations, alteração no PostgreSQL, mudanças nos encontros, imagens, regras de acesso ou planilhas.
- **Validação local do pacote:** testes unitários Jinja sem Flask; reexecutar a suíte Flask completa na máquina da campanha.
- **Próxima ação:** verificar a geração Atlas → Capturáveis com o mestre no ambiente PostgreSQL e revisar a usabilidade da interface.
