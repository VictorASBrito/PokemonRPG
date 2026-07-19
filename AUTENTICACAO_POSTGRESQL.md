# Autenticação e usuários no PostgreSQL

Nesta etapa, o PostgreSQL passou a ser a fonte oficial para:

- login e validação de senha;
- situação ativa ou inativa do usuário;
- perfil de mestre, administrador ou jogador;
- vínculo com a campanha;
- cadastro de novos acessos;
- criação inicial do personagem;
- listagem dos jogadores no painel do mestre.

## Compatibilidade temporária

Ficha, Pokémon e Box ainda usam os serviços JSON. Por isso, durante o cadastro de
um jogador, o sistema cria também os arquivos temporários necessários para as
telas antigas.

O JSON não é consultado para validar login em execução normal. Ele será removido
do fluxo quando as próximas telas forem convertidas para o PostgreSQL.

## Verificação

Execute:

```powershell
flask --app app.py usuarios verificar
```

O comando valida:

- campanha configurada;
- quantidade de usuários;
- usuários ativos;
- membros da campanha;
- personagens ativos;
- jogadores sem personagem vinculado.

## Teste manual

1. Saia de qualquer sessão antiga.
2. Entre com o mestre importado.
3. Abra **Jogadores** e confirme que a fonte exibida é PostgreSQL.
4. Cadastre um novo jogador.
5. Saia da conta do mestre.
6. Entre com o novo jogador.
7. Confirme que o dashboard atual ainda abre por meio da ponte temporária.
8. Desative o acesso pelo painel do mestre e confirme que o login é bloqueado.

## Nenhuma migration nova

Esta etapa usa somente as tabelas já criadas pela migration inicial. Não execute
`flask db migrate` nem `flask db upgrade` apenas por causa desta atualização.
