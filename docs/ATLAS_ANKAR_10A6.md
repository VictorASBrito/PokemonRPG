# Atlas de Ankar — Etapa 10A.6: Vínculos de formas e busca por Pokémon

**Data:** 28/10/2026. **Tipo:** atualização incremental, sem migrations.

## Objetivo

Vincular os 33 nomes encontrados nas planilhas de Ankar que não coincidiam com os nomes das formas cadastradas. A correspondência foi conferida contra `data/catalogo/pokemons.json` do repositório (códigos de forma do importador oficial). **Os vínculos só ficam ativos se a forma correspondente existir e estiver ativa no PostgreSQL atual.** Nenhum registro da planilha ou forma do banco foi renomeado.

### Correspondências diretas

| Nome nas planilhas | Código da forma no catálogo | Nome no catálogo |
| --- | --- | --- |
| Corsola-G | `corsola-galar` | Corsola (Galar) |
| Darumaka-G | `darumaka-galar` | Darumaka (Galar) |
| Diglett-A | `diglett-alola` | Diglett (Alola) |
| Farfetch'd-G | `farfetch-d-galar` | Farfetch'd (Galar) |
| Geodude-A | `geodude-alola` | Geodude (Alola) |
| Graveler-A | `graveler-alola` | Graveler (Alola) |
| Grimer-A | `grimer-alola` | Grimer (Alola) |
| Linoone-G | `linoone-galar` | Linoone (Galar) |
| Meowth-A | `meowth-alola` | Meowth (Alola) |
| Meowth-G | `meowth-galar` | Meowth (Galar) |
| Mr. Mime-G | `mr-mime-galar` | Mr. Mime (Galar) |
| Muk-A | `muk-alola` | Muk (Alola) |
| Ponyta-G | `ponyta-galar` | Ponyta (Galar) |
| Rattata-A | `rattata-alola` | Rattata (Alola) |
| Sandshrew-A | `sandshrew-alola` | Sandshrew (Alola) |
| Stunfisk-G | `stunfisk-galar` | Stunfisk (Galar) |
| Vulpix-A | `vulpix-alola` | Vulpix (Alola) |
| Yamask-G | `yamask-galar` | Yamask (Galar) |
| Zigzagoon-G | `zigzagoon-galar` | Zigzagoon (Galar) |
| Oricorio (E) | `oricorio-pom-pom` | Oricorio (Pom-Pom) |
| Oricorio (F) | `oricorio-baile` | Oricorio (Baile) |
| Oricorio (G) | `oricorio-sensu` | Oricorio (Sensu) |
| Oricorio (P) | `oricorio-pa-hu` | Oricorio (Pa'hu) |

**Atenção:** a relação das letras E/F/G/P de Oricorio com seus tipos e estilos foi inferida pelas iniciais (Elétrico/Fogo/Ghost/Psíquico). Confirmar se a campanha usa essa mesma convenção; o arquivo `app/data/ankar_formas_aliases.json` permite revisar essas associações sem tocar nas planilhas ou no banco.

### Escolha de forma ao gerar

Para nomes sem variante indicada na planilha, o Atlas exibe as formas compatíveis e pede ao mestre que escolha qual delas apareceu:

| Nome genérico | Formas apresentadas |
| --- | --- |
| Basculin | Vermelho, Azul |
| Burmy | Planta, Arenoso, Entulho |
| Eiscue | Congelado, Revelado |
| Indeedee | Macho, Fêmea |
| Minior | Meteoro, Núcleo |
| Morpeko | Satisfeito, Faminto |
| Pumpkaboo | Médio, Pequeno, Grande, Gigante |
| Wishiwashi | Sozinho, Cardume |

Nenhuma forma é escolhida automaticamente quando duas ou mais opções estão ativas. O POST valida no servidor que o UUID escolhido está entre as opções permitidas para **aquele encontro da planilha**; valores manipulados são rejeitados. Com uma única forma, o fluxo permanece direto como antes, mantendo a geração existente de natureza, sexo e Shiny.

### Shellos — limite do catálogo atual

`Shellos (A)` e `Shellos (R)` apontam **por enquanto** para o mesmo código `shellos`: a fonte oficial disponível contém apenas `Shellos`, sem formas separadas por cor. O Atlas mantém a sigla original visível e informa no card que o vínculo é genérico. **Isso não significa que as duas variantes sejam idênticas no mundo da campanha.** Para imagens e formas independentes, elas precisarão ser criadas no catálogo mediante uma etapa separada.

### Pesquisa abaixo do mapa

- A busca passa a aceitar nomes da planilha (`Grimer-A`, `Corsola-G`) e nomes da forma correspondente (`Grimer (Alola)`, `Corsola (Galar)`), com busca tolerante a acentos, parênteses e pontuação.
- O resultado filtra rotas, cidades e pontos de interesse **onde o Pokémon realmente consta**, indicando o nome de origem e os terrenos/zonas correspondentes.
- A navegação anterior por nome do local, habitat, acesso e terreno continua válida.
- Os 119 pontos do mapa, filtros de categorias, zoom removido e coordenadas da Etapa 10A.5 não foram alterados.

### Segurança e compatibilidade

- Não modifica `data/catalogo/pokemons.json`, `app/data/catalogo_ankar_visual.json` ou as planilhas XLSX.
- Não altera os modelos nem o PostgreSQL, não cria migrations e não executa capturas automaticamente ao navegar ou pesquisar.
- Mantém a autenticação de mestre, o token CSRF, o limite de capturáveis, a atribuição e a geração padrão pelo serviço existente.
- Os cards sem forma ativa permanecem visíveis como pendentes, sem botões que produzam formas incorretas.
- `X` e `Random` nunca viram formas geráveis.

## Arquivos da atualização

- `app/data/ankar_formas_aliases.json` (novo)
- `app/services/ankar_formas_service.py` (novo)
- `app/services/regiao_ankar_service.py` (atualizado)
- `app/routes/regiao.py` (atualizado)
- `templates/regiao/indice.html` e `templates/regiao/detalhe.html` (atualizados)
- `static/js/atlas-ankar.js` e `static/css/atlas-ankar.css` (atualizados)
- `tests/test_ankar_10a6_vinculos.py` e `tests/test_ankar_10a6_flask.py` (novos)
- `scripts/diagnosticar_formas_ankar.py` e `scripts/registrar_atlas_10a6.py` (novos)

## Instalação e testes

Extrair o pacote na raiz do projeto e substituir **somente os arquivos listados**. Reiniciar Flask e atualizar navegador (`Ctrl+F5`) para recarregar JS/CSS versionados como `v10a6`.

```powershell
python scripts/registrar_atlas_10a6.py
python scripts/diagnosticar_formas_ankar.py
python -m pytest -q tests/test_ankar_10a6_vinculos.py tests/test_ankar_10a6_flask.py tests/test_ankar_10a5_mapa_fixo.py tests/test_mapa_ankar_visual.py tests/test_atlas_10a4_1_template.py tests/test_ankar_10a4.py tests/test_atlas_ankar_flask.py
```

**Validação no ambiente de preparação:** 22 testes isolados de correspondência, template e regressão do mapa passaram; `node --check` e compilação Python passaram. **Testes Flask/SQLAlchemy e validação dos códigos ativos no PostgreSQL real permanecem pendentes do ambiente local do projeto.**

## Próxima revisão

Verificar quais vínculos foram efetivamente encontrados no PostgreSQL com `python scripts/diagnosticar_formas_ankar.py`. Confirmar a convenção das siglas de Oricorio e decidir se serão cadastradas formas próprias de Shellos azul/rosa. Testar a busca por `Corsola-G` e `Corsola (Galar)`, abrir a Rota 4 e gerar encontro selecionando um treinador.
