# Níveis de acesso — Pokémon RPG

## Admin / Mestre (existente)
Mantém acesso administrativo do sistema, catálogos, contas, painéis e
inventários. Pode criar Pokémon nas Boxes de jogadores e conceder/ajustar itens.
Os perfis originais `administrador` e `mestre` continuam válidos sem mudanças.

## Tester (novo)
Acessa as mesmas telas pessoais de Jogador. Pode criar Pokémon **apenas em espaços
vazios de sua própria Box** (até 100), além de gerenciar equipe, editar **todos os campos** (inclusive espécie, gênero, natureza e Shiny) e remover
os próprios Pokémon. **Não pode criar, conceder ou ajustar quantidades de itens**.

## Jogador
Acessa suas fichas, equipe, Box, inventário e ações regulares de movimentação,
uso, equipamento e transferência de itens possuídos. Não pode criar Pokémon ou
gerar itens; também não pode alterar espécie/forma, gênero, natureza ou Shiny dos seus Pokémon.
Espaços vazios da Box são apenas informativos.

## Gerenciar os níveis
Mestre: `Jogadores → Permissões → Jogador/Tester → Salvar perfil`.
Também é possível escolher o nível ao criar jogador. A importação das nove
fichas continua criando contas `jogador` por padrão, sem direitos extras.

As rotas de criação e geração consultam o perfil **atual do PostgreSQL**,
independentemente da sessão, para bloquear envios diretos e aplicar revogações
sem exigir novo login. A troca de perfil é auditada.

## Migração

```powershell
flask --app app.py db upgrade
flask --app app.py db current
```

Revisão esperada: `3a8e5c71d902 (head)`.

Antes de expor a aplicação pelo Cloudflare, faça backup do PostgreSQL e
`static/uploads/`. A permissão de criação não elimina a necessidade de
proteções de CSRF, controle de sessões e testes contra acesso indevido.
