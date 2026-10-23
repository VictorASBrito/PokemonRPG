# Importação inicial para o PostgreSQL

Esta etapa transfere os catálogos e os dados atuais da campanha para o banco.
As telas ainda continuam usando JSON até a próxima fase.

## 1. Faça um backup do banco

No DBeaver, use **Ferramentas → Backup** no banco `pokemon_rpg`.

## 2. Analise as fontes

```powershell
flask --app app.py dados analisar
```

Na base entregue, o resultado esperado é aproximadamente:

```text
Usuários: 1
Campanhas: 1
Jogadores: 0
Pokémon dos jogadores: 0
Formas Pokémon: 1064
Golpes: 687
Tipos: 19
Categorias de golpe: 3
Naturezas: 25
Status: 11
Atributos: 12
```

As quantidades de jogadores e Pokémon dependerão das fichas já cadastradas em
`data/campanhas/<campanha>/jogadores`.

## 3. Simule a carga

```powershell
flask --app app.py dados importar --dry-run
```

O comando executa os inserts e updates dentro de uma transação, valida as
restrições e executa rollback ao final. Nenhum registro permanece no banco.

## 4. Importe de verdade

```powershell
flask --app app.py dados importar
```

A importação é idempotente. Executá-la novamente atualiza os mesmos registros,
sem duplicá-los. Um relatório JSON é criado em `logs/`.

## 5. Valide

```powershell
flask --app app.py dados validar
```

Também é possível executar `scripts/validar_importacao.sql` pelo DBeaver.

## Observações

- Os 1064 registros do catálogo atual são importados como **formas Pokémon**.
- Formas com o mesmo nome-base são agrupadas em uma única espécie. Por exemplo,
  Charizard, Charizard Mega X e Charizard Mega Y pertencem à espécie Charizard.
- O catálogo atual não contém o relacionamento completo de golpes aprendidos
  por espécie. Por isso, `forma_pokemon_golpes` permanecerá vazia nesta carga.
  Esse relacionamento poderá ser importado da planilha ou administrado pelas
  futuras telas do mestre.
- Os JSON continuam sendo preservados como backup e fonte de comparação até a
  conversão das rotas para o PostgreSQL.
