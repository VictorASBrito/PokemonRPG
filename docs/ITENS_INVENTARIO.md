# Itens e inventário no PostgreSQL

Esta etapa torna o PostgreSQL a fonte oficial para o catálogo de itens e para
todas as movimentações do inventário dos personagens.

## Funcionalidades entregues

### Catálogo administrativo de itens

O mestre pode acessar:

```text
/mestre/catalogo/itens
```

A tela permite:

- pesquisar por nome, código ou descrição;
- filtrar por categoria, situação, origem e uso;
- criar categorias durante o cadastro;
- criar, editar e duplicar itens;
- configurar preço, imagem e descrição;
- definir se o item é consumível, equipável ou utilizável em batalha;
- criar efeitos por um editor visual;
- desativar e reativar registros sem apagar vínculos antigos;
- registrar as alterações em `historico_alteracoes`.

Os efeitos são armazenados em `itens.efeitos` com estrutura versionada. Os tipos
iniciais incluem recuperação de PV, remoção de status, alteração de atributo,
dano, modificador de cálculo, evolução, Mega Evolução e efeito textual.

> O botão de uso consome a quantidade e registra os efeitos configurados no
> histórico. A execução automática de cura, dano ou status será integrada ao
> futuro assistente de combate.

### Inventário do personagem

O jogador pode acessar:

```text
/jogador/inventario
```

O mestre pode abrir o inventário de qualquer personagem da campanha por:

```text
/mestre/jogadores/<personagem_id>/inventario
```

A tela permite:

- pesquisar e filtrar os itens possuídos;
- consultar quantidades e efeitos;
- consumir itens marcados como consumíveis;
- entregar um item equipável a um Pokémon;
- devolver um item carregado ao inventário;
- trocar o item carregado, devolvendo automaticamente o anterior;
- transferir unidades para outro personagem da mesma campanha;
- adicionar itens e ajustar quantidades quando o acesso é do mestre.

As operações usam bloqueio de linha durante mudanças de quantidade e impedem:

- quantidades negativas;
- consumo acima da quantidade disponível;
- transferência para o próprio personagem;
- transferência entre campanhas diferentes;
- equipamento de item inativo ou não equipável;
- acesso do mestre a personagens de outra campanha.

## Mudança importante nas fichas

O inventário não é mais editado como texto livre na ficha do personagem. A
ficha apresenta um resumo e um link para a tela oficial do inventário.

O item carregado também não é alterado diretamente na ficha do Pokémon. Isso
evita criar ou remover unidades sem movimentar `personagem_itens`.

O fluxo oficial é:

```text
Inventário → escolher item → escolher Pokémon → equipar
```

Ao desequipar, uma unidade volta ao inventário. Ao substituir o item, o item
anterior também retorna automaticamente.

## Migration

Esta versão adiciona:

```text
d94c7ab20e51_catalogo_itens_e_inventario.py
```

Ela inclui em `itens`:

```text
preco
consumivel
equipavel
uso_em_batalha
```

A migration também marca como equipáveis os itens que já estavam carregados por
Pokémon antes da atualização.

Aplique com:

```powershell
flask --app app.py db upgrade
```

Confira:

```powershell
flask --app app.py db current
```

Resultado esperado:

```text
d94c7ab20e51 (head)
```

Não execute novamente a importação dos JSON.

## Diagnósticos

Valide o catálogo:

```powershell
flask --app app.py catalogo verificar
```

O resultado deve incluir:

```text
Catálogo de itens está consistente no PostgreSQL.
```

Valide os inventários:

```powershell
flask --app app.py inventario verificar
```

Resultado esperado:

```text
Itens, inventários e equipamentos estão consistentes no PostgreSQL.
```

O diagnóstico verifica preços negativos, quantidades inválidas, referências
órfãs e Pokémon carregando itens que não estão marcados como equipáveis.

## Teste manual recomendado

1. Entre como mestre e abra **Catálogo → Itens**.
2. Crie um item consumível com preço e efeito de recuperação de PV.
3. Crie ou edite um item equipável.
4. Abra o inventário de um jogador.
5. Adicione três unidades do item consumível.
6. Consuma uma unidade e confirme a nova quantidade.
7. Adicione uma unidade do item equipável.
8. Entregue o item a um Pokémon e confirme que ele saiu do inventário.
9. Retire o item do Pokémon e confirme que ele retornou.
10. Transfira uma unidade para outro personagem da campanha.
11. Atualize a página e reinicie o servidor para validar a persistência.
12. Abra a ficha do personagem e do Pokémon para confirmar que ambas exibem o
    estado atualizado sem permitir alterações paralelas.

## Tabelas principais

```text
categorias_item
itens
personagem_itens
pokemons
personagens
historico_alteracoes
```

## Revisão incremental do cadastro — 23/10/2026

- No salvamento do catálogo, o backend passa a rejeitar preço não inteiro, negativo ou acima de 999.999.999 Pokédolares, mantendo preço em branco como zero.
- Se todos os efeitos forem removidos durante a edição, uma falha de validação em outro campo não deve repor os efeitos antigos no editor. O banco segue inalterado até um envio válido.
- Os cenários de regressão estão em `tests/test_itens_inventario.py` e **ainda precisam de execução integrada em ambiente com Flask instalado**.
- Nenhuma migration foi adicionada. Esta revisão não altera itens já existentes nem corrige inconsistências armazenadas no banco de produção.
