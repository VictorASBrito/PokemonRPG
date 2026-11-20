# Etapa 10E.3.1 — Consulta de elegibilidade evolutiva na ficha

**Escopo:** consulta e exibição de opções, sem ações de evolução ou autorizações. A etapa pressupõe as árvores oficiais (10E.2.4) e regionais (10E.2.5) já cadastradas no PostgreSQL de Ankar. **Sem migration**.

## Objetivo

Diferenciar o fato de existir uma relação no catálogo do fato de um
**Pokémon específico do jogador** cumprir a condição para evoluir.
O nível individual não existe: toda a avaliação por nível usa o
**nível em `personagens.nivel`**, compartilhado com a equipe.
Pedras são conferidas em `personagem_itens.quantidade`,
vinculadas ao **mesmo personagem**.

As fichas de Pokémon existentes (jogador e mestre) ganham uma seção
**Evoluções de [forma]**, após o formulário principal:
- **Requisito atendido:** o nível do treinador alcançou o mínimo, ou
  ao menos uma pedra evolutiva correspondente está na mochila;
- **Nível insuficiente:** a ficha informa o nível mínimo e a diferença;
- **Pedra não encontrada:** não há unidade ativa daquela pedra no
  inventário real do treinador; item meramente equipado não é contado;
- **Depende do mestre:** amizade, troca, item especial, noite, clima,
  localização, gênero, golpe, forma/região ou qualquer outra condição
  adicional. Os destinos ficam visíveis, mas sem autorização implícita.

Uma forma sem evoluções permanentes ativas recebe a mensagem de ausência
de vínculos. **Mega Evolução, mudança reversível e parentesco regional
não são tratados como evolução permanente** na consulta.

## Implementação

- `app/services/consulta_evolucao_service.py`:
  `consultar_evolucoes_pokemon(pokemon, personagem)` obtém as arestas
  `EvolucaoPokemon` ativas da **forma exata** em
  `pokemon.forma_pokemon_id`; recusa Pokémon de outro personagem,
  inativos e destinos inativos. Consulta o saldo de pedras com JOIN
  `PersonagemItem` / `Item`, respeitando `Item.ativo`.
  Classifica com abordagem conservadora para nunca anunciar
  uma evolução narrativa como comum.
- `app/routes/pokemons.py`: reutiliza o mesmo `_editar` para
  `/jogador/pokemon/<id>` e
  `/mestre/jogadores/<id>/pokemon/<id>`, carregando os Pokémon
  do personagem pelo contexto autorizado **já existente**.
  Não cria um endpoint de acesso adicional ao Pokémon.
- `templates/jogador/pokemon.html` e `static/css/pokemon.css`:
  seção legível e responsiva fora dos formulários de POST. Não existe
  botão de evoluir, liberador ou consumidor de item.

### Política de segurança

- A expressão `aprovado_mestre=True` em **relações do catálogo**
  é uma aprovação editorial da linha evolutiva, não uma concessão
  para o Pokémon de um jogador. **Nunca libera** o ramo especial.
- `requer_liberacao_mestre`, `liberacao_individual`, gatilhos
  `amizade`, `troca`, `especial` e requisitos condicionais são
  tratados como **requer mestre**. Ex.: Espeon, Umbreon, Sylveon,
  Gallade com restrição de gênero, Slowking de Galar com Galarica
  Wreath e Raticate de Alola à noite.
- Apenas itens de pedra evolutiva **identificados pelo nome/código
  exato do catálogo** contam como pedra comum. Itens desconhecidos,
  itens específicos ou evolução por nível com condição adicional
  são conservadoramente encaminhados ao mestre.
- São exibidas **somente** relações ativas e permanentes,
  preservando distinções de origem: Vulpix de Alola não pode
  aproveitar relação do Vulpix comum.
- A consulta não escreve, comita, consome item, altera HP/atributos,
  espécie/forma, nível, Box, natureza, golpes, Shiny ou histórico.
- **Requisito atendido não equivale a evolução executada**.
  A escolha do jogador, consumo transacional de pedra e autorização
  individual do mestre **ainda serão desenvolvidos**.

## Homologação sugerida

Entre com usuário do jogador e abra um Pokémon capturado na equipe
ou na Box. A seção de evoluções deve mostrar a situação dos seus
ramos, sem botões de alteração de forma. Exemplos:
1. Charmander nível 12 de treinador: evolução a Charmeleon bloqueada
   por nível 16; no nível 48, requisito atendido.
2. Eevee com e sem Pedra da Água no inventário: Vaporeon alterna
   entre requisito atendido e pedra ausente; Umbreon e Espeon
   permanecem restritos ao mestre.
3. Vulpix (Alola) com Pedra do Gelo: Ninetales (Alola) pode
   aparecer com requisito atendido; forma comum não aparece.
4. Rattata (Alola) com treinador nível 48: evolução para Raticate
   (Alola) permanece restrita por condição noturna.
5. Conferir a mesma seção pela ficha do mestre.

### Testes

```powershell
python -m pytest -q tests/test_consulta_evolucao_10e3_1.py tests/test_evolucoes_regionais_10e2_5.py tests/test_importacao_evolucoes_10e2_4.py tests/test_arvore_evolutiva_10e2_3.py tests/test_evolucoes_admin_10e2_2.py tests/test_catalogo_admin.py
```

Workflow `.github/workflows/test-elegibilidade-evolucao-10e3-1.yml`.
O teste automatizado usa SQLite; é necessária homologação da tela
no PostgreSQL real após integrar o PR.

## Próximo passo

**10E.3.2:** persistir autorizações por instância de Pokémon, por
relação evolutiva e por mestre, com histórico e expiração/cancelamento.
Isso deve exigir migration e proteção transacional. Em seguida, 10E.3.3
ação explícita do jogador para evoluir e 10E.3.4 consumo correto de itens,
recalculo de atributos e PV sem perder identidade.
