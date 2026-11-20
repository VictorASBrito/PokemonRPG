# Etapas 10E.3.3 e 10E.3.4 — Evolução efetiva e consumo atômico

**Escopo:** evolução permanente por decisão explícita do jogador. Nível
sempre compartilhado via `personagens.nivel`; não existe XP, nível ou
amizade numéricos individuais na implementação de Ankar.

**Pré-requisitos:** árvores nacionais/regionais 10E.2.4/5 importadas
e implementação 10E.3.2 em `main` com migration
`b93e21c031a2` **já aplicada ao PostgreSQL**. Nesta etapa **não há
nova migration**.

## Regra estabelecida

A seção **Evoluções** na ficha dos Pokémon do jogador mostra
**Evoluir para [forma]** somente quando a evolução pode ser concluída
com os dados atuais. A escolha e confirmação pertencem ao jogador; o
mestre ainda concede/revoga apenas as condições narrativas especiais.

| Tipo | Requisitos para evoluir |
|---|---|
| Nível puro | Nível atual do treinador ≥ nível do catálogo |
| Pedra comum | Pedra correta no inventário do personagem, ativa e consumível |
| Amizade, troca, horário, localização, golpe, gênero ou outra condição | Autorização vigente para **aquele Pokémon e aquele ramo**, dada pelo mestre; nível mínimo informado também é verificado |
| Especial com material | Autorização individual + material específico na mochila, ativo e consumível, com 1 unidade consumida |

**Exemplos:** Piplup nível 50 pode escolher evoluir para Prinplup;
Eevee com Pedra da Água pode evoluir para Vaporeon consumindo uma
unidade; Eevee→Umbreon exige concessão narrativa individual, mas não
material; Slowpoke de Galar→Slowbro de Galar requer concessão
individual **e** Bracelete Galariano. As opções não atendidas
permanecem visíveis, porém sem botão de evolução.

Após a evolução, a ficha apresenta a nova forma, e as permissões
concedidas para a origem são encerradas para evitar reutilização
após eventual edição manual do Pokémon.

## Fontes e decisão de adaptação

O manual `pkmrpg-playtest-2_5.pdf`, **capítulo 9, página impressa
44**, estabelece que evoluir é decisão do treinador e que os
atributos devem ser recalculados a partir dos atributos-base do
estágio evoluído. O **capítulo 16, páginas impressas 59–60**, lista
materiais e pedras, além do requisito de amizade 100 do livro.
**Ankar removeu a amizade numérica**. A autorização narrativa pelo
mestre substitui a liberação por amizade nas relações especiais;
pedras comuns são caminhos regulares conforme decisão anterior.

O livro não fixa nesta seção o tratamento dos **PV atuais durante
a transformação**. Política de engenharia adotada para Ankar:
preservar o *dano absoluto já sofrido*. Por exemplo, se antes
o Pokémon tinha 70/80 PV (10 de dano) e depois passa a ter máximo
100, fica com 90/100 PV. Pokémon com 0 PV permanece desmaiado.
Se o novo máximo for menor que o dano anterior, a evolução
mantém pelo menos 1 PV quando o Pokémon ainda estava consciente.
**Isto é uma adaptação explicitamente documentada**, não uma
citação de regra do manual.

Para itens especiais com exigência de equipamento ou troca nos jogos
originais, a implementação de Ankar exige uma unidade na **mochila**
e a consome durante a evolução. O mestre pode revisar essa convenção
antes de usar itens de evolução especiais. Não consome itens
desconhecidos, não usa nomes parecidos, não consome item equipado
fora da mochila e não tenta inferir um substituto.

## Implementação

- `app/services/evolucao_efetiva_service.py` implementa
  `evoluir_pokemon` com todas as pré-condições dentro de uma transação
  de banco. O serviço faz `flush` mas não `commit`; o endpoint
  comita apenas quando a operação inteira conclui.
- `app/services/materiais_evolucao_service.py` contém aliases
  explícitos de pedras comuns (10), Galarica Cuff/Wreath, Up-Grade,
  Dubious Disc, Evolution Stones e outros materiais do capítulo 16
  e códigos do CSV da PokéAPI. Itens ambíguos ou não catalogados
  interrompem o processo para revisão do mestre.
- `app/services/consulta_evolucao_service.py` expõe
  `pode_evoluir` e `bloqueio_execucao` para a UI. Mesmo se um
  cliente adulterar o HTML, **o POST repete todas as validações**.
