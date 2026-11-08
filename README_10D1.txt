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
