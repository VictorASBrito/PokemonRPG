# Correção da restrição do perfil Tester no PostgreSQL

O erro `psycopg.errors.CheckViolation: ck_usuarios_perfil_valido` indica que a CHECK
**real** do banco ainda permite apenas `administrador`, `mestre` e `jogador`.
Os modelos e serviços Python já permitem `tester`, mas o banco bloqueia o UPDATE.

## Aplicação recomendada

1. Encerre o servidor e o Cloudflare Tunnel temporariamente.
2. Faça um backup do PostgreSQL. Preserve também `.env` e `static/uploads/`.
3. Atualize o código e abra o terminal na pasta do projeto.
4. Execute:

```powershell
flask --app app.py db current
flask --app app.py db heads
flask --app app.py db upgrade
flask --app app.py db current
flask --app app.py usuarios verificar
```

A revisão esperada é `b72cf044e6ad (head)`.

A nova migração é transacional e corrige a CHECK. Ela não modifica contas,
nomes, senhas, personagens nem Pokémon; também não muda perfis existentes.

### Conferir no DBeaver

```sql
SELECT conname, pg_get_constraintdef(oid) AS definicao
FROM pg_constraint
WHERE conrelid = 'usuarios'::regclass AND contype = 'c';
```

Para `ck_usuarios_perfil_valido`, a definição deve mencionar
`'administrador'`, `'mestre'`, `'tester'` e `'jogador'`.

Depois, teste mudar **uma conta de teste** de Jogador para Tester pela tela de
permissões. Confira o perfil sem expor hashes de senha:

```sql
SELECT login, nome, perfil, ativo FROM usuarios ORDER BY login;
```

**Não** execute `flask db stamp` para fingir que a revisão foi aplicada.
Não exclua e não recrie a tabela `usuarios`.

Se o `db upgrade` reportar que já está em `b72cf044e6ad`, mas a CHECK
continua antiga, houve deriva adicional do esquema. Não use `stamp` nem
execute alterações aleatórias: confira o resultado da consulta no DBeaver.
