# Etapa 10E.4 — Mega Evoluções e formas alternativas temporárias

**Decisão do mestre Ankar (20/11/2026):**

1. Formas alternativas, como **Morpeko Satisfeito/Faminto**, podem ser trocadas pelo próprio dono do Pokémon, **sem permissão do mestre**, desde que as formas correspondentes existam e estejam ativas no catálogo.
2. **Mega Evolução é uma capacidade do TREINADOR:** o mestre concede ou revoga a permissão na seção **Campo → Permissões de Mega Evolução**. Não exigimos Pedra Chave, Mega Pedras nem golpe específico de Rayquaza.
3. A Mega Evolução é temporária, ativada pelo jogador com o Pokémon no Campo. **Máximo de uma Mega ativa por treinador**. Retirar do Campo, encerrar o Campo, desmaiar ou o mestre revogar a permissão encerra a Mega.

**Não alterar** `pokemon.forma_pokemon_id`: preserva-se sempre a espécie/forma permanente, identidade, natureza, Shiny, golpes, Box e treinador.

## Catálogo

`data/referencias/transformacoes_10e4.json` lista explicitamente 48 destinos Mega verificados no catálogo Ankar, além de 46 caminhos alternativos revisados. Charizard X/Y, Rayquaza e as formas de Morpeko são exemplos. O sistema só apresenta destinos com `FormaPokemon` e `EspeciePokemon` ativos e pertencentes **à mesma espécie**, e nunca permite mudança arbitrária para Mega de outra espécie ou variante regional não permitida.

Para alternativas, o serviço percorre as conexões da referência nos dois sentidos e considera também variantes ativas com `categoria='alternativa'` da mesma espécie; o dono pode retornar à forma original. Para espécies com alterações normalmente disparadas por habilidade, clima ou turno, como Morpeko ou Darmanitan Zen, a troca nesta versão é **manual**, pois não existe motor automático de habilidades/turnos/clima no Campo. Os requisitos naturais são informações narrativas, não novos bloqueios sem autorização.

## Banco de dados e migração

Migration **`c42e10040001_transformacoes_e_mega_treinador.py`**, descendente de `b93e21c031a2`:

- `personagens.mega_habilitada BOOLEAN NOT NULL DEFAULT false`.
- `pokemons.forma_temporaria_id` (FK opcional a `formas_pokemon`).
- `pokemons.tipo_transformacao` = `mega`, `alternativa` ou `NULL`.
- Constraint de consistência: tipo e forma temporária devem existir juntos.

**Não** há migration destrutiva nem importação de alterações reais ao catálogo. A tela lê apenas os destinos existentes. Downgrade bloqueia descarte de dados quando houver permissão Mega ou transformação ativa.

Com backup restaurável antes do deploy:

```powershell
flask --app app.py db current
flask --app app.py db upgrade
flask --app app.py db current
```

A nova revisão esperada é `c42e10040001`, verificando que `b93e21c031a2` já foi aplicada. Nunca substituir PostgreSQL por `db.create_all()`.

## Fluxo de uso

**Mestre:** abre **Campo** e encontra a seção **Permissões de Mega Evolução**. Cada treinador apresenta seu estado e os botões **Liberar Mega** ou **Revogar Mega**. A liberação vale para o treinador, não para um único Pokémon. Ao revogar, Megas ativas desse treinador retornam à forma base na mesma transação. Concessão e revogação ficam em `HistoricoAlteracao`.

**Jogador ou tester dono:** pode alternar a forma de um Pokémon na ficha, na seção **Mega Evolução e formas alternativas**. No Campo, pode selecionar uma forma alternativa ou, se habilitado, ativar uma Megaforma do Pokémon colocado na equipe/Campo. O Campo compartilhado exibe o sprite, nome e tipos da **forma temporária atual**, sincronizados por polling, com botão para **Reverter forma**.

A Mega não consome itens e não exige equipá-los. A ação exige perfil real válido, que o Pokémon pertença ao personagem da sessão e esteja no Campo. O serviço trava `Personagem` e `Pokemon`, garantindo **uma Mega simultânea** por treinador. A forma ativa é guardada em overlay, sem atualizar `forma_pokemon_id`; CSRF em todas as rotas POST.

**Atributos/PV:** `calcular_pokemon` lê os atributos da forma temporária quando presente, reutilizando as regras da campanha e o nível compartilhado do treinador. O dano absoluto já sofrido é mantido durante a transformação e o retorno, e um Pokémon com 0 PV continua desmaiado. Essa preservação de dano é uma adaptação operacional de Ankar. A edição manual da identidade limpa o overlay antes do cálculo; a evolução permanente é bloqueada enquanto houver transformação temporária.

## Rotas e código

- `app/services/transformacoes_service.py`: catálogo revisado, permissões, escolha e reversão, recalcular PV e auditoria.
- `app/models/db/character.py`, `app/models/db/pokemon_instance.py`, `app/models/db/pokemon_catalog.py`: novas colunas/relacionamentos explícitos.
- `app/services/campo_service.py`: render do sprite/tipos temporários, controle de permissões e reversão de Megas ao retirar/limpar o Campo.
- `app/routes/combates.py`: POST de Mega por treinador (só mestre) e transformação no Campo (só dono).
- `app/routes/pokemons.py`: POST de forma alternativa na ficha do Pokémon dono; view com Mega permissionada e forma ativa.
- `app/services/pokemon_db_service.py`: atributos da forma ativa; edição de forma permanente ou PV 0 não deixa Mega antiga.
- `app/services/evolucao_efetiva_service.py`: impede evolução permanente com overlay ativo.
- `app/services/fichas_url_service.py`: autoriza POST da própria ficha via `/p/<login>/` sem abrir endpoints mestre.
- `templates/campo/painel.html`, `templates/campo/_times.html`, `templates/jogador/pokemon.html`, CSS/JS: controles responsivos.
- `tests/test_mega_alternativas_10e4.py` e CI `test-megas-formas-alternativas-10e4.yml` com regressões.

## Testes de homologação

1. Após backup e upgrade, mestre libera Mega para um treinador no Campo. Confirmar que outro treinador continua sem permissão; nenhum item foi solicitado.
2. Jogador coloca um Charizard no Campo, escolhe Mega X ou Mega Y. A imagem/tipo/atributos mudam; o UUID do Pokémon e sua forma permanente seguem Charizard. Tentar uma segunda Mega do mesmo treinador: deve ser bloqueada.
3. Retirar Charizard do Campo, limpar o Campo ou revogar a permissão: Mega reverte. PV preservam dano; desmaio permanece em 0.
4. Jogador que tem Morpeko Satisfeito alterna para Faminto na própria ficha ou no Campo e vice-versa, sem liberação do mestre. O campo não automatiza a troca a cada turno.
5. Confirmar que uma conta mestre não pode acionar uma transformação em nome de jogador, e que o jogador não pode alterar permissão Mega ou Pokémon alheio.
6. Testar ficha individual `/p/<login>/`, CSRF, ausência de Mega no Campo, e evolução permanente com transformação ativa.
7. Verificar os registros históricos de concessão, revogação, ativação e reversão.

**Não aplicado pelo assistente:** schema real, permissões de treinadores, itens, formas e alterações no PostgreSQL da campanha. Homologação após merge depende do usuário.

## Próximos incrementos opcionais

Automatizar turnos/clima/habilidades para Morpeko, Darmanitan, Castform etc. somente após desenvolver um motor de combate, mantendo o controle manual como alternativa.
