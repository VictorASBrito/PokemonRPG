# 10E.4.1 — Revisão visual única: evoluções, formas e Mega no painel expandido

**Decisão confirmada pelo mestre (20/11/2026): uma só implantação.**
As ações passam a acontecer **dentro do Pokémon expandido no Painel do Jogador**,
enquanto a permissão Mega passa para o menu **⋮** do respectivo treinador
no painel geral do mestre. Não se cria uma etapa posterior para o toggle.

## Comportamento visual

| Situação | Componente no expandido |
|---|---|
| Evolução permanente com todos os requisitos atendidos | Ícone **vermelho**; abre os destinos evolutivos com sprite, nome, requisito e botão de confirmação |
| Exatamente uma forma alternativa | Botão **azul** exibindo **sprite da forma + nome**; ação direta |
| Duas ou mais formas alternativas | Botão **Mudar de forma**; abre menu acessível com **sprites + nomes** |
| Uma Megaforma | **Ícone da Mega Pedra + Mega Evoluir**, direto |
| Duas ou mais Megaformas, ex. Charizard X/Y | **Ícone da Mega Pedra + Mega Evoluir**; menu com as Megaformas |
| Forma temporária já ativa | Botão **Reverter forma** |
| Mega não liberada ou Pokémon fora do Campo | Mega aparece indicada, mas desabilitada/explicada |

O vermelho só aparece quando `consulta_evolucao.pode_evoluir` é
verdadeiro, o Pokémon não está no Campo e não há forma temporária
ativa. Evita anunciar uma ação que o servidor recusaria.

Os indicadores vermelho e azul ficam sobre o retrato somente
quando o Pokémon está expandido. O botão abre a área da ação
correspondente, sem trocar de página. Após POST de evolução ou
transformação, um redirect volta ao dashboard com `?foco=<pokemon_id>`;
o JS reabre o mesmo cartão automaticamente.

O menu e os botões usam HTML `<details>`, `<summary>`,
`<button>` e `<form>`, com foco/teclado acessíveis.
Confirmação JS antes das ações irreversíveis.

Os ícones são três SVGs locais originais:
`static/img/evolucao-disponivel.svg`,
`static/img/mudanca-forma.svg` e
`static/img/mega-pedra-ankar.svg`. Os sprites das formas
são lidos do catálogo `FormaPokemon` (com variante shiny
quando correspondente).

## Menu ⋮ do mestre

`Mestre → Painel → ⋮ do treinador → Mega Evolução` tem:

- símbolo da Mega Pedra;
- nome e estado atual (**Habilitada/Desabilitada**);
- switch de ativação/revogação.

O endpoint novo `POST /mestre/painel/jogadores/<personagem_id>/mega`
exige perfil mestre e o mesmo token CSRF das outras configurações.
Reutiliza **`permitir_mega_treinador`**, portanto conserva
a verificação de vínculo do mestre à campanha e a reversão das
Megas ativas quando o mestre revoga a permissão. **Sem pedras,
sem concessão por Pokémon**.

O antigo painel de permissões do Campo foi retirado da interface,
assim como os formulários duplicados de transformação presentes
nos cartões do Campo. O Campo mantém a representação e os dados
da forma ativa; os endpoints de serviço antigos continuam disponíveis
para compatibilidade/segurança de vínculos salvos, sem rota nova
desprotegida.

As telas tradicionais **Editar Pokémon** mantêm informação de
elegibilidade e os formulários de **autorização narrativa do mestre**,
mas não duplicam o botão de evolução ou transformação do jogador;
informam que o controle está no expandido. O mestre em modo de
prévia vê os dados, sem botões que executem ações do jogador.

## Implementação

- `app/services/painel_acoes_pokemon_service.py` agrega por instância
  resultados do serviço evolutivo 10E.3 e das formas 10E.4;
  mantém permissões, propriedade e bloqueios intactos.
- `app/routes/jogadores.py` calcula ações para a equipe e CSRF
  de evolução/forma; `app/routes/mestre.py` enriquece a prévia
  do jogador e cria o POST de permissão Mega via `⋮`.
- `app/services/painel_mestre_service.py` expõe apenas
  `mega_habilitada` no contexto do mestre; alteração real via
  serviço que verifica o mestre da campanha.
- `app/routes/pokemons.py` aceita origem do painel e redireciona
  de volta ao Pokémon expandido depois do POST, com URL segura.
- `templates/jogador/dashboard.html`, `static/js/dashboard-pokemon.js`,
  `static/css/dashboard.css`: indicadores vermelho/azul,
  menus e manutenção de foco.
- `templates/mestre/dashboard.html`,
  `static/css/painel-mestre-10d3.css`: configuração Mega nos
  três pontinhos.
- `templates/campo/painel.html`, `templates/campo/_times.html`,
  `templates/jogador/pokemon.html`: retirada de ações duplicadas.
- Testes de integração e regressão em
  `tests/test_painel_expandido_evolucao_10e4_1.py`
  e workflow `test-painel-expandido-evolucao-10e4-1.yml`.

## Preservação e homologação

**Não há migration nova.** São reutilizadas as colunas da etapa 10E.4,
incluindo `Personagem.mega_habilitada` e
`Pokemon.forma_temporaria_id` — o banco de produção já deve ter
`c42e10040001` aplicado.

Fluxos para homologar após integrar:
1. Jogador com Piplup nível suficiente abre Pokémon expandido;
   vê vermelho e pode escolher Prinplup. O cartão reabre após evoluir.
2. Morpeko com uma alternativa: aparece sprite + nome diretamente.
   Rotom com várias: menu **Mudar de forma**, com sprites/nome.
3. Mestre abre ⋮ do jogador, ativa o switch junto da Mega Pedra.
   O jogador coloca Charizard no Campo e escolhe Mega Evoluir
   (X ou Y). A forma temporária aparece no painel expandido,
   sem consumir itens.
4. Mestre desativa Mega; a Mega ativa reverte e os demais dados
   do Pokémon não são perdidos.
5. Confirmar que as ações não aparecem na prévia do mestre,
   e que a ficha /p/<login> mantém identidade separada.
6. Confirmar que o Campo não apresenta mais os controles antigos;
   ele continua exibindo as formas ativas.

A integração não deve editar diretamente dados de produção,
não deve reimportar a Pokédex e não modifica o esquema.
