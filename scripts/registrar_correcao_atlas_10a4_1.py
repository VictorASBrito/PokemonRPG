"""Registra a correção do template 10A.4.1 nos dois históricos do projeto.

Somente adiciona documentação, uma vez; não altera código, banco nem dados.
"""
from __future__ import annotations

from pathlib import Path

MARCA = "<!-- ATLAS_ANKAR_V10A4_1 -->"
TEXTO = f"""\n\n{MARCA}
### Etapa 10A.4.1 — Compatibilidade da ficha do Atlas (28/10/2026)
- **Problema:** o teste `test_template_detalhe_aponta_para_mapa_sem_alterar_encontros` da Etapa 10A.3 renderizava `templates/regiao/detalhe.html` diretamente e não passava `formas`. A atualização 10A.4 introduziu `formas.get(...)` e causava `jinja2.exceptions.UndefinedError`, mesmo com o endpoint real fornecendo o contexto.
- **Correção:** valores padrão seguros para as variáveis opcionais `formas`, `encontrados_por`, `descricao_paragrafos` e `atlas_csrf`, apenas quando omitidas ou nulas. A página real permanece inalterada quando a rota fornece esses valores.
- **Arquivos:** `templates/regiao/detalhe.html`, `tests/test_atlas_10a4_1_template.py`, script e documentação desta correção.
- **Escopo:** sem migrations, alteração no PostgreSQL, mudanças nos encontros, imagens, regras de acesso ou planilhas.
- **Validação local do pacote:** testes unitários Jinja sem Flask; reexecutar a suíte Flask completa na máquina da campanha.
- **Próxima ação:** verificar a geração Atlas → Capturáveis com o mestre no ambiente PostgreSQL e revisar a usabilidade da interface.
"""


def registrar(raiz: Path) -> list[str]:
    atualizados = []
    for nome in ("CONTINUIDADE_PROJETO.md", "DIARIO_DESENVOLVIMENTO.md"):
        destino = Path(raiz) / "docs" / nome
        if not destino.is_file():
            raise FileNotFoundError(f"Documento não encontrado: {destino}")
        original = destino.read_text(encoding="utf-8")
        if MARCA in original:
            continue
        with destino.open("a", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(TEXTO)
        atualizados.append(str(destino))
    return atualizados


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    print("Documentos atualizados:", registrar(raiz))
