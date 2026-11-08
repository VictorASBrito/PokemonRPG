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
