# Painel geral do mestre e ordem da sessão

## Painel

O endereço `/mestre/dashboard` concentra a visão operacional da sessão. Cada jogador apresenta PV, Pokédolares, atributos do personagem, alertas e a equipe ativa.

A pesquisa no topo é local e instantânea. Ela procura por jogador, treinador, classe, origem, apelido e espécie dos Pokémon da equipe. O filtro **Com alertas** mostra apenas personagens com acesso desativado, PV baixo ou Pokémon com PV baixo/status ativo.

## Ordem manual da sessão

A primeira etapa do assistente de combate é propositalmente manual. O mestre usa **Definir ordem** para organizar a sequência em que os jogadores aparecem no painel.

- é possível arrastar os cartões;
- também existem setas para mover para cima/baixo;
- a ordem é salva automaticamente no PostgreSQL;
- ao recarregar ou entrar novamente no painel, a sequência permanece;
- nenhum cálculo de iniciativa ou turno é feito automaticamente.

A ordem é gravada em `personagens.ordem_painel` e alterações são registradas em `historico_alteracoes` com a ação `reordenar_painel`.

## Atributos do personagem

O resumo ao lado dos PV deixa de mostrar contadores de equipe/Box/acesso e passa a mostrar os atributos ativos do personagem, respeitando a ordem definida no catálogo de atributos.

## Prévia do jogador

O nome/avatar do jogador e o botão **Prévia do jogador** abrem:

```text
/mestre/jogadores/<personagem_id>/preview
```

A prévia usa o mesmo template `jogador/dashboard.html` utilizado pela conta do jogador. Uma faixa identifica que o mestre está em modo de visualização e os links são redirecionados para equivalentes seguros do mestre.

## Botões Voltar

Quando o mestre abre ficha, equipe, Box ou inventário de um jogador, o botão **Voltar** retorna para `/mestre/dashboard` em vez da listagem `/mestre/jogadores`.

## Ajuste rápido de PV

Treinadores e Pokémon continuam com botões `-10`, `-5`, `+5` e `+10`. A alteração é enviada ao PostgreSQL sem recarregar a página e é registrada em `historico_alteracoes` com a ação `ajustar_pv_painel`.

- treinador: limitado entre `-PV máximo` e `PV máximo`;
- Pokémon: limitado entre `0` e `PV máximo`.

## Migration

Esta etapa adiciona:

```text
e6b19d2a4c73_ordem_jogadores_painel_mestre.py
```

Aplique com:

```powershell
flask --app app.py db upgrade
flask --app app.py db current
```

A revisão esperada é:

```text
e6b19d2a4c73 (head)
```

## Testes

```powershell
pytest -q
```

A suíte desta versão possui 46 testes automatizados.
