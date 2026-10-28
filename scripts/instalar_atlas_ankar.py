"""Instala os dois pontos de integração do Atlas, sem sobrescrever arquivos locais.

Esta rotina modifica SOMENTE app/__init__.py e templates/base.html, acrescentando
import/registro do blueprint e dois links de navegação do mestre. Também anexa
uma anotação aditiva aos documentos de continuidade, se existirem.
Pode ser executada mais de uma vez. Nenhuma migration ou alteração no banco.
"""
from __future__ import annotations

from pathlib import Path

MARCA_DOC = "<!-- ATLAS_ANKAR_V10A2 -->"
CONTINUIDADE = """

<!-- ATLAS_ANKAR_V10A2 -->
### Etapa 10A.2 — Atlas visual de Ankar (28/10/2026)
- Entregue catálogo visual **somente leitura** com 119 locais: 73 rotas, 26 cidades e 20 pontos de interesse (352 tabelas, 2.683 entradas).
- Rotas em `/regiao/ankar`; detalhes em `/regiao/ankar/<slug>`; acesso restrito ao mestre para evitar spoilers aos jogadores.
- Fonte estática: `app/data/catalogo_ankar_visual.json`, gerada das duas planilhas originais pelo script `scripts/gerar_catalogo_ankar.py`; fontes não são necessárias em produção para a consulta.
- Habitats principal/secundário, terrenos, acessos, deslocamento/tamanho, descrições, zonas e encontros por terreno são exibidos. `% Captura` não é peso de encontro.
- Datas que o Excel gerou automaticamente a partir de d100 são apresentadas como faixas (dia-mês) mantendo o valor original no JSON. Marcadores `x`, sobreposições e dados incompletos não são alterados.
- Novos módulos: `app/routes/regiao.py`, `app/services/regiao_ankar_service.py`, `templates/regiao/`, `static/css/atlas-ankar.css`, `static/js/atlas-ankar.js`.
- Registro do blueprint e links da navegação inseridos por `scripts/instalar_atlas_ankar.py`, que preserva conteúdo local e é idempotente.
- Nenhuma migration, escrita no PostgreSQL, rolagem de encontros ou atribuição de capturáveis. Validar testes Flask com dependências instaladas e conferir UI local.
- Próxima etapa: revisão visual/conteúdo e só depois discussão do fluxo de encontros, permissões e dados persistidos.
"""
DIARIO = """

<!-- ATLAS_ANKAR_V10A2 -->
### 2026-10-28 — Etapa 10A.2: Atlas visual de Ankar
- **Objetivo:** disponibilizar rotas, cidades, pontos de interesse, habitats, terrenos, acessos e Pokémon no site antes de implementar funções.
- **Status:** IMPLEMENTADO EM PACOTE INCREMENTAL; VALIDAÇÃO FLASK E NAVEGADOR PENDENTES.
- **Base:** commit `871cfae` (27/10/2026), compatível com a instalação da etapa 10A.1.1.
- **Dados:** 73 rotas, 26 cidades, 20 pontos de interesse; 352 tabelas e 2.683 linhas de encontros extraídas das planilhas fornecidas nesta conversa.
- **Arquivos:** atlas JSON, leitor XLSX, serviço, blueprint, templates, CSS, JS, instalador aditivo, testes e documentação especializada.
- **Decisões:** somente leitura, tela do mestre; sem mecanismos de encontro/captura. Recuperar interpretação visual de datas do Excel sem substituir o original; marcador `x` mantém semântica não confirmada.
- **Migrations:** nenhuma. **PostgreSQL:** nenhuma escrita. **GitHub:** nenhuma alteração.
- **Testes:** registrar aqui o resultado executado localmente após instalar as dependências.
- **Próximo:** validar telas, revisar exceções de dados e planejar a função posterior com o mestre.
"""


def atualizar_se_novo(caminho: Path, trecho: str) -> bool:
    if not caminho.is_file():
        return False
    base = caminho.read_text(encoding="utf-8")
    if MARCA_DOC in base:
        return False
    caminho.write_text(base.rstrip() + "\n" + trecho, encoding="utf-8")
    return True


def instalar(raiz: Path) -> dict:
    app_path = raiz / "app/__init__.py"
    base_path = raiz / "templates/base.html"
    if not app_path.is_file() or not base_path.is_file():
        raise RuntimeError("Execute o instalador na raiz da aplicação Flask já existente.")
    app_original = app_path.read_text(encoding="utf-8")
    base_original = base_path.read_text(encoding="utf-8")

    app_novo = app_original
    if "from app.routes.regiao import regiao_bp" not in app_novo:
        marcador = "from app.routes.boxes import boxes_bp"
        if marcador not in app_novo:
            raise RuntimeError(f"Não encontrei âncora para import no {app_path}.")
        app_novo = app_novo.replace(marcador, marcador + "\n    from app.routes.regiao import regiao_bp", 1)
    if "app.register_blueprint(regiao_bp)" not in app_novo:
        marcador = "app.register_blueprint(boxes_bp)"
        if marcador not in app_novo:
            raise RuntimeError(f"Não encontrei âncora para registro no {app_path}.")
        app_novo = app_novo.replace(marcador, marcador + "\n    app.register_blueprint(regiao_bp)", 1)

    base_novo = base_original
    novo_link = '<a href="{{ url_for(\'regiao.indice_ankar\') }}">Região</a>'
    # Inserir nas duas ramificações do mestre, preservando a navegação de jogador.
    if base_novo.count(novo_link) < 2:
        marcador = '<a href="{{ url_for(\'combates.painel\') }}">Campo</a>'
        if base_novo.count(marcador) < 3:
            raise RuntimeError("Navegação do template foi alterada: revisão manual necessária.")
        # Caso a atualização já tenha sido parcialmente aplicada, não duplicar.
        if novo_link in base_novo:
            raise RuntimeError("Link Região existe apenas parcialmente no template; revise o arquivo.")
        base_novo = base_novo.replace(marcador, novo_link + "\n                    " + marcador, 2)

    if app_novo != app_original:
        app_path.write_text(app_novo, encoding="utf-8")
    if base_novo != base_original:
        base_path.write_text(base_novo, encoding="utf-8")
    docs = []
    for path, trecho in ((raiz / "docs/CONTINUIDADE_PROJETO.md", CONTINUIDADE),
                         (raiz / "docs/DIARIO_DESENVOLVIMENTO.md", DIARIO)):
        if atualizar_se_novo(path, trecho):
            docs.append(str(path.relative_to(raiz)))
    return {"app": app_novo != app_original, "base": base_novo != base_original, "docs": docs}


def main():
    raiz = Path(__file__).resolve().parent.parent
    resultado = instalar(raiz)
    print("Atlas Ankar registrado:", resultado)
    print("Reinicie o servidor e acesse /regiao/ankar com o perfil mestre.")


if __name__ == "__main__":
    main()
