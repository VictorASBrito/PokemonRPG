# Pokémon RPG — 10D.3: cards verticais do mestre

**Base:** commit `bfc6d9c0ab22f1ae6bc35fb1e13c588f292f09c5`, que já inclui a central única 10D.2, ajuste de PV numérico e cura de todos os Pokémon de um treinador ou de toda a campanha. Esta entrega não altera esses serviços nem o PostgreSQL.

## O que muda

- A central apresenta cards de treinadores em **3 colunas no desktop comum** (a partir de 1350 px), **2 colunas em telas intermediárias** (860–1349 px) e **uma coluna em celular e tablet estreito**. Em telas extralargas (≥1900 px), cabem até quatro colunas.
- Cada card deixa o layout de faixa horizontal e assume uma hierarquia vertical: **identidade → VIDA → STATUS → Pokémon 2×3 → rodapé**.
- Vida do treinador inclui PV, barra e ajuste numérico `−`/`+`.
- Status sempre visível: atributos Físico, Destreza, Saúde, Conhecimento, Comunicação e Espírito em mini-cards, além de dinheiro/equipe/Box/perfil/acesso.
- Apelidos de Pokémon têm espaço próprio, com espécie em segunda linha; nomes longos são limitados a duas linhas com tooltip de título para evitar desalinhamentos.
- O menu nativo `⋮` reúne: Ficha, Equipe, Inventário, Box, Nível, Permissão e Ativar/Desativar acesso. Fecha com Escape ou clique fora.
- **Prévia do jogador** e **Curar Pokémon** ficam no rodapé do card. **Curar todos os Pokémon** permanece no topo da central.
- Busca, filtros, modo de ordenação (arrastar/setas), limites de PV e endpoints de cura seguem intactos.

## Escopo de segurança

Nenhuma rota, permissão, serviço, modelo ou dado é alterado. Ações de cura ainda exigem confirmação e CSRF no backend. O ajuste numérico de PV permanece validado pelos endpoints existentes. O botão de ativar/desativar acesso continua com o comportamento da versão-base; uma revisão de proteção CSRF dessa rota pode ser feita separadamente, sem integrar mudanças de segurança a este patch visual.

## Instalação

1. Faça commit ou guarde cópia das alterações locais.
2. Extraia o ZIP na raiz do projeto, mantendo as pastas `patch_10d3`, `static`, `scripts`, `tests` e `docs`.
3. Execute `python scripts/instalar_painel_10d3.py --verificar` (não escreve nada).
4. Execute `python scripts/instalar_painel_10d3.py` para substituir somente `templates/mestre/dashboard.html`. Backups automáticos em `relatorios/backups_ui_10d3/`.
5. Execute `python -m pytest -q tests/test_painel_10d3.py tests/test_painel_mestre.py tests/test_painel_mestre_10d2_flask.py`.
6. Reinicie Flask e pressione Ctrl+F5.

## Checklist manual no Flask real

- Desktop (1366/1440/1920): 3/3/4 cards por linha; nenhum painel do treinador ocupa uma faixa inteira; atributos sempre visíveis.
- Tablet (820/1024): 1/2 cards por linha. Menu `⋮` não deve ser cortado e todos os formulários continuam editáveis.
- Celular (360/390): uma coluna de treinadores, mini-cards em duas colunas, sem rolagem horizontal.
- Abrir o menu `⋮` de dois treinadores: somente um deve ficar aberto. Fechar por Escape e toque fora.
- Filtrar, pesquisar, reordenar e abrir Prévia/Ficha/Equipe/Inventário/Box.
- Validar ajuste de PV com números digitados, cura individual e global, inclusive após trocar a ordem de jogadores.
- Conferir sprites de entrada dos nove jogadores e fallback Pokébola para demais treinadores.
- Verificar tema escuro e claro, nicknames longos e Pokémon com condições ativas.

## Verificação executada na preparação

- 5 testes isolados de Jinja, markup e instalação passaram sem Flask/PostgreSQL.
- JavaScript validado com `node --check`.
- Smoke test visual representativo em Chromium para 360, 390, 768, 820, 1024, 1366, 1440 e 1920 px, sem transbordamento horizontal. A página representativa não equivale à interface Flask real.

## Limites

Não há avaliação integrada do PostgreSQL nesta entrega. O patch não adiciona novos campos ou funcionalidades administrativas; somente reorganiza as já existentes. As ações e seu comportamento de negócio permanecem conforme a Etapa 10D.2.
