"""Registra a correção de testes UTF-8 sem sobrescrever o histórico existente.

Uso, a partir da raiz do projeto:
    python scripts/registrar_correcao_atlas_utf8.py

O script é opcional para o funcionamento do Atlas; só acrescenta documentação.
"""
from __future__ import annotations

from pathlib import Path

MARCA = "<!-- ATLAS_ANKAR_V10A2_1_UTF8 -->"

CONTINUIDADE = """

<!-- ATLAS_ANKAR_V10A2_1_UTF8 -->
### Etapa 10A.2.1 — Correção dos testes no Windows (28/10/2026)
- Corrigido `tests/test_atlas_ankar.py`: todas as leituras de arquivos no teste de idempotência agora especificam `encoding='utf-8'`. A codificação padrão `cp1252` do Windows gerava `UnicodeDecodeError` ao ler o diário.
- O instalador, o Atlas visual, os JSON, a navegação, os acessos e as planilhas não sofreram mudanças nesta correção.
- Relato do usuário antes do patch: 9 testes passaram e 1 falhou; aguardar reexecução dos 10 testes no Windows para confirmar a correção no ambiente real.
- **Sem migrations ou escrita no PostgreSQL.**
"""

DIARIO = """

<!-- ATLAS_ANKAR_V10A2_1_UTF8 -->
### 2026-10-28 — Etapa 10A.2.1: Ajuste UTF-8 em teste de regressão
- **Objetivo:** corrigir a falha `UnicodeDecodeError: cp1252` em `test_instalador_e_idempotente_e_nao_altera_jogador` no Windows.
- **Status:** PATCH PREPARADO; reexecução Windows pendente.
- **Alterações:** `tests/test_atlas_ankar.py` usa `read_text(encoding='utf-8')`; documentação de correção em `docs/CORRECAO_UTF8_ATLAS_ANKAR_10A2_1.md`.
- **Resultado anterior informado pelo usuário:** `9 passed, 1 failed in 3.01s` antes da correção.
- **Migrations:** nenhuma. **PostgreSQL:** nenhuma alteração. **GitHub:** nenhuma alteração.
- **Próximo:** `python -m pytest -q tests/test_atlas_ankar.py tests/test_atlas_ankar_flask.py` no Windows e conferir navegação visual.
"""


def registrar(raiz: Path) -> list[str]:
    alterados = []
    for nome, trecho in (
        ("docs/CONTINUIDADE_PROJETO.md", CONTINUIDADE),
        ("docs/DIARIO_DESENVOLVIMENTO.md", DIARIO),
    ):
        caminho = raiz / nome
        if not caminho.is_file():
            continue
        original = caminho.read_text(encoding="utf-8")
        if MARCA in original:
            continue
        caminho.write_text(original.rstrip() + "\n" + trecho, encoding="utf-8")
        alterados.append(nome)
    return alterados


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    print("Documentos atualizados:", registrar(raiz))
