# Etapa 10A.2.1 — Compatibilidade dos testes no Windows (28/10/2026)

## Problema confirmado

Na execução local do mestre (`Python 3.13` no PowerShell/Windows), 9 testes passaram e 1 falhou no teste `test_instalador_e_idempotente_e_nao_altera_jogador` com `UnicodeDecodeError`, ao ler documentação UTF-8 usando `Path.read_text()` sem especificar `encoding` (o Windows usou `cp1252`).

## Correção

Atualizado **somente** `tests/test_atlas_ankar.py`: todas as chamadas de `Path.read_text()` do teste de idempotência agora usam `encoding='utf-8'`. O instalador já gravava os arquivos corretamente em UTF-8. Não alterar o instalador para gravar em `cp1252`: isso reduziria a compatibilidade e não resolveria a causa.

## Como aplicar

Copiar o arquivo corrigido `tests/test_atlas_ankar.py` para o mesmo caminho no projeto. Em seguida:

```powershell
python -m pytest -q tests/test_atlas_ankar.py tests/test_atlas_ankar_flask.py
```

Não é necessário executar novamente `scripts/instalar_atlas_ankar.py`, reiniciar o servidor, mexer nas planilhas, migrar o banco ou atualizar o JSON. O Atlas e as rotas instaladas permanecem inalterados.

O script opcional `scripts/registrar_correcao_atlas_utf8.py` registra esta correção de forma aditiva e idempotente nos documentos mestres, sem substituir seus conteúdos.

## Estado da validação

- Relatório do ambiente do mestre antes do patch: **9 passaram, 1 falhou por `UnicodeDecodeError`**, em 3,01 s.
- Validação no ambiente do assistente: **8 testes sem Flask passaram** (`pytest -q tests/test_atlas_ankar.py`) e o registro de documentação foi testado quanto à idempotência.
- Testes Flask integrados e reexecução real no Windows: dependem da execução local do mestre; não presumir resultado.
- **Sem migration, sem alteração de esquema ou de dados.**
