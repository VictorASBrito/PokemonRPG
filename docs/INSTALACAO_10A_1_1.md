# Aplicação do pacote incremental 10A.1.1

**Base esperada:** `VictorASBrito/PokemonRPG`, commit `871cfaefbb1b6c59a0b001d1f9fa172d38cb1529` (27/10/2026), tanto `main` quanto `feature/att-frontend` nessa revisão.

1. Faça backup ou commit das suas alterações locais. Confira `git status` e `git log -1 --oneline`. **Não substitua arquivos alterados localmente sem comparar diferenças.**
2. Descompacte o ZIP **dentro da pasta raiz do PokemonRPG**, preservando os subdiretórios `app/`, `tests/`, `docs/` e `scripts/`.
3. Rode `python scripts/aplicar_documentacao_10a1.py --simular` e depois `python scripts/aplicar_documentacao_10a1.py`. Essa etapa acrescenta as notas da versão 10 a `docs/CONTINUIDADE_PROJETO.md` e `docs/DIARIO_DESENVOLVIMENTO.md` **sem substituir o histórico existente**. É segura se repetida; sem os dois arquivos originais, recusa a alteração.
4. Instale as dependências: `python -m pip install -r requirements-dev.txt`. O `requirements-dev.txt` original inclui o `requirements.txt` atualizado com `openpyxl`.
5. Teste: `python -m pytest -q tests/test_auditoria_ankar.py`.
6. Rode a auditoria (PowerShell):

```powershell
flask --app app.py ankar auditar-planilhas `
  --rotas "Região de Ankar - Rotas - PokéRPG.xlsx" `
  --cidades "Ankar - Cidades e Pontos de Interesse - PokéRPG.xlsx" `
  --todos
```

Se as planilhas estiverem em outra pasta, informe seus caminhos nos parâmetros.

**Código de saída 1 não necessariamente indica problema de software**: erros conhecidos de d100 nas planilhas fazem a auditoria retornar código 1 até serem revisados. Nenhum comando deste pacote grava no PostgreSQL e não há migrations.

**Conferência recomendada:** verifique `git diff --stat`, `git status` e os erros reportados. Somente depois de concluir sua validação local faça commit e push manualmente. A Etapa 10A.1.2 ainda não foi implementada.
