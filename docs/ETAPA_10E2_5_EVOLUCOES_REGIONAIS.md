# 10E.2.5 — Auditoria e complemento das evoluções regionais de Ankar

**Base confirmada:** `main` depois do PR #16 mesclado. **Escopo:** somente
as formas da Pokédex #001–#898 que já existem no catálogo de Ankar.
**Sem migration** nem evolução de Pokémon já capturados.

## Diagnóstico: a causa

A versão 10E.2.4 consolidou **430 relações em nível de espécie**.
A maior parte das rotas variantes de Alola e Galar ficou de fora,
pois os CSVs da PokéAPI representam essas linhas por
`required_pokemon_form_id` e `evolved_pokemon_form_id` (ou
`region_id`) e não apenas `evolved_species_id`.

Conferência no `data/catalogo/pokemons.json`:
- **18** formas `-alola`: **zero** vínculos no JSON nacional anterior.
- **18** formas `-galar`: **seis** apareciam como origem de vínculos
  já presentes (Meowth→Perrserker, Farfetch'd→Sirfetch'd,
  Mr. Mime→Mr. Rime, Corsola→Cursola, Linoone→Obstagoon,
  Yamask→Runerigus).
- **Duas** formas `darmanitan-galar-normal` e
  `darmanitan-galar-zen` não estavam vinculadas.
- Contagem: **38 formas regionais**, seis com vínculo no JSON anterior.
  **Não confundir** uma forma sem relação com erro se não evolui,
  como Articuno/Zapdos/Moltres de Galar e Stunfisk de Galar.
  Darmanitan Zen é transformação de batalha, **não** evolução.

A leitura é do **código versionado**, não do PostgreSQL de produção.
O mestre confirmou que já importou uma parte das relações; o novo
comando confere o estado do PostgreSQL localmente antes de aplicar.

## 17 relações adicionais verificadas

**Regulares** (nível ou pedra sem condições adicionais):

| Origem | Destino | Requisito |
|---|---|---|
| Sandshrew (Alola) | Sandslash (Alola) | Pedra do Gelo |
| Vulpix (Alola) | Ninetales (Alola) | Pedra do Gelo |
| Diglett (Alola) | Dugtrio (Alola) | Nível 26 |
| Geodude (Alola) | Graveler (Alola) | Nível 25 |
| Grimer (Alola) | Muk (Alola) | Nível 38 |
| Ponyta (Galar) | Rapidash (Galar) | Nível 40 |
| Zigzagoon (Galar) | Linoone (Galar) | Nível 20 |
| Darumaka (Galar) | Darmanitan (Galar Normal) | Pedra do Gelo |

**Reservadas ao mestre**, mesmo quando compartilham nível ou pedra
com a forma comum, por causa de condições adicionais:

| Origem | Destino | Por que é especial |
|---|---|---|
| Rattata (Alola) | Raticate (Alola) | Nível 20 **à noite** |
| Pikachu | Raichu (Alola) | Pedra do Trovão **e contexto de Alola** |
| Meowth (Alola) | Persian (Alola) | Amizade; não há amizade numérica em Ankar |
| Graveler (Alola) | Golem (Alola) | Troca |
| Exeggcute | Exeggutor (Alola) | Pedra da Folha **e região Alola** |
| Cubone | Marowak (Alola) | Nível 28 **à noite em Alola** |
| Slowpoke (Galar) | Slowbro (Galar) | **Galarica Cuff**, item especial |
| Slowpoke (Galar) | Slowking (Galar) | **Galarica Wreath**, item especial |
| Koffing | Weezing (Galar) | Nível 35 **na região Galar** |

Total: **17** vínculos complementares, **8 regulares + 9 com
liberação individual**. O conjunto nacional de 430 permanece intacto,
resultando em **447 relações distintas na fonte combinada**, sem
prometer que todas foram inseridas no banco (vínculos já existentes
não são sobrescritos). O nível segue vinculado ao treinador.

### Fontes e rastreabilidade

- PokéAPI: CSV `pokemon_evolution.csv`, `pokemon_species.csv`
  e `items.csv` do repositório `PokeAPI/pokeapi`, versão pública
  consultada em 20/11/2026. Os 17 registros guardam número nacional,
  códigos da origem/destino, `linha_pokeapi`,
  `version_group_id`, IDs de forma e link de evolution-chain.
