# 10B.3.2 — Correção do acesso tradicional do Mestre

## Problema

O acesso visual ao slot **Mestre** utiliza `GET /login/coringa` para mostrar
`templates/login.html`. Esse template estava com `<form method="post">`, sem
`action`. Navegadores enviam POST para a URL atual (`/login/coringa`), enquanto
a rota `entrada_personagens.coringa` só aceita GET. Resultado: HTTP 405.

## Alteração isolada

- `templates/login.html`: formulário envia para `url_for('auth.login')`.
- `app/routes/entrada_personagens.py`: GET do coringa não rejeita sessão ativa;
  pode mostrar login para trocar entre Mestre, teste e contas alternativas.
- `app/routes/auth.py`: a guarda de sessão existente é aplicada só em GET,
  permitindo que POST valide as credenciais e substitua a sessão administrativa
  antiga apenas depois de autenticação bem-sucedida.

**Não foi alterada a verificação de senha, permissões do mestre, dados de
usuários, nem as URLs `/p/<login>/` dos nove jogadores.** A sessão administrativa
tradicional segue sendo uma por navegador; as fichas via URL são independentes.

## Testes

```powershell
python scripts/corrigir_login_mestre_10b3_2.py
python -m pytest -q tests/test_login_mestre_10b3_2.py tests/test_login_mestre_10b3_2_flask.py
```

Teste manual: `/selecionar` → Mestre → informar credenciais da conta Mestre,
Victor ou teste. Depois verifique a troca de conta a partir de `/selecionar`
com uma sessão administrativa já existente e o funcionamento simultâneo das
fichas `/p/<login>/`.

Não há migrations, importações nem mutações de senhas. O instalador altera
somente os três arquivos descritos e acrescenta histórico, quando disponível.
