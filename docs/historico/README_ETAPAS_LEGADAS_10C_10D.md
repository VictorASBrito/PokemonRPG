# Guias legados das etapas 10C e 10D

> Registro histórico do desenvolvimento. Estes READMEs de versão foram reunidos para deixar a raiz limpa, sem descartar decisões passadas. Para executar a versão atual, use [README.md](../../README.md).

## README_10C3.txt

~~~text
ETAPA 10C.3 — RECONSTRUÇÃO CONTROLADA DO CATÁLOGO E CURA FUNCIONAL
Base: PokémonRPG commit 5a544230641dcdade27c37c89dc3af206454ad2d (Imagens Itens 1)

1. Extraia este ZIP na raiz do PokemonRPG. Não substitua .env, static/uploads ou JSON de jogadores.
2. python scripts/instalar_itens_10c3.py
3. python scripts/registrar_documentacao_itens_10c3.py
4. python -m pytest -q tests/test_itens_10c3_puro.py tests/test_itens_10c3_flask.py tests/test_itens_inventario.py
5. python scripts/reconstruir_catalogo_10c3.py --descartar-naturezas
   SOMENTE SIMULAÇÃO: leia relatorios/catalogo_10c3/simulacao.json
6. Faça backup completo PostgreSQL (pg_dump -Fc) e tire todos os jogadores do site.
7. APENAS APÓS APROVAR O PLANO:
   python scripts/reconstruir_catalogo_10c3.py --aplicar --confirmar RECONSTRUIR-ANKAR --descartar-naturezas
8. flask --app app.py inventario verificar
   flask --app app.py catalogo auditar-itens --todos

AVISO: --aplicar recria registros no PostgreSQL, com novos IDs. Não execute sem backup PostgreSQL.
- A flag --descartar-naturezas permite descartar especificamente uma unidade do falso item Ingênuo, registrada no relatório.
- Nenhum item é adicionado aos jogadores automaticamente; o Mapa de Ankar é criado somente no catálogo.
- O serviço de uso terapêutico realmente recupera PV ou remove condições Pokémon, sem ultrapassar o PV máximo, selecionando o alvo e consumindo o item na mesma transação.
- A Poção usa 20 PV como ponto inicial, editável no catálogo. Elixir não é automático (PP não gerenciado no RPG).
- Reaproveita imagens já existentes do commit Imagens Itens 1; não as duplica.
- Sem migrations.

LEIA A DOCUMENTAÇÃO COMPLETA: docs/ETAPA_10C3_RECONSTRUCAO_CATALOGO.md

~~~

---

## README_10C4.txt

~~~text
ETAPA 10C.4 — USAR NA LISTA, SELECIONAR POKÉMON NA EQUIPE

Base: commit e392239a (main), posterior à Etapa 10C.3.

1. Extraia este ZIP na pasta raiz do PokemonRPG, preservando as pastas.
2. python scripts/instalar_inventario_10c4.py
3. python scripts/registrar_documentacao_inventario_10c4.py
4. python -m pytest -q tests/test_inventario_uso_10c4.py tests/test_itens_10c3_puro.py tests/test_itens_10c3_flask.py tests/test_itens_inventario.py
5. Reinicie o Flask e use Ctrl+F5.

Nenhum script deste pacote faz qualquer operação sobre o PostgreSQL.
Nenhum item é distribuído, excluído ou recriado.
Ações de usar/equipar continuam usando rotas e validações do servidor.
Leia docs/ETAPA_10C4_INVENTARIO_USO_VISUAL.md.

~~~

---

## README_10C4_1.txt

~~~text
POKEMON RPG — ETAPA 10C.4.1 — AVISOS GLOBAIS DE 1,5 SEGUNDO

1. Extraia o ZIP na raiz do projeto PokemonRPG.
2. python scripts/instalar_avisos_toast_10c4_1.py
3. python scripts/registrar_documentacao_avisos_10c4_1.py
4. python -m pytest -q tests/test_avisos_toast_10c4_1.py tests/test_avisos_toast_10c4_1_flask.py
5. Reinicie o Flask e atualize a pagina (Ctrl+F5).

