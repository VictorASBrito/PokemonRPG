"""Registra a revisão visual 10B.2 nos documentos já existentes (idempotente).

Uso na raiz do projeto: python scripts/registrar_entrada_10b2.py
"""
from __future__ import annotations

from pathlib import Path

MARCADOR = "<!-- ENTRADA_PERSONAGENS_10B2 -->"
TEXTO_CONTINUIDADE = """\n\n{marcador}\n### Etapa 10B.2 — Refinamento da seleção de personagens (28/10/2026)\n- Alterações restritas a `templates/entrada_personagens.html` e `static/css/entrada-personagens.css`.\n- O décimo slot foi renomeado de Coringa para **Mestre**, com a Pokébola já presente em `static/img/pokebola.png`. A rota de acesso tradicional permanece `entrada_personagens.coringa`.\n- Slots dos nove jogadores mantêm exatamente a mesma dimensão visual; sprites exibidas inteiras com `object-fit: contain`, centralizadas e sem corte. A ordem, as imagens dos slots e a configuração de logins permanecem intactas.\n- Texto sob o título: apenas “Escolha seu personagem para abrir a ficha.”; textos explicativos do coringa e rodapé removidos.\n- Sem alterações na autenticação, sessões, permissões, banco de dados, migrations ou configurações de contas.\n- Verificações: executar `python -m pytest -q tests/test_entrada_10b2_visual.py tests/test_entrada_personagens.py tests/test_entrada_personagens_flask.py` no ambiente do projeto.\n""".format(marcador=MARCADOR)
TEXTO_DIARIO = """\n\n{marcador}\n### 2026-10-28 — Etapa 10B.2: revisão visual da seleção circular\n- **Objetivo:** manter as nove sprites inteiras e círculos iguais; trocar estrela por Pokébola e nome Coringa por Mestre; simplificar textos.\n- **Arquivos:** `templates/entrada_personagens.html`, `static/css/entrada-personagens.css`, `tests/test_entrada_10b2_visual.py`, `scripts/registrar_entrada_10b2.py`.\n- **Autenticação:** inalterada. Slot Mestre continua encaminhando ao formulário de usuário/senha pela rota existente. Ordem e vínculos atuais dos personagens preservados.\n- **Banco/migrations:** nenhuma alteração.\n- **Teste local:** verificação da renderização isolada e regressão de estrutura; conferir na instalação real.\n""".format(marcador=MARCADOR)


def registrar(raiz: Path) -> list[str]:
    alterados: list[str] = []
    for nome, texto in (
        ("docs/CONTINUIDADE_PROJETO.md", TEXTO_CONTINUIDADE),
        ("docs/DIARIO_DESENVOLVIMENTO.md", TEXTO_DIARIO),
    ):
        arquivo = raiz / nome
        if not arquivo.is_file():
            raise FileNotFoundError(f"Documento esperado não encontrado: {nome}")
        atual = arquivo.read_text(encoding="utf-8")
        if MARCADOR in atual:
            continue
        arquivo.write_text(atual.rstrip("\n") + texto, encoding="utf-8")
        alterados.append(nome)
    return alterados


if __name__ == "__main__":
    print("Documentos atualizados:", registrar(Path(__file__).resolve().parents[1]))
