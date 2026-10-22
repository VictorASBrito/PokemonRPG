# Compartilhar o Pokémon RPG com jogadores — Cloudflare Tunnel

Esta integração foi feita para **testes temporários com jogadores convidados**, usando a
versão do projeto com PostgreSQL. A máquina do mestre hospeda o aplicativo; os jogadores
não instalam Python, PostgreSQL nem `cloudflared`.

## Pré-requisitos

- PostgreSQL funcionando na máquina do mestre, com os usuários/jogadores já cadastrados.
- Python e `.venv` do projeto preparados (`pip install -r requirements.txt`).
- `.env` com `DATABASE_URL` válido e `POKEMON_RPG_SECRET_KEY` aleatória com **pelo menos 32 caracteres**.
- Instale a versão atual do `cloudflared` para Windows, pelo [download oficial](https://developers.cloudflare.com/tunnel/downloads/).
  Depois confira: `cloudflared --version`.
- Para usar a proteção por e-mail, a versão do `cloudflared` deve suportar `--allowed-mail`
  (funcionalidade lançada pela Cloudflare em outubro de 2026).

Não é necessário redirecionar portas no roteador, comprar domínio nem criar conta
Cloudflare para este teste rápido.

## 1 — Instalar as dependências do projeto

No PowerShell, na pasta raiz do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Não execute `python app.py` para publicar o site.** O modo habitual do Flask é
destinado ao uso local. A integração usa o Waitress sem debugger e ouvindo apenas em
`127.0.0.1`, impedindo acesso direto da rede ao servidor.

## 2 — Iniciar o servidor local (terminal 1)

```powershell
.\scripts\1_servidor_teste.ps1
```

O script inicia `python servidor_teste.py`. Acesse
`http://127.0.0.1:5000/login` somente para confirmar se o servidor subiu.
**Importante:** o modo de testes configura cookies como `Secure`. Portanto, para
fazer login, use a URL **HTTPS do túnel** (não o endereço `http://127.0.0.1`).

Se o PowerShell bloquear `.ps1`, use, apenas para esta execução:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\1_servidor_teste.ps1
```

## 3 — Iniciar o túnel (terminal 2)

```powershell
.\scripts\2_tunel_cloudflare.ps1 -Emails "jogador1@exemplo.com","jogador2@exemplo.com"
```

Insira os **endereços reais dos jogadores**. O script exige pelo menos um e-mail e
usa `--allowed-mail` para mandar código de verificação para cada visitante.
É uma proteção adicional à autenticação normal do Pokémon RPG.

Se o PowerShell bloquear scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\2_tunel_cloudflare.ps1 -Emails "jogador1@exemplo.com","jogador2@exemplo.com"
```

O terminal do túnel mostrará um endereço similar a:

```
https://palavras-aleatorias.trycloudflare.com
```

**Este é apenas um exemplo**: o endereço real é criado pela Cloudflare e muda
quando o túnel é reiniciado. Envie o endereço aos jogadores autorizados. Eles
serão solicitados a verificar o e-mail e depois poderão fazer login normalmente
com seus **usuários de jogador** do RPG.

Se não encontrar o comando `cloudflared`, instale-o e reabra o terminal; como
alternativa, coloque `cloudflared.exe` na raiz do projeto (não o inclua no Git).

## 4 — Encerramento e disponibilidade

- Mantenha abertos os dois terminais e o computador ligado e com internet.
- Ctrl+C no terminal 2 interrompe a publicação e **invalida a URL**.
- Ctrl+C no terminal 1 encerra o servidor local.
- O banco de dados e os arquivos de imagens permanecem na máquina do mestre.
- Os jogadores só precisam de navegador e das credenciais do aplicativo.
- O túnel não garante funcionamento ininterrupto; é uma ferramenta de testes.

## Segurança e boas práticas

1. Faça backup do **PostgreSQL** e de `static/uploads/` antes de convidar usuários.
2. Nunca exponha o debugger Flask. Utilize `servidor_teste.py` (Waitress).
3. Use senhas individuais para jogadores e contas de mestre; **não compartilhe** a senha do mestre.
4. Configure a variável `POKEMON_RPG_SECRET_KEY` longa, aleatória e privada.
5. O teste é restrito por **e-mail no Cloudflare** e por **login no site**. Não compartilhe o link publicamente.
6. Esta não é uma implantação pronta para produção: falta uma revisão abrangente de CSRF,
   rate limiting de login, permissões e backups automatizados. Mantenha o piloto com
   poucos usuários de confiança até que essas melhorias sejam feitas.
7. Cookies de sessão são `Secure`, `HttpOnly`, `SameSite=Lax` no servidor de teste.
8. Se migrar para um túnel com domínio próprio, inclua-o em
   `POKEMON_RPG_HOSTS_ADICIONAIS=teste.seudominio.com` no `.env`.

## Problemas comuns

- **Conexão recusada pelo túnel:** primeiro verifique o terminal 1 e PostgreSQL.
- **Erro 502:** o processo Waitress não está rodando ou não escuta em 127.0.0.1:5000.
- **`--allowed-mail` desconhecido:** atualize o `cloudflared`.
- **Login não persiste em localhost:** cookies seguros exigem HTTPS; use a URL do túnel.
- **Erro 400 de host inválido:** confira se está usando um subdomínio `trycloudflare.com`;
  domínios próprios exigem `POKEMON_RPG_HOSTS_ADICIONAIS`.
- **Link mudou:** Quick Tunnels têm endereços aleatórios a cada execução.

Documentação oficial: <https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/>.
