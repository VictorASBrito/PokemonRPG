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