- Pokémon Database: verificação de formas individuais, incluindo
  [Sandshrew](https://pokemondb.net/pokedex/sandshrew),
  [Vulpix](https://pokemondb.net/pokedex/vulpix),
  [Rattata](https://pokemondb.net/pokedex/rattata),
  [Diglett](https://pokemondb.net/pokedex/diglett),
  [Golem](https://pokemondb.net/pokedex/golem),
  [Ponyta](https://pokemondb.net/pokedex/ponyta),
  [Zigzagoon](https://pokemondb.net/pokedex/zigzagoon),
  [Darumaka](https://pokemondb.net/pokedex/darumaka)
  e [Slowpoke](https://pokemondb.net/pokedex/slowpoke).
- Manual `pkmrpg-playtest-2_5.pdf` capítulo 9 e capítulo 16
  para regras gerais. **A ausência de amizade numérica em Ankar e o
  tratamento de pedras comuns foram decisões do mestre**, não
  substituições ocultas por regras dos jogos.
- Dataset revisado: `data/referencias/evolucoes_regionais_10e2_5.json`.

## Como simular e adicionar somente os faltantes

### Pelo site

Após merge, abra **Mestre → Catálogo Pokémon → Completar árvores
regionais**. Essa página é o **modo regional** da ferramenta anterior,
mas utiliza assinatura SHA256 e dataset separados. Mostra os 17
possíveis, quantos já existem e quantos serão adicionados.
Confirme um backup restaurável do PostgreSQL antes da aplicação.
O mestre digita `COMPLETAR-REGIONAIS-ANKAR` no formulário.

### Pelo terminal PowerShell

**Simulação — não altera o banco:**

```powershell
flask --app app.py catalogo completar-arvores-regionais
```

**Após backup real verificado e revisão do plano:**

```powershell
flask --app app.py catalogo completar-arvores-regionais --aplicar --plano SUA_ASSINATURA --backup-confirmado --confirmar COMPLETAR-REGIONAIS-ANKAR
```

**Conferir idempotência, depois visitar árvores no site:**

```powershell
flask --app app.py catalogo completar-arvores-regionais
```

Esperado: **zero novas relações** após aplicação total. Se já existirem
alguns dos 17 pares, o resultado inicial será menor. Se houver
forma ausente, número divergente, vínculo conflitante ou ciclo,
**todas as alterações são bloqueadas** até revisão humana.

## Garantias e limitações

- Mantém o importador nacional 10E.2.4 intacto, usando opção
  `apenas_regionais=True` no serviço já testado.
- Reutiliza `EvolucaoPokemon`, `HistoricoAlteracao`,
  SHA256 do estado e assinatura, confirmação de backup, verificação
  de FK/ciclo, travas e transação única.
- **Não reativa, não apaga, não reescreve** vínculos existentes, ainda
  que cadastrados manualmente. As seis relações de Galar anteriores
  continuam preservadas.
- Relações especiais recebem
  `requer_liberacao_mestre=True` e
  `liberacao_individual=True`, com condições legíveis na árvore.
  **Autorizar e evoluir um Pokémon específico é função futura
  da 10E.3**; esta etapa só cria os registros de catálogo.
- Evolução **nunca** muda `Pokemon.forma_pokemon_id` nesta etapa.
  Nenhum item, Box, PV, natureza, Shiny ou nível é alterado.
- **Darmanitan (Galar Zen)** depende de modo de combate, escopo
  da 10E.4 — não deve ser forçado como evolução permanente.
- Não há formas de Hisui/Paldea na fonte atual de 898 espécies de
  Ankar; isso não equivale a assegurar que futuras gerações já
  estejam contempladas.

### Testes

```powershell
python -m pytest -q tests/test_evolucoes_regionais_10e2_5.py tests/test_importacao_evolucoes_10e2_4.py tests/test_arvore_evolutiva_10e2_3.py tests/test_evolucoes_admin_10e2_2.py tests/test_catalogo_admin.py tests/test_auditoria_pokedex_10e2_1.py
```

CI `.github/workflows/test-evolucoes-regionais-10e2-5.yml`.
A CI automatizada usa SQLite; teste manual no PostgreSQL da
campanha é separado e deve começar pela simulação.