- `app/routes/pokemons.py` recebe POST exclusivo do jogador em
  `/jogador/pokemon/<pokemon_id>/evolucoes/<relacao_id>/evoluir`.
  Utiliza perfil real, contexto de campanha e personagem da sessão,
  token CSRF e mensagem de confirmação, mas não confia em campos
  ocultos para nível, espécie, autorização ou estoque.
- `templates/jogador/pokemon.html` exibe o botão apenas quando
  os requisitos estão operacionais e um formulário de confirmação
  apartado do formulário de edição. Master permanece no painel de
  autorizações da 10E.3.2.
- `app/services/autorizacao_evolucao_service.py` permite registrar
  motivo de encerramento `Forma alterada pela evolução` na mesma
  transação, mantendo o motivo antigo para alterações manuais.

### Operação atômica

1. Validar `Usuario` ativo com perfil `jogador`, sua
   `Personagem` ativa e campanha correta; lock em personagem e
   Pokémon. O jogador só evolui **seus** Pokémon.
2. Confirmar que Pokémon **não está no Campo** (combate), forma de
   origem e destino exatos/ativos e relação permanente ativa.
3. Revalidar nível do treinador; para caminhos especiais, a
   autorização ativa correspondente ao Pokémon, à relação e à
   forma. Não usar `aprovado_mestre` como autorização.
4. Identificar material em whitelist de aliases; travar e descontar
   `PersonagemItem` do **mesmo treinador** quando preciso.
   Itens devem estar ativos e com `consumivel=True`.
5. Salvar nova `forma_pokemon_id`, recalcular via
   `calcular_pokemon` reutilizando todas as regras vigentes
   da campanha (Shiny, natureza, atributos adicionais, estilo,
   condições de status); ajustar `pv_atual` preservando dano.
6. Invalidar concessões da forma anterior, guardar
   `HistoricoAlteracao` de evolução e consumo do material e
   concluir com um único `commit`. Se qualquer passo falha,
   o endpoint faz `rollback` integral.

Preserva o mesmo `Pokemon.id`, apelido, shiny, natureza, golpes,
item equipado, anotação, posição na equipe/Box e quantidade de
Pokémon. A evolução **não ensina golpes automaticamente**.
Ações de autorizar/revogar/evoluir não são expostas no menu geral
do catálogo.

## Segurança e limitações

- Acesso só por jogador dono do Pokémon, com CSRF, contexto e
  autorização revalidados; mestre não evolui em nome do jogador
  por esta tela.
- Evoluções especiais com material não reconhecido ou catalogado
  como não consumível **não são executadas**, mesmo com autorização.
  Corrija primeiro o catálogo de itens ou o vínculo evolutivo.
- Controles de UI são informativos; a operação sempre revalida o
  estado do PostgreSQL sob locks, inclusive concorrência com
  revogação, troca de espécie e consumo de inventário.
- Sem Mega Evoluções (10E.4) e sem alterações temporárias de forma.
- **Não** alterar manualmente Pokémon de campanha, importar relações,
  aplicar migration ou mudar dados privados como parte da entrega.

## Homologação recomendada

1. Fazer backup real e testar primeiro em ambiente isolado.
2. Com um Charmander nível ≥16, abrir sua ficha como jogador,
   confirmar e verificar evolução para Charmeleon. Na ficha do
   mestre, não deve aparecer botão de evolução.
3. Com Eevee e duas Pedras da Água na mochila, evoluir para
   Vaporeon: estoque cai de 2 para 1, a ficha permanece na
   Box/equipe original, Shiny e natureza permanecem.
4. Com Eevee → Umbreon, mestre concede autorização a um
   Eevee específico; somente esse Eevee recebe o botão. Ao
   evoluir, concessões antigas ficam encerradas.
5. Testar evolução regional com condições narrativas; nível mínimo
   continua obrigatório quando documentado.
6. Simular falha de estoque; nenhuma mudança de forma ou PV.
   Pokémon em Campo não deve evoluir.
7. Conferir histórico da evolução e, quando aplicável, do
   consumo do item; verificar que não houve recarga de PV.

### Testes automatizados

```powershell
python -m pytest -q tests/test_evolucao_efetiva_10e3_3_4.py tests/test_autorizacao_evolucao_10e3_2.py tests/test_consulta_evolucao_10e3_1.py tests/test_evolucoes_regionais_10e2_5.py tests/test_equipe_pokemon.py tests/test_boxes.py tests/test_itens_inventario.py
```

Workflow dedicado:
`.github/workflows/test-evolucao-efetiva-10e3-3-4.yml`.

**Próximo:** 10E.4 Mega Evoluções e formas reversíveis, em sistema
separado do estágio permanente.
