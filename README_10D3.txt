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
