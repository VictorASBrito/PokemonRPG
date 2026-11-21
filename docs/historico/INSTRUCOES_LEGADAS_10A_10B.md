# Instruções históricas de implantação e importação

> Documentação de etapas anteriores (10A/10B), **não executar como instalador atual**. Os originais foram consolidados e retirados da raiz; o histórico Git preserva cada versão. Consulte [README principal](../../README.md) e [arquitetura atual](../ARQUITETURA_FRONTEND.md) para operação presente.

## INSTRUCOES_10A6.txt

~~~text
POKEMON RPG — ETAPA 10A.6: VÍNCULOS E BUSCA POR POKÉMON

1. Extraia este ZIP diretamente na raiz do PokemonRPG, permitindo substituir somente os arquivos correspondentes.
2. Atualize a documentação (idempotente):
   python scripts/registrar_atlas_10a6.py
3. Confira as formas ativas no PostgreSQL (somente leitura):
   python scripts/diagnosticar_formas_ankar.py
4. Rode os testes no seu ambiente .venv:
   python -m pytest -q tests/test_ankar_10a6_vinculos.py tests/test_ankar_10a6_flask.py tests/test_ankar_10a5_mapa_fixo.py tests/test_mapa_ankar_visual.py tests/test_atlas_10a4_1_template.py tests/test_ankar_10a4.py tests/test_atlas_ankar_flask.py
5. Reinicie o Flask e recarregue /regiao/ankar com Ctrl+F5.
6. Pesquise por Corsola-G ou Corsola (Galar), abra Rota 4 e confira o card.

NÃO é necessário executar migrations, reimportar as planilhas nem substituir o banco de dados.
A documentação técnica completa está em docs/ATLAS_ANKAR_10A6.md.

LIMITES IMPORTANTES:
- Shellos (A) e (R) compartilham a única forma Shellos disponível no catálogo atual.
- Espécies com múltiplas formas sem detalhe na planilha exigem escolha do mestre.
- Verifique se a convenção E/F/G/P de Oricorio combina com sua campanha.

~~~

---

## INSTRUCOES_10B1.txt

~~~text
Pokémon RPG — Etapa 10B.1: Entrada circular de personagens

1) Extraia este ZIP na raiz do PokemonRPG, SEM apagar arquivos existentes.
2) Execute: python scripts/instalar_entrada_personagens.py
3) Liste:   python scripts/configurar_entrada_personagens.py listar
4) Configure EXATAMENTE os 9 jogadores que devem entrar sem senha:
   python scripts/configurar_entrada_personagens.py definir login1 login2 login3 login4 login5 login6 login7 login8 login9
   (ou 'auto' SOMENTE quando houver exatamente 9 jogadores elegíveis.)
5) Associe sprites slot-01.png a slot-09.png em static/img/login-personagens/.
6) Testes: python -m pytest -q tests/test_entrada_personagens.py tests/test_entrada_personagens_flask.py
7) Reinicie o Flask e acesse /login.

IMPORTANTE: qualquer visitante que abrir /login pode clicar nas 9 contas liberadas!
O acesso coringa mantém a senha para mestre e contas de teste.

Leia docs/ENTRADA_VISUAL_ANKAR.md para detalhes e segurança.

~~~

---

## INSTRUCOES_10B2.txt

~~~text
Pokémon RPG — Etapa 10B.2 (ajuste visual da tela de entrada)

1. Extraia este ZIP na raiz do projeto PokemonRPG.
2. Substitua apenas estes dois arquivos de interface:
   templates/entrada_personagens.html
   static/css/entrada-personagens.css
   (scripts/, tests/ são arquivos novos; não sobrescreva outras mudanças.)
3. Execute: python scripts/registrar_entrada_10b2.py
4. Teste: python -m pytest -q tests/test_entrada_10b2_visual.py tests/test_entrada_personagens.py tests/test_entrada_personagens_flask.py
5. Reinicie o servidor e atualize /login com Ctrl+F5.

Nenhuma configuração de slots, nome de login, sessão ou dado do banco é alterado.
O slot inferior se chama Mestre, mas mantém a rota de login tradicional e exige senha.

~~~

---

## INSTRUCOES_10B3.txt

~~~text
POKÉMON RPG — ETAPA 10B.3 — FICHAS INDEPENDENTES POR URL

