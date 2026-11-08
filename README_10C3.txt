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
