"""Registra a alteracao visual 10C.4.1 sem duplicar notas em execucoes repetidas."""
from __future__ import annotations
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MARCADOR = "<!-- AVISOS_TOAST_10C4_1 -->"
NOTA = f"""

{MARCADOR}
### Etapa 10C.4.1 — Notificacoes flutuantes de confirmacao
- Mensagens `flash()` do Flask (sucesso, erro, aviso e informacao) deixam de ocupar espaco dentro de `.conteudo` e passam a surgir em pequenos toasts na parte superior direita.
- Cada toast desaparece apos 1,5 segundo; passar o mouse ou focar o aviso pausa a contagem e o botao Fechar permite encerramento manual.
- A alteracao vale globalmente para mestre e jogadores (inventario, fichas, catalogos e demais telas que utilizam `templates/base.html`), sem alteracoes no banco.
- Arquivos: `scripts/instalar_avisos_toast_10c4_1.py`, `static/css/avisos-toast-10c4-1.css`, `static/js/avisos-toast-10c4-1.js`.
- Pendencia visual anterior mantida: autocomplete do catalogo/rodape da mochila do mestre pode ser cortado com altura reduzida; precisa de ajuste separado.
"""


def registrar(raiz: Path = RAIZ) -> list[str]:
    alterados = []
    for relativo in (
        "docs/ETAPA_10C4_INVENTARIO_USO_VISUAL.md",
        "docs/CONTINUIDADE_PROJETO.md",
        "docs/DIARIO_DESENVOLVIMENTO.md",
    ):
        arquivo = Path(raiz) / relativo
        if not arquivo.is_file():
            continue
        anterior = arquivo.read_text(encoding="utf-8")
        if MARCADOR in anterior:
            continue
        arquivo.write_text(anterior.rstrip() + NOTA + "\n", encoding="utf-8")
        alterados.append(relativo)
    return alterados


if __name__ == "__main__":
    for caminho in registrar():
        print("Documentado:", caminho)
    print("Registro 10C.4.1 concluido.")
