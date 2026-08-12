# Painel geral do mestre e pesquisas dinâmicas

## Painel

O endereço `/mestre/dashboard` concentra a visão operacional da sessão. Cada jogador apresenta PV, nível, Pokédolares, quantidade de Pokémon na Box e equipe ativa. Os Pokémon exibem imagem, tipos, PV, status e item carregado.

A pesquisa no topo é local e instantânea. Ela procura por jogador, treinador, classe, origem, apelido e espécie dos Pokémon da equipe. O filtro **Com alertas** mostra apenas personagens com acesso desativado, PV baixo ou Pokémon com PV baixo/status ativo.

## Ajuste rápido de PV

Treinadores e Pokémon possuem botões `-10`, `-5`, `+5` e `+10`. A alteração é enviada ao PostgreSQL sem recarregar a página e é registrada em `historico_alteracoes` com a ação `ajustar_pv_painel`.

- treinador: limitado entre `-PV máximo` e `PV máximo`;
- Pokémon: limitado entre `0` e `PV máximo`.

## Pesquisas do catálogo

As listagens administrativas de Pokémon, golpes e itens, além da busca de formas para vínculos de golpes, usam `static/js/pesquisa-dinamica.js`. O formulário continua funcionando normalmente sem JavaScript, mas com JavaScript ativo os resultados e a paginação são atualizados por `fetch`.

## Autocomplete de Pokémon e golpes

As fichas consultam:

```text
/api/catalogo/formas?q=...
/api/catalogo/golpes?q=...
```

Os endpoints exigem login e retornam no máximo 20 correspondências. Isso evita inserir todo o catálogo no HTML de cada ficha.

## Aplicação

Não existe migration nova nesta etapa. Depois de atualizar os arquivos:

```powershell
flask --app app.py db current
pytest -q
python app.py
```

A revisão esperada do banco continua `d94c7ab20e51 (head)`.
