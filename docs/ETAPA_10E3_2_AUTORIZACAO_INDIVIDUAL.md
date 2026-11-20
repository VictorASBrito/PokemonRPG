# Etapa 10E.3.2 — Liberação individual de evolução pelo mestre

**Escopo:** autorizar e revogar relações evolutivas especiais para um
Pokémon específico de um personagem da campanha Ankar.

**Dependência:** a 10E.3.1 já está na `main`; as relações nacionais e
regionais estão no PostgreSQL do mestre. **Migration nova obrigatória**,
sem importação de relações nem evolução efetiva de Pokémon.

## Como funciona

O mestre abre a ficha do Pokémon de um jogador e, nas opções
evolutivas especiais, registra uma **justificativa narrativa de 5 a 500
caracteres**. Após confirmar, o ramo aparece como
**Liberada pelo mestre**, somente na instância selecionada.

O mestre pode revogar a concessão no mesmo painel com um motivo. A
opção volta a **Depende do mestre**. Se houver outra concessão ou outro
Pokémon da mesma espécie, essas permissões permanecem independentes.

**Exemplo:** Eevee Lua recebe autorização para Umbreon, mas Eevee Sol
não recebe, nem Espeon de Eevee Lua. O status `aprovado_mestre` na
linha do catálogo **não** é permissão individual.

**Importante:** essa liberação **não transforma a forma do Pokémon**,
não atualiza PV/atributos/golpes, não consome pedra nem executa
troca. O botão Evoluir será implantado posteriormente, com confirmação
do treinador e consumo transacional de itens.

## Banco de dados

Migration `b93e21c031a2_autorizacao_evolucao_individual.py`,
revisão filha de `a14d4e4044a1`.

Nova tabela `autorizacoes_evolucao_pokemon`:
- `pokemon_id` (Pokémon real, FK), `relacao_id` (ramo cadastrado,
  FK) e `forma_origem_id` (fotografia da forma autorizada).
- `autorizado_por_id`, `autorizado_em`, `justificativa`.
- `ativo`, `revogado_em`, `revogado_por_id` e
  `motivo_revogacao`.
- Restrição única para o par (`pokemon_id`, `relacao_id`):
  nunca criar dois registros de autorização para o mesmo Pokémon e
  caminho, mesmo após revogações. Novas concessões reativam o mesmo
  registro, com nova auditoria.

Toda concessão, revogação e invalidação por mudança manual de forma
gera `HistoricoAlteracao` com o autor e o estado anterior/novo.

### Aplicação controlada

Antes do deploy, gerar/verificar backup PostgreSQL restaurável.
Na instalação atualizada executar:

```powershell
flask --app app.py db current
flask --app app.py db upgrade
flask --app app.py db current
```

A versão esperada após upgrade é `b93e21c031a2`. Revisar a revisão
anterior `a14d4e4044a1` para evitar alterar schema inesperado.
O downgrade bloqueia automaticamente a remoção da nova tabela se
existirem autorizações gravadas.

**Nunca** executar `db.create_all()` para substituir migrations no
PostgreSQL da campanha. O CI usa SQLite para a suíte de integração.

## Autorização e proteção

- A rota `/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>`
  exibe os formulários apenas para o mestre; POSTs são separados:
  `.../evolucoes/<relacao_id>/autorizar` e `.../revogar`.
- `perfil_obrigatorio("mestre")` revalida o perfil real no banco.
  O serviço confirma `Usuario.ativo` e `perfil`, exige
  `CampanhaMembro.papel="mestre"` na campanha (administrador global
  tem acesso privilegiado), confere o personagem e o Pokémon ativo
  na campanha corrente.
- Token CSRF obrigatório, via formulário de sessão. Não existe rota
  de liberação nas fichas dos jogadores.
- O serviço segura a linha do Pokémon via `SELECT FOR UPDATE`,
  valida vínculo evolutivo permanente, ativo, origem exata e destino
  ativo. Só caminhos com requisito especial exigem concessão e
  podem ser liberados por esse procedimento.
- Mudança manual de espécie/forma na edição da ficha desativa todas as
  concessões anteriores na **mesma transação**, com histórico. Mesmo
  que volte à forma antiga, a autorização não reaparece.
- Revogação mantém histórico. Retries de conceder/revogar no mesmo
  estado são idempotentes, sem gerar auditoria duplicada.
- A consulta 10E.3.1 marca `liberada_mestre` **somente** se o
  `pokemon_id`, `relacao_id` e `forma_origem_id` corresponderem
  ao Pokémon atual, com `ativo=True` e `revogado_em` nulo.
- A concessão é narrativa por caminho/instância e **não significa
  item consumido ou condições ambientais automaticamente verificadas**.

## Roteiro de homologação

1. Com backup e `db upgrade` concluídos, entrar como mestre e abrir
   o Pokémon de um jogador que possua evolução especial.
2. Liberar Eevee → Umbreon, com motivo narrativo; confirmar
   **Liberada pelo mestre** na ficha dele e **Depende do mestre** na
   ficha de outro Eevee e no ramo Espeon.
3. Entrar como jogador: visualizar a liberação, **sem** botão mestre
   e **sem** botão de evolução nesta etapa.
4. Voltar como mestre, revogar com motivo. Confirmar que o status
   voltou a depender do mestre.
5. Autorizar novamente e confirmar ausência de duplicatas; observar
   histórico da decisão. Tentar editar a espécie e confirmar
   invalidação de autorização antiga.
6. Conferir que itens, PV, natureza, Shiny e Box não foram alterados.

### Testes da etapa

```powershell
python -m pytest -q tests/test_autorizacao_evolucao_10e3_2.py tests/test_consulta_evolucao_10e3_1.py tests/test_evolucoes_regionais_10e2_5.py tests/test_equipe_pokemon.py tests/test_boxes.py tests/test_itens_inventario.py
```

CI `.github/workflows/test-autorizacao-evolucao-10e3-2.yml`.

## Próxima fase

**10E.3.3:** permitir ao treinador aceitar uma evolução individual
explicitamente, revalidando na mesma transação relação ativa,
condições, autorização mestre vigente e forma de origem.
**10E.3.4:** consumir pedras/itens corretamente e recalcular
atributos/PV, mantendo identidade e histórico. As duas entregas
precisam ser planejadas em conjunto para evitar evoluções parciais.
