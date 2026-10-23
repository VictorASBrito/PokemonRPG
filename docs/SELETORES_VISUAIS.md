# Listas de seleção com imagens e informações

Esta etapa moderniza **as listas de escolha de objetos**, antes exibidas como `datalist` do navegador. O redesenho amplo do inventário ficará para a próxima etapa.

## Telas incluídas

- Criar Pokémon na Box: busca dinâmica com sprite, nome, categoria da forma e etiquetas de tipos.
- Editar Pokémon (Admin/Tester): seleção de forma no mesmo componente.
- Editar golpes do Pokémon: tipo colorido, nome, categoria e expressão de dano. Golpes não têm imagem no banco: recebem um símbolo tipado no lugar da miniatura.
- Mestre > Inventário > Adicionar item: miniatura (upload/URL), nome, categoria e sinalização consumível/equipável.
- Mestre > Catálogo > Golpes > Vínculos: miniaturas e tags dos tipos para escolher formas.

## Comportamento

- Digitar inicia pesquisa no PostgreSQL com espera breve (200 ms); no máximo 20 resultados por consulta.
- Setas para navegar, `Enter` para escolher, `Esc` para fechar; clique também seleciona.
- Resultado vazio, erro de rede e carregamento têm indicação textual.
- Item adicionado ao inventário só envia `item_id` se a seleção foi confirmada numa opção real. Não permite inventar ID com texto livre.
- O código original e os valores dos formulários continuam compatíveis com os serviços existentes.
- Todos os textos de resultados são inseridos com `textContent`, evitando interpretar nomes cadastrados como HTML.
- Combobox e painel usam os tokens CSS de tema claro e escuro. Em telas pequenas, reposicionam a lista acima do input quando necessário.

## Arquivos principais

- `app/services/pokemon_db_service.py`: respostas de busca enriquecidas e busca de itens.
- `app/routes/pokemons.py`: nova rota GET `/api/catalogo/itens` exclusiva do mestre.
- `static/js/autocomplete-catalogo.js`: seletor visual compartilhado.
- `static/css/seletor-visual.css`: miniaturas, estados e acessibilidade.
- `templates/jogador/novo_pokemon.html`, `templates/jogador/pokemon.html`, `templates/jogador/inventario.html`, `templates/mestre/catalogo/golpe_vinculos.html`.

## Instalação

Preservar `.env`, `data/` e `static/uploads/`. **Não há migration.**

Para testar:

```powershell
pytest -q tests/test_seletores_visuais.py tests/test_pesquisas_dinamicas.py tests/test_itens_inventario.py tests/test_golpes_admin.py
python servidor_teste.py
```

Atualizar a página com Ctrl+F5 para forçar a atualização de JS/CSS.
