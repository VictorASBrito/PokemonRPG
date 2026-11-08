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