Altera somente templates/base.html via instalador. Os arquivos CSS/JS novos ficam em static/.
Nenhum comando do pacote escreve no PostgreSQL ou muda dados dos jogadores.
A correcao visual do autocomplete do inventario do mestre permanece pendente.
Leia docs/ETAPA_10C4_1_AVISOS_TOAST.md.

~~~

---

## README_10C4_2.txt

~~~text
ETAPA 10C.4.2 — AVISOS TEMPORÁRIOS AO USAR ITENS

Requisitos: Etapas 10C.4 e 10C.4.1 já instaladas no PokemonRPG.

1. Extraia o ZIP na raiz do projeto, preservando as pastas.
2. python scripts/instalar_aviso_selecao_10c4_2.py
3. python -m pytest -q tests/test_aviso_selecao_10c4_2.py
4. Reinicie o Flask e use Ctrl+F5.

Alteração: as mensagens do botão Usar que antes apareciam acima dos
Pokémon agora usam os mesmos toasts de 1,5 segundo das mensagens globais.
O botão Cancelar permanece discreto no cabeçalho BAG durante a seleção.

Não modifica o banco, quantidades, regras de cura, outras páginas ou imagens.
Não execute scripts de reconstrução do catálogo por causa deste pacote.

Documentação: docs/ETAPA_10C4_2_AVISOS_SELECAO_POKEMON.md

~~~

---

## README_10C5.txt

~~~text
ETAPA 10C.5 — REPAGINACAO VISUAL RESPONSIVA
Base GitHub: main bbe10f7 (Avisos via toast 2)

1. Extraia esta pasta preservando scripts/, static/, docs/ e tests/ na raiz PokemonRPG.
2. Confira as alteracoes locais antes de instalar: git status -sb
3. python scripts/instalar_visual_10c5.py --verificar
4. python scripts/instalar_visual_10c5.py
5. python -m pytest -q tests/test_visual_10c5.py
6. Reinicie Flask, pressione Ctrl+F5 e valide desktop, tablet e mobile.

Melhorias: menu de navegacao visivel em tablets e celulares; painel do mestre
sem recorte por overflow; autocomplete do catalogo acessivel; layout do
inventario em tablet/mobile; hierarquia visual, foco, espacamentos e modais.

Nenhuma mudanca no banco ou na logica dos itens; toasts 1,5 s preservados.
O instalador altera apenas os templates base.html e jogador/inventario.html.
Backups dos templates: relatorios/backups_ui_10c5/ (nao versionar).

Leia docs/ETAPA_10C5_REVISAO_VISUAL.md para o roteiro completo de testes.

~~~

---

## README_10C5_1.txt

~~~text
POKÉMON RPG — ETAPA 10C.5.1
Correção dos testes da repaginação responsiva no Windows
Base: Etapa 10C.5 já extraída/instalada no projeto.

Este patch altera APENAS:
- scripts/instalar_visual_10c5.py: listas de caminhos usam .as_posix() (Windows e Linux retornam '/').
- tests/test_visual_10c5.py: CSS é validado com Python puro; tinycss2 adiciona validação mais completa apenas se estiver instalado.

INSTALAÇÃO
1. Extraia o conteúdo deste ZIP na RAIZ da pasta PokemonRPG, substituindo os 2 arquivos de mesmo nome.
2. Execute (PowerShell):
   python -m pytest -q tests/test_visual_10c5.py
3. Se o visual 10C.5 já está instalado, NÃO é necessário rodar o instalador novamente.
   Para verificar: python scripts/instalar_visual_10c5.py --verificar
   Retorno esperado se instalado: Visual 10C.5 já instalado. Nenhuma alteração.

O patch não altera templates, CSS, JavaScript, banco PostgreSQL, cadastros, inventários ou permissões.
Validação do patch em ambiente Linux: 6 testes passaram. Precisa confirmar na instalação Windows.

~~~

---

## README_10D1.txt

~~~text
POKÉMON RPG — ETAPA 10D.1 — PADRONIZACAO DOS MENUS E PRIMEIRA AUDITORIA
Base: main @ a7198a1 (Repaginação Visual no inventário).

