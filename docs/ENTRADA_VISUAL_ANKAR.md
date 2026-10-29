# Etapa 10B.1 — Entrada visual de Ankar

## Objetivo

Substituir a entrada inicial por **nove personagens em círculo** e um **décimo slot coringa na parte inferior**. O coringa abre o login atual com usuário/senha para mestre, administrador e contas de teste. As páginas, permissões e sessões existentes não foram reformuladas.

## Instalação

1. Extraia o ZIP incremental preservando as pastas na raiz do projeto.
2. Execute `python scripts/instalar_entrada_personagens.py` (idempotente; cria backups dos três arquivos existentes antes de editá-los).
3. Execute `python scripts/configurar_entrada_personagens.py listar` para ver as contas de **jogadores comuns** elegíveis na campanha.
4. Se forem exatamente nove e você tiver confirmado os nomes, execute `python scripts/configurar_entrada_personagens.py auto`. Caso contrário, execute `python scripts/configurar_entrada_personagens.py definir LOGIN1 LOGIN2 LOGIN3 LOGIN4 LOGIN5 LOGIN6 LOGIN7 LOGIN8 LOGIN9`, substituindo pelos nove logins desejados na ordem do círculo. **Não inclua sua conta de teste `victor`**; mestre e tester são automaticamente bloqueados, mas uma conta de teste com perfil `jogador` precisará ser excluída manualmente.
5. As **nove sprites enviadas** estão incluídas em `static/img/login-personagens/slot-01.png` até `slot-09.png`, na ordem do envio. Confirme se a ordem escolhida na configuração corresponde a cada imagem. Se alguma sprite local não estiver disponível, a página tenta a foto já cadastrada (`personagens.foto_url`); se não houver, mostra a inicial do nome.
6. Reinicie Flask e abra `/` (redireciona para `/login`) ou `/login`. `Ctrl+F5` atualiza o CSS.

O arquivo de configuração criado é **`data/entrada_personagens.json`** (não incluído como configuração ativa no ZIP e não deve ser sobrescrito em atualizações). Para mudar a ordem, edite seus nove registros ou execute `definir ... --substituir`, que cria backup.

## Segurança — decisão consciente

**Senha zero implica identificação sem autenticação forte:** qualquer visitante com acesso ao endereço do site consegue entrar como qualquer personagem configurado, ver e alterar dados que o jogador poderia alterar. Este é o comportamento solicitado para a mesa, porém não protege os dados dos jogadores em um endereço público. Para publicação na internet, considere uma proteção externa para restringir acesso ao grupo de jogadores (por exemplo, um login de acesso compartilhado ou um serviço de identidade na borda); a aplicação sozinha **não** verifica a identidade da pessoa clicando na sprite.

Guardas técnicas implementadas:
- Nenhuma conta é habilitada automaticamente: exige configuração explícita com exatamente nove logins diferentes.
- A rota POST aceita apenas números 1–9 e exige token CSRF vinculado à sessão.
- Reconsulta PostgreSQL a cada POST: usuário e personagem ativos, campanha ativa, vínculo com papel `jogador`, perfil `jogador` exato. Perfis `mestre`, `administrador` e `tester` não funcionam na entrada direta nem se incluídos manualmente no JSON.
- Mantém os mesmos campos de sessão do login anterior; não cria privilégios novos. Sessão de acesso visual não mostra ação de alterar senha, mas a rota tradicional não é removida.
- Curinga continua com senha; erros do formulário de senha não são silenciosamente convertidos em entrada direta.
- Não introduz tabelas, migrations ou alterações automáticas no banco.

## Testes sugeridos

```powershell
python -m pytest -q tests/test_entrada_personagens.py tests/test_entrada_personagens_flask.py
```

Validação manual recomendada: `/login` exibe os nove personagens; clicar em cada um abre a ficha correspondente; o coringa abre usuário/senha; tentar selecionar número 10, CSRF inválido ou login de mestre/tester é rejeitado; trocar usuário e sair encerra a sessão; layout permanece utilizável em celular, tablet e desktop.
