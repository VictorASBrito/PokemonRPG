"""Anexa (uma vez) notas 10A.1.1 aos documentos existentes, sem sobrescreve-los.

Execucao explicita pelo responsavel depois de descompactar o ZIP na raiz.
Este script modifica SOMENTE os dois arquivos de documentacao citados.
"""
from __future__ import annotations

from pathlib import Path

MARCADOR = "<!-- ANKAR-10A-1-1-2026-10-27 -->"

CONTINUIDADE = """

---

<!-- ANKAR-10A-1-1-2026-10-27 -->
## Versão 10 — Etapa 10A.1.1: auditor das planilhas de Ankar (27/10/2026)

- **Base de código conferida:** commit `871cfaefbb1b6c59a0b001d1f9fa172d38cb1529` (27/10/2026), `main` idêntica a `feature/att-frontend` nessa revisão. Preparada uma entrega incremental para instalação local; nenhuma alteração foi feita no GitHub.
- **Escopo entregue:** serviço `app/services/auditoria_ankar_service.py` e comando `flask --app app.py ankar auditar-planilhas --rotas ... --cidades ...` (texto ou JSON) em leitura exclusiva; separação de local, zona, terreno e entradas, sem deduzir significado dos dados ambíguos. Registrado em `docs/AUDITORIA_PLANILHAS_ANKAR.md`.
- **Planilhas reais analisadas somente leitura:** 73 rotas e 47 abas de cidades/pontos (120 no total); 352 tabelas e 2.683 entradas observadas, com 313 erros e 626 avisos de auditoria no estado atual. Relatório detalhado em `docs/RELATORIO_AUDITORIA_ANKAR_2026-10-27.txt`. Essas contagens não são conteúdo importado/validado.
- **Ocorrências importantes:** sobreposição Pyukumuku 56–60 / Skrelp 60–75 na Rota 1 Água; datas Excel indevidamente interpretadas; tabelas incompletas, intervalos inválidos, `x` e marcadores `Random`. Não converter datas ou `x` automaticamente.
- **Compatibilidade:** registrados novos comandos por Blueprint, `openpyxl>=3.1,<4.0` em `requirements.txt`; nenhum modelo ORM, migration, PostgreSQL, captura, combate ou regras Shiny alterado.
- **Testes neste ambiente:** 10 testes unitários passaram; 1 teste de CLI ficou ignorado por ausência de Flask, Flask-SQLAlchemy e Flask-Migrate no ambiente de trabalho. **Não afirmar integração Flask/PostgreSQL validada** até execução local.
- **Ação seguinte:** instalar, executar `python -m pytest -q tests/test_auditoria_ankar.py`, executar o comando sobre as planilhas reais, revisar erros e relatar resultados. Somente depois planejar aprovação/importação validada da geografia (10A.1.2). Etapas de NPCs, Campo e eventos continuam não implementadas nesta Versão 10.
"""

DIARIO = """

<!-- ANKAR-10A-1-1-2026-10-27 -->
### 2026-10-27 — Versão 10, Etapa 10A.1.1: auditoria somente leitura de Ankar
- **Objetivo:** auditar planilhas de rotas, cidades e pontos de interesse, preservando zonas e terrenos, antes de qualquer importação.
- **Status:** IMPLEMENTADO EM ZIP; 10 TESTES UNITÁRIOS PASSARAM; INSTALAÇÃO/INTEGRAÇÃO FLASK PENDENTES DE VALIDAÇÃO PELO MESTRE.
- **Branch/commit-base:** `main` = `feature/att-frontend`, commit `871cfaefbb1b6c59a0b001d1f9fa172d38cb1529` (27/10/2026). GitHub usado apenas para leitura.
- **Arquivos:** `app/services/auditoria_ankar_service.py`, `app/commands/ankar.py`, `app/commands/__init__.py`, `app/__init__.py`, `requirements.txt`, `tests/test_auditoria_ankar.py`, `docs/AUDITORIA_PLANILHAS_ANKAR.md`, `docs/RELATORIO_AUDITORIA_ANKAR_2026-10-27.txt`, `scripts/aplicar_documentacao_10a1.py`, documentação de continuidade/diário (acréscimos preservando conteúdo histórico).
- **Esquema/migrations:** nenhuma. Sem escrita em PostgreSQL, sem modificação de XLSX, sem importação de encontros.
- **Leitura exploratória real:** 120 abas, 352 tabelas, 2.683 entradas, 313 erros e 626 avisos, conforme relatório. `x`, datas Excel, sobreposição d100 e `Random` não interpretados automaticamente.
- **Testes executados:** `PYTHONPATH=... python -m pytest -q tests/test_auditoria_ankar.py` → 10 passaram, 1 ignorado (Flask ausente no ambiente da execução). Compilação Python dos arquivos novos passou. CLI real no aplicativo e PostgreSQL não testados aqui.
- **Riscos/pendências:** validar integração Flask e arquivos reais no computador do mestre; discutir correções da planilha sem sobrescrever originais; decidir semântica de `x` e marcadores ambíguos. O relatório pode apontar lacunas aparentes devido a d100 inválidos.
- **Próxima ação:** instalar ZIP incremental, instalar dependências, executar testes e comando, obter feedback local; somente então prosseguir para armazenamento validado 10A.1.2.
"""


def aplicar(raiz: Path, *, simular: bool = False) -> list[str]:
    atualizacoes = {
        raiz / "docs" / "CONTINUIDADE_PROJETO.md": CONTINUIDADE,
        raiz / "docs" / "DIARIO_DESENVOLVIMENTO.md": DIARIO,
    }
    ausentes = [str(path) for path in atualizacoes if not path.is_file()]
    if ausentes:
        raise FileNotFoundError("Documentos historicos ausentes; nenhuma alteracao realizada: "
                                + ", ".join(ausentes))
    resultado = []
    for path, bloco in atualizacoes.items():
        texto = path.read_text(encoding="utf-8-sig")
        if MARCADOR in texto:
            resultado.append(f"JA ATUALIZADO: {path}")
            continue
        if not simular:
            # Preserva integralmente o documento historico existente.
            with path.open("a", encoding="utf-8") as destino:
                destino.write(bloco)
        resultado.append(f"{'SIMULACAO' if simular else 'ATUALIZADO'}: {path}")
    return resultado


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simular", action="store_true", help="Nao grava arquivos.")
    args = parser.parse_args()
    try:
        for mensagem in aplicar(Path(__file__).resolve().parent.parent,
                                simular=args.simular):
            print(mensagem)
    except (OSError, UnicodeError) as erro:
        parser.exit(1, f"ERRO: {erro}\n")
