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