INSTALAÇÃO
1. Faça backup da versão local (git status; não descarte suas alterações).
2. Extraia o ZIP na raiz do PokemonRPG, mantendo as pastas.
3. Execute:
   python scripts/instalar_fichas_por_url.py
   python -m pytest -q tests/test_fichas_por_url_10b3.py tests/test_fichas_por_url_10b3_flask.py
4. Reinicie o Flask.
5. Abra http://127.0.0.1:5000/selecionar e escolha os personagens.
6. Para ver os links configurados:
   python scripts/listar_links_fichas.py
   python scripts/listar_links_fichas.py --base https://seu-endereco

EXEMPLOS
  /p/lucas/                   → painel de lucas
  /p/mari/jogador/ficha       → ficha de mari
  /p/jao/jogador/equipe      → equipe de jao
  /p/mari/jogador/inventario  → inventário de mari
  /selecionar                 → círculo (mesmo com Mestre conectado)

Cada link tem cookie de sessão independente, com os privilégios do jogador
correspondente. O login tradicional Mestre continua isolado. Usar o botão
'Trocar personagem' retorna à seleção.

ATENÇÃO: links de jogadores são sem senha e dão acesso inclusive a alterações
na ficha pelo usuário da URL. Não compartilhe fora da mesa. Contas mestre,
administrador e tester não recebem URLs públicas por esse mecanismo.

O instalador cria backups '*.antes_10b3.bak' e é idempotente.
Não executa migrations nem altera dados do PostgreSQL, passwords ou sprites.

VALIDAÇÃO NESTE AMBIENTE: 6 testes independentes passaram; os testes de
integração Flask/SQLAlchemy precisam ser executados no computador do usuário.

DOCUMENTAÇÃO COMPLETA: docs/FICHAS_POR_URL_10B3.md

~~~

---

## INSTRUCOES_10B3_1.txt

~~~text
POKÉMON RPG — CORREÇÃO 10B.3.1 — INSTALAÇÃO DE FICHAS POR URL

SINTOMAS CORRIGIDOS
- RuntimeError: Âncora não encontrada em app/routes/auth.py
- KeyError: 'app/__init__.py' no teste de instalação (Windows)
- 404 em /p/<login>/... e /selecionar decorrentes da instalação abortada

APLICAÇÃO
1. Na raiz do PokemonRPG, extraia ESTE ZIP, substituindo os arquivos de mesma pasta.
   Não extraia dentro de uma subpasta extra.
2. Execute:
   python scripts/instalar_fichas_por_url.py
3. Execute:
   python -m pytest -q tests/test_fichas_por_url_10b3.py tests/test_fichas_por_url_10b3_flask.py
4. Reinicie o servidor Flask.
5. Abra http://127.0.0.1:5000/selecionar e dois links /p/<login>/ em abas diferentes.
6. Teste /mestre/dashboard em outra aba depois de fazer login tradicional no Mestre.

OBSERVAÇÕES
- NÃO execute novamente a configuração dos nove slots: ela é mantida.
- A alteração evita modificar app/routes/auth.py, aceitando personalizações locais.
- O botão Sair da ficha usa o cookie daquela ficha e volta a /selecionar;
  a sessão administrativa do Mestre não é afetada.
- Para inspecionar as rotas, se ainda existir 404:
    python -c "from app import create_app; a=create_app(); print(a.url_map)"
  O mapa deve mostrar /selecionar. /p/<login>/ é resolvido pelo middleware e
  não aparece como regra literal no mapa de rotas.
- O instalador mantém backup dos arquivos que muda (*.antes_10b3.bak) e é idempotente.
- Não há migration, nem escrita nas tabelas do PostgreSQL.

VALIDAÇÃO REALIZADA NESTE AMBIENTE
- 8 testes do instalador/middleware passaram.
- Flask/SQLAlchemy não disponíveis neste ambiente; testes Flask pendentes em seu PC.

~~~

---

## INSTRUCOES_10B3_2.txt

~~~text
POKÉMON RPG — ETAPA 10B.3.2 — LOGIN MESTRE / TESTE / VICTOR

SINTOMA
O slot Mestre abre GET /login/coringa. O formulário login.html, sem atributo action,
envia POST à mesma rota, que aceita apenas GET. Flask responde 405 Method Not Allowed.

