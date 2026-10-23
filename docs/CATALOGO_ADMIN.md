# Painel administrativo de espécies e formas Pokémon

Esta etapa permite administrar espécies e formas diretamente no PostgreSQL.
Os arquivos JSON não são consultados pelas telas do catálogo.

## Funcionalidades

- painel de resumo do catálogo;
- pesquisa por nome, espécie ou código;
- filtros por categoria, tipo e situação;
- criação de uma forma para uma espécie existente;
- criação de espécie personalizada com sua forma inicial;
- edição de espécie e forma;
- tipos primário e secundário;
- atributos base dinâmicos, conforme a tabela `atributos`;
- imagens normal e Shiny;
- duplicação de formas como registros inativos;
- desativação lógica e reativação;
- prévia de atributos por nível, Shiny, natureza e estilo de combate;
- auditoria em `historico_alteracoes`.

## Rotas

```text
/mestre/catalogo
/mestre/catalogo/pokemons
/mestre/catalogo/pokemons/novo
/mestre/catalogo/pokemons/<id>/editar
```

Somente usuários com perfil de mestre ou administrador podem acessar essas rotas.

## Aplicação

Não existe migration nova nesta etapa. Mantenha o `.env` da sua instalação e
execute:

```powershell
pip install -r requirements.txt
flask --app app.py db current
flask --app app.py catalogo verificar
python app.py
```

A revisão esperada continua sendo:

```text
d94c7ab20e51 (head)
```

## Teste manual sugerido

1. Entre como mestre.
2. Acesse **Catálogo** no menu superior.
3. Pesquise uma forma já importada.
4. Edite uma imagem ou atributo base e salve.
5. Atualize a página e confirme a persistência.
6. Crie uma espécie personalizada e sua primeira forma.
7. Use a prévia em um nível qualquer, com e sem Shiny.
8. Duplique a forma e confirme que a cópia nasce inativa.
9. Reative ou desative a forma pela interface.
10. Confira `historico_alteracoes` no DBeaver.

## Observações

- Desativar uma forma não remove Pokémon existentes que já a utilizam.
- Formas inativas deixam de aparecer nos cadastros normais de novos Pokémon.
- Alterações nos atributos base afetam imediatamente os cálculos de todas as
  fichas ligadas à forma.
- A edição de uma espécie afeta todas as formas vinculadas a ela.


## Continuação do catálogo

O gerenciamento de golpes, o editor visual de efeitos e os vínculos com formas
Pokémon estão documentados em `CATALOGO_GOLPES.md`.


> Na versão consolidada do projeto, a revisão atual é `d94c7ab20e51` por causa do módulo posterior de itens e inventário. Consulte `ITENS_INVENTARIO.md`.
