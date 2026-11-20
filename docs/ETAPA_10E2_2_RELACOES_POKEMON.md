# 10E.2.2 — Editor de relações evolutivas e formas Pokémon

**Status:** implementado em branch e submetido a CI; o banco real de Ankar
não recebe relações automaticamente. Sem migration: reutiliza
`EvolucaoPokemon` e `HistoricoAlteracao`.

## 1. Fontes e critério de decisão

1. **Campanha Ankar**: regra vigente do projeto e decisões do mestre
   prevalecem sobre o livro e sobre regras dos jogos. Nível do Pokémon
   = nível do treinador; não há XP individual nem amizade numérica ativa.
2. **Manual PKMRPG v2.5** (arquivo fornecido, cap. 9, pp. 44–45):
   evolução por nível, amizade ou item; evolução é opcional; atributos
   recalculados após evoluir; Mega temporária no combate e revertida
   no fim do combate ou desmaio, com Pedra Chave/Mega Pedra. No capítulo
   16, seção “Pedras para Mega Evolução” (p. 60), exige amizade ≥90
   para usar pedras: **não aplicar automaticamente**, pois a campanha
   de Ankar removeu a mecânica de amizade.
3. **PokéAPI**: endpoint documentado
   `https://pokeapi.co/api/v2/evolution-chain/{id}/`. O grafo
   `chain.evolves_to` contém `evolution_details` com `trigger`,
   `min_level` e outros requisitos. Não presumir que a API resolve
   todas as condições narrativas nem que valores de versões diferentes
   são idênticos.
4. **Pokémon Database**: `https://pokemondb.net/evolution/level`
   como verificação cruzada de níveis para famílias de iniciais.
   Outras formas (amizade, item, troca) exigem comparação individual
   entre jogos, livro e decisões do mestre.

### Seis evoluções verificadas

| Origem | Destino | Nível | PokéAPI | Pokémon Database |
|---|---|---:|---|---|
| Bulbasaur | Ivysaur | 16 | evolution-chain/1 | evolution/level |
| Ivysaur | Venusaur | 32 | evolution-chain/1 | evolution/level |
| Charmander | Charmeleon | 16 | evolution-chain/2 | evolution/level |
| Charmeleon | Charizard | 36 | evolution-chain/2 | evolution/level |
| Squirtle | Wartortle | 16 | evolution-chain/3 | evolution/level |
| Wartortle | Blastoise | 36 | evolution-chain/3 | evolution/level |

A entrada Charmander → Charmeleon também é indicada textualmente
na página 44 do livro. Os outros níveis listados vêm do cruzamento
PokéAPI/Pokémon Database, não de uma tabela do livro.

Os dados verificáveis e links de referência constam em
`data/referencias/evolucoes_verificadas_10e2.json`.
O sistema **não consulta sites em tempo de execução**, evitando
travar a administração devido à internet ou importar requisitos
externos sem aprovação. Somente as seis sugestões aparecem no
editor; **cada uma só é gravada se o mestre clicar “Aprovar e cadastrar”**.

## 2. Uso no site

Entre com perfil **mestre**:

1. Abra `/mestre/catalogo/pokemons`, selecione a forma e clique
   **Relações** (ou em “Evoluções e formas relacionadas” na edição).
2. Consulte relações de entrada (pré-evoluções) e de saída
   (destinos; ativas ou inativas), com acesso à ficha da outra forma.
3. Para iniciais, aprove uma sugestão revisada; para outras espécies,
   pesquise um destino existente e informe tipo, gatilho, eventual
   nível, item ou condição, fonte e observações.
4. Edite um vínculo salvo ou **desative-o** (soft-delete), mantendo
   histórico de auditoria. A edição de vínculo desativado o reativa.

### Categorias

| Tipo de relação | Uso permitido |
|---|---|
| `evolucao` | Direção permanente; gatilhos por nível, item, troca, amizade ou condição especial; não pode formar ciclos |
| `mega` | Base → forma de categoria `mega` **da mesma espécie**; exige identificação da Mega Pedra ou condição especial; **não efetua transformação** |
| `alternativa` | Forma → variante `alternativa` da mesma espécie, com condição explícita; retorno será tratado na 10E.4 |
| `regional` | Base → variante `regional` da mesma espécie, como parentesco; **não é troca de forma liberada** |

**Importante**: requisitos com amizade ou troca ficam apenas como
metadados narrativos, sem elegibilidade automática. Relações Mega
não geram aresta inversa e não interferem no verificador de ciclos
permanentes. `EvolucaoPokemon.tipo_requisito` conserva o gatilho;
`requisitos["tipo_relacao"]` distingue evolução de outras ligações.
Registros legados sem `tipo_relacao` são considerados evolução
permanente por precaução.

### Auditoria e proteção

- Rotas usam `@perfil_obrigatorio("mestre")`, o padrão vigente.
- Validação rejeita mesmo ID de origem e destino, tipo/gatilho
  incompatíveis, forma inativa, relação duplicada, ciclos de evolução,
  Mega como evolução permanente e variantes de espécie errada.
- `requisitos` armazena nível e condições, fonte e URL HTTPS.
  Valores externos não comandam mudanças de personagem.
- Histórico da relação usa `HistoricoAlteracao` em inclusão,
  edição e desativação. Nenhuma tabela adicional ou migration.
- A entrada no editor não faz mudanças em
  `Pokemon.forma_pokemon_id`/Box/PV, nem cria itens/níveis.
- O primeiro incremento mostra **vínculos diretos**, não uma árvore
  evolutiva global completa. Visualização em árvore e elegibilidade
  serão incrementos separados.

## 3. Testes

```powershell
python -m pytest -q tests/test_evolucoes_admin_10e2_2.py tests/test_catalogo_admin.py tests/test_auditoria_pokedex_10e2_1.py tests/test_ordenacao_pokedex_10e1.py
```

Workflow: `.github/workflows/test-evolucoes-10e2-2.yml`.
Validar os resultados de CI na própria PR. Teste na instalação
PostgreSQL real deve ser realizado após revisão e merge.

## 4. Etapas seguintes

- **10E.2.3**: visão em árvore (todos os estágios e ramificações),
  comparação sistemática de outras cadeias pela PokéAPI e
  Pokémon Database e importação somente após aprovação explícita.
- **10E.3**: cálculo da elegibilidade usando nível do treinador,
  eventos e item, autorização do mestre e confirmação; preservar
  identidade, atributos, histórico e nível compartilhado.
- **10E.4**: estado temporário de Mega/forma alternativa, reversão
  segura após combate e regras narrativas de Ankar, sem ativação
  automática de amizade.