CORREÇÃO
- O formulário de senha passa a enviar POST explicitamente para /login (auth.login).
- O formulário do slot Mestre pode ser aberto mesmo se houver sessão administrativa ativa.
- POST /login aceita nova autenticação; a verificação de senha existente permanece.
- Se a senha estiver incorreta, a sessão anterior não é substituída.
- As fichas em /p/<login>/, os cookies individuais e os nove slots não são alterados.

INSTALAR
1. Extraia o ZIP na raiz de PokemonRPG, preservando scripts/, tests/, docs/.
2. Com .venv ativo, execute:
       python scripts/corrigir_login_mestre_10b3_2.py
3. Teste:
       python -m pytest -q tests/test_login_mestre_10b3_2.py tests/test_login_mestre_10b3_2_flask.py
4. Reinicie o Flask e acesse /selecionar -> Mestre -> informe mestre/victor/teste.
5. Confira que os slots de jogadores /p/<login>/ ainda funcionam simultaneamente.

Instalador idempotente. Antes de mudar arquivos, valida todos os trechos e cria
backups .antes_10b3_2.bak. Mantém configuração do data/entrada_personagens.json.
NÃO exige migrations nem altera o banco, senhas ou privilégios.

VALIDAÇÃO NESTE AMBIENTE
Testes independentes do Flask serão executados aqui. Testes de integração Flask
precisam ser executados no ambiente do projeto com as dependências instaladas.

~~~

---

## RESUMO_IMPORTACAO_JOGADORES.txt

~~~text
IMPORTAÇÃO DAS NOVE FICHAS — ANKAR
=================================
Os dados foram extraídos de nove planilhas recebidas em 22/10/2026.
Nove contas preparadas, 54 Pokémon na equipe, 155 na Box, 109 linhas de inventário.
O PostgreSQL local do mestre não está acessível por esta conversa: o comando
abaixo deve ser executado no computador em que o banco está configurado.

Antes de gravar:
  flask --app app.py jogadores-planilhas importar
Para gravar:
  flask --app app.py jogadores-planilhas importar --aplicar

Logins e personagens:
  tuts  → Power
  manu  → Astrid
  braz  → Erivaldo Jr
  jao   → Juliano lima
  nanda → Bili
  lucas → Chelle
  jare  → Bartz
  vini  → Priscilla
  mari  → Claire François

Senha inicial: 12345; troca obrigatória no primeiro login.

Ajustes confirmados pelo mestre em 22/10/2026:
  - Jão: o primeiro Pokémon é Scolipede; na planilha consta "Mega?" por lore.
    Apelido "Yoda" preservado; identificação original mantida no JSON de origem.
  - Manu: números Shiny = 1, 12, 20, 26, 37, 45, 60, 80, 82, 100.
    PV preparado = 30, pois veio em branco na planilha.
  - Vini: números Shiny = 4, 75, 14, 36, 97, 5, 35, 42, 76, 17.
  - Mari: PV atual 30 mantido, como solicitado (na planilha 30/24).

Pendências para conferir na simulação:
  - Confirmar correspondências de formas, naturezas e golpes no PostgreSQL local.
  - Não é possível confirmar aqui se todos os nomes de espécies, naturezas e
    golpes correspondem ao catálogo do PostgreSQL local. A simulação os mostrará.
  - Logins/personagens que já existam no banco são preservados, sem sobrescrita.

Os scripts do Cloudflare foram mantidos sem a exigência de e-mail, conforme
solicitado. O servidor_teste.py contém a correção do nome "aplicativo".

REVISAO FINAL ANTES DA GRAVACAO:
  - Manu: Bulbasaur (Vínculo) terá forma própria no PostgreSQL ao aplicar,
    com base 70/9/9/12/11/9, tipos Grama/Veneno e imagens fornecidas.
    Os extras 236 e 6% foram preservados sem interpretação de regra.
  - Braz: 6 naturezas da Box atualizadas.
  - Nanda: 20 naturezas da Box atualizadas. Axew, Prinplup e Simipour Shiny.
  - Lucas: 12 naturezas da Box atualizadas. Corsola Shiny.
  - Vini: 12 naturezas da Box atualizadas.
  - Mari: PV atual 30, PV máximo calculado 30, sem aviso anterior.
  - Manu: PV 30 vindo de campo ausente continua sinalizado.
  - A forma Bulbasaur (Vínculo) é criada na transação da ficha de Manu,
    sem qualquer alteração na forma normal Bulbasaur.

~~~

---