1. Faça commit/backup das suas modificações locais antes de aplicar.
2. Extraia este ZIP na raiz do PokemonRPG, preservando subpastas.
3. python scripts/instalar_padrao_visual_10d1.py --verificar
4. python scripts/instalar_padrao_visual_10d1.py
5. python -m pytest -q tests/test_padrao_visual_10d1.py
6. Reinicie Flask e force o recarregamento do navegador (Ctrl+F5).

O instalador modifica apenas templates/base.html. O CSS novo entra globalmente
como última camada visual. Não há alterações em rotas, dados, estoque, ações,
JS de batalha, sessões, permissões nem migrations.

IMPORTANTE: este pacote é a PRIMEIRA ETAPA da revisão de todo o projeto.
Leia docs/AUDITORIA_UX_FUNCIONAL_10D1.md para achados, riscos e sequência.
Não execute comandos de limpeza/reconstrução do banco para testar esta etapa.

~~~

---

## README_10D2.txt

~~~text
Pokémon RPG — Etapa 10D.2: CENTRAL ÚNICA DO MESTRE
Base: main 0a157b7 — Repaginação visual 2

1) Extraia este ZIP na raiz da pasta PokemonRPG.
2) Confira alterações locais: git status -sb
3) python scripts/instalar_painel_mestre_10d2.py --verificar
4) python scripts/instalar_painel_mestre_10d2.py
5) python -m pytest -q tests/test_painel_mestre_10d2.py tests/test_painel_mestre_10d2_flask.py tests/test_painel_mestre.py
6) Reinicie o Flask; use Ctrl+F5.

Não há migrations, alteração de senhas ou limpeza de inventário.
Curas em massa SÃO alterações de dados quando confirmadas. Teste em ambiente de desenvolvimento.

Documentação completa em docs/ETAPA_10D2_CENTRAL_MESTRE.md.

~~~

---

## README_10D3.txt

~~~text
POKÉMON RPG — ETAPA 10D.3
Cards verticais do Painel do Mestre
Base confirmada: commit bfc6d9c — Curar todos os pokemons ou apenas de um jogador.

Objetivo
- Reorganizar os treinadores em cards verticais compactos, alinhados ao desenho do mestre.
- Tornar VIDA e STATUS permanentes, incluindo os seis atributos do treinador.
- Exibir os Pokémon em 2 colunas × 3 linhas por card, corrigindo o alinhamento de apelidos.
- Mover Ficha, Equipe, Inventário, Box, nível, permissão e acesso para o menu ⋮.
- Manter Prévia do jogador e Curar Pokémon no rodapé.
- Preservar ajuste de PV, cura global/individual, busca, filtros e ordenação.

Instalação (PowerShell, na raiz de PokemonRPG):
  git status -sb
  python scripts/instalar_painel_10d3.py --verificar
  python scripts/instalar_painel_10d3.py
  python -m pytest -q tests/test_painel_10d3.py tests/test_painel_mestre.py tests/test_painel_mestre_10d2_flask.py

Reinicie o Flask, recarregue com Ctrl+F5.

Arquivos
  patch_10d3/dashboard.html                    Template substituto armazenado fora da pasta templates
  static/css/painel-mestre-10d3.css             Camada de responsividade do Painel do Mestre
  static/js/painel-mestre-10d3.js               Menu de opções (fecha por Escape/clique externo)
  scripts/instalar_painel_10d3.py               Pré-verificação, backup, aplicação, idempotência
  tests/test_painel_10d3.py                    Testes isolados sem PostgreSQL
  docs/ETAPA_10D3_CARDS_VERTICAIS.md           Documentação e roteiro de revisão

O instalador substitui SOMENTE templates/mestre/dashboard.html e guarda
uma cópia em relatorios/backups_ui_10d3/. A instalação do CSS e JS se dá pela extração do ZIP.
NÃO executa migrations, não altera PostgreSQL, nem a lógica de curas e PV.
O instalador recusa templates sem os marcadores 10D.2 esperados.

Em caso de conflito com alterações locais, não force a instalação: compare o template
com o último commit e preserve suas mudanças.

~~~

---

