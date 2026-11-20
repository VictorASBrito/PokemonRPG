# 10E.2.3 — Árvore evolutiva, ramificações e revisão de fontes

**Status:** código em PR; integração e homologação no PostgreSQL de Ankar
são separadas. **Sem migration** e sem importar relações em massa.

## 1. Objetivo

A etapa 10E.2.2 já permite criar/editar relações dirigidas, mas lista
apenas o que chega/sai da forma selecionada. A 10E.2.3 apresenta toda a
**família evolutiva conectada** por relações permanentes ativas, com
pré-evoluções, estágios intermediários, ramos alternativos, destinos
compartilhados e seus requisitos. Lê `EvolucaoPokemon`, sem modificar
`Pokemon`, Box, PV, habilidades ou nível do jogador.

Interface: **Mestre → Catálogo → Pokémon → Relações → Ver árvore da família**.
Endereço GET: `/mestre/catalogo/pokemons/<UUID>/arvore`.

O modelo `ArvoreEvolutiva` é calculado pelo serviço
`app/services/arvore_evolutiva_service.py`; o template Jinja
`pokemon_arvore.html` e o CSS responsivo `arvore-evolutiva.css`
exibem estágios, ramos e links para editar cada relação.

### Como funciona

- Consulta só vínculos `EvolucaoPokemon.ativo=True`. `requisitos.tipo_relacao =
  evolucao` é o vínculo permanente; o legado sem tipo assume evolução.
- Busca ancestrais e descendentes pelo grafo **não direcionado para
  descoberta da família**, mas **ordena as etapas pela direção original**.
  Usa ordenação topológica (Kahn) para colocar cada estágio após
  todos os seus predecessores e representar convergências.
- Cada cartão mostra forma, imagem, nome, número nacional e seus
  predecessores com os requisitos cadastrados. Entradas simultâneas
  apontam para o mesmo cartão, sem duplicá-lo.
- Vínculos `mega`, `alternativa` e `regional` aparecem em seção
  separada e não criam estágios permanentes nem troca de forma.
- Um ciclo legado é sinalizado, mas não provoca recursão infinita.
  Limite de 120 formas por família, com aviso de truncamento; nenhuma
  mutação ocorre durante a visualização.
- Acesso é exclusivo ao perfil mestre, como as demais páginas do
  catálogo. Não existe botão de evolução de Pokémon de jogador.

## 2. Revisão das fontes (20/11/2026)

**Fontes consultadas diretamente:**

- `pkmrpg-playtest-2_5.pdf`, **cap. 9**, página impressa 44 (PDF
  página 45): evolução por nível/amizade/item, evolução opcional,
  recálculo dos atributos e Mega temporária. Continuação na
  página impressa 45 (PDF 46).
- **Cap. 16**, páginas impressas **59–60** (PDF 60–61): materiais,
  pedras de evolução e observação de que qualquer **material** exige
  **amizade máxima 100**. Isso conflita com a remoção da amizade
  numérica na campanha Ankar; o requisito não foi silenciosamente
  reintroduzido.
- PokéAPI: documentação `https://pokeapi.co/docs/v2`,
  `https://pokeapi.co/api/v2/evolution-chain/67/` (família Eevee)
  e `/10/` (Pichu/Pikachu/Raichu). Objetos `evolution_details`
  descrevem `min_level`, `item`, `held_item`, `trigger`,
  amizade e condições. Informações podem variar por versão.
- Pokémon Database: `https://pokemondb.net/evolution/stone`,
  `/evolution/trade` e `/pokedex/eevee`.

**Arquivo novo:** `data/referencias/evolucoes_revisadas_10e2_3.json`,
com 12 propostas adicionais às seis evoluções da 10E.2.2.

| Proposta | Situação | Fonte do critério |
|---|---|---|
| Eevee → Vaporeon | Aprovável individualmente | Pedra da Água, livro e jogos |
| Eevee → Jolteon | Aprovável individualmente | Pedra do Trovão |
| Eevee → Flareon | Aprovável individualmente | Pedra do Fogo |
| Eevee → Leafeon | Aprovável individualmente | Pedra da Folha; jogos antigos também usam Moss Rock |
| Eevee → Glaceon | Aprovável individualmente | Pedra do Gelo; jogos antigos também usam Ice Rock |
| Pikachu → Raichu (padrão) | Aprovável individualmente | Pedra do Trovão |
| Vulpix (padrão) → Ninetales (padrão) | Aprovável individualmente | Pedra do Fogo |
| Eevee → Espeon | Pendente | Jogos: amizade + dia; livro: Estilhaço do Sol para Eevee; Ankar sem amizade numérica |
| Eevee → Umbreon | Pendente | Jogos: amizade + noite; livro: Estilhaço da Lua; Ankar sem amizade numérica |
| Eevee → Sylveon | Pendente | Jogos: movimento Fada + afeto/amizade por versão; livro: Pedra da Lua cita Eevee sem destino |
| Porygon → Porygon2 | Pendente | Jogos: troca segurando Upgrade; livro: Atualização, sem menção explícita de troca |
| Porygon2 → Porygon-Z | Pendente | Jogos: troca segurando Dubious Disc; livro: Disco Dúbio, sem menção explícita de troca |

**Cuidado importante:** mesmo as sete propostas com pedras possuem
alerta explícito: o manual requer amizade máxima para usar materiais,
e essa mecânica não está habilitada em Ankar. A aprovação pelo mestre
é a decisão administrativa de registrar a relação, mas **não é a
execução da evolução**. A etapa 10E.3 deverá definir a elegibilidade
real, consumo de item e confirmação narrativa antes de mudar formas
de Pokémon de jogador.

As cinco propostas **pendentes** são exibidas no editor, **sem botão
de aprovação**, e também são recusadas no serviço caso alguém fabrique
manualmente um POST. Para aplicá-las é necessário definir uma regra de
Ankar e cadastrá-la manualmente no painel, documentando a decisão.
Não inventar exigências de níveis, locais, períodos ou amizade.

## 3. Como validar

1. Atualizar branch, iniciar servidor e entrar como mestre.
2. Abrir forma Charmander → **Relações** → **Ver árvore da família**.
   Sem relações aprovadas, o diagrama mostra só a forma selecionada.
3. Cadastrar Charmander → Charmeleon e Charmeleon → Charizard,
   retornando à árvore para ver os três estágios e requisitos.
4. Em Eevee, conferir oito propostas: cinco itens aprováveis,
   três pendentes. Aprovar uma pedra e confirmar que o grafo passa
   a apresentar um ramo; o Pokémon no Box não deve mudar.
5. Revisar vínculos Mega e regionais separados da árvore permanente.
6. Rodar o teste:

```powershell
python -m pytest -q tests/test_arvore_evolutiva_10e2_3.py tests/test_evolucoes_admin_10e2_2.py tests/test_catalogo_admin.py tests/test_auditoria_pokedex_10e2_1.py tests/test_ordenacao_pokedex_10e1.py
```

Workflow GitHub Actions:
`.github/workflows/test-arvore-evolutiva-10e2-3.yml`.

## 4. O que fica para a próxima etapa

**10E.3 — Evolução efetiva de Pokémon do jogador**, incluindo
validação dos requisitos, nível **compartilhado com o treinador**,
consumo de materiais no inventário, revisão de decisões narrativas,
atualização transacional da forma com registro de histórico e
recalculo de atributos/PV sem perder natureza, Shiny, golpes, itens
ou identidade. Nada disso é ativado na 10E.2.3.

**10E.4 — Formas temporárias**, Mega Evolução e retorno após batalha
sem reintroduzir amizade numérica/XP individual.
