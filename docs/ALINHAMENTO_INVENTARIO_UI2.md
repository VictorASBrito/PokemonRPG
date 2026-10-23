# Pokémon RPG — Inventário UI2: alinhamento das colunas

Esta atualização refina exclusivamente a disposição horizontal do inventário, conforme o exemplo do painel enviado.

## Alterações

- `Voltar` posicionado à direita do contêiner da mochila.
- O resumo `Bolsa ativa` usa exatamente a largura do cartão de pesquisa/listagem.
- O contador `Itens nesta bolsa` ocupa a mesma largura do cartão de detalhes e tem a mesma altura do resumo da bolsa.
- O divisor vertical entre os dois resumos coincide com o espaço entre as colunas inferiores.
- O layout mantém a rolagem interna do inventário e se adapta a telas menores.

A atualização **não altera rotas, serviços de inventário ou o banco PostgreSQL**; a única alteração no código Python é a versão visual enviada no cabeçalho da resposta HTTP.

## Aplicar ao projeto existente

Extraia o pacote fora da pasta onde está seu projeto de verdade. No PowerShell, abra a pasta `PokemonRPG` extraída e execute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\INSTALAR_ALINHAMENTO_INVENTARIO_UI2.ps1 -Destino "C:\Users\Victor\Desktop\Projetos\PokemonRPG"
```

O instalador substitui apenas `static/css/inventario.css` e `app/services/inventario_apresentacao.py`; cria backup dos arquivos anteriores e preserva `data/`, `.env`, `static/uploads/` e os dados PostgreSQL.

Reinicie o servidor e atualize o navegador com **Ctrl+F5**.

Para confirmar a versão utilizada, abra as ferramentas do navegador, guia **Rede/Network**, solicite novamente o inventário e observe o cabeçalho:

`X-PokemonRPG-Inventario: ui2-alinhamento-inventario-20261023`

## Validação realizada

O CSS foi inspecionado no Chromium com uma renderização de teste da estrutura real do HTML em quatro resoluções: 1718×900, 1440×900, 1024×768 e 390×844. Nos três layouts em duas colunas, foi validado que as extremidades dos resumos coincidem com as dos cartões inferiores e que `Voltar` termina à direita do painel. A navegação do aplicativo real e os dados no PostgreSQL não foram testados neste ambiente.
