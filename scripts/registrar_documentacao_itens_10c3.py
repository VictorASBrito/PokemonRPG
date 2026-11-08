from __future__ import annotations
from pathlib import Path
RAIZ=Path(__file__).resolve().parents[1]
MARCA='<!-- ANKAR_10C3_CATALOGO_20261028 -->'
NOTAS={
 'docs/CONTINUIDADE_PROJETO.md':'''### 2026-10-28 — Etapa 10C.3: reconstrução de itens e efeitos reais
- Escopo: manifesto explícito de 77 códigos legados para 48 itens de destino, com preservação de vínculos e somatório de estoques; remoção de naturezas falsas somente mediante aceite consciente.
- Catálogo reconstruído somente com `--aplicar --confirmar RECONSTRUIR-ANKAR`, após backup de dados e auditoria. Nunca aplicar como efeito colateral da instalação.
- Cura PV/remover condição passa a funcionar ao consumir com seleção do Pokémon, transação conjunta e histórico; sem PP automático.
- Mapa da Região de Ankar: item-chave sem interação, visualizado no inventário em modal com `static/img/ankar-mapa.jpg`.
- Fonte: commit `5a54423` (“Imagens Itens 1”). **Sem migrations**. Integração PostgreSQL não verificada neste ambiente.
- Detalhes em `docs/ETAPA_10C3_RECONSTRUCAO_CATALOGO.md`.
''',
 'docs/DIARIO_DESENVOLVIMENTO.md':'''### 2026-10-28 — Etapa 10C.3: reconstrução controlada do catálogo de itens
- **Status:** pacote incremental preparado, testes isolados executados, testes Flask/PostgreSQL e aplicação pendentes de execução local e aprovação.
- **Mudanças:** plano de 77 códigos para 48 cadastros, vínculos de inventários, arte de itens do commit Imagens Itens 1, mapa estático e cura funcional (PV/status) com seleção de alvo.
- **Proteções:** simulação padrão, bloqueios contra dados diferentes, conflito de imagens e usuários de outras campanhas, backup JSON antes de aplicar, confirmação explícita; natureza Ingênuo com 1 unidade só pode ser descartada com flag específica.
- **Banco:** não alterado pela entrega; reconstrução destrutiva só com comando explícito após backup PostgreSQL; nenhuma migration.
- **Testes:** executar `python -m pytest -q tests/test_itens_10c3_puro.py tests/test_itens_10c3_flask.py` e testes de regressão reais.
- **Próximo:** revisar simulação, validar imagem de cada item, aplicar conscientemente e testar cura/condições + mapa.
'''
}

def registrar(raiz=RAIZ):
    feitos=[]
    for rel,txt in NOTAS.items():
        path=Path(raiz)/rel
        if not path.exists():continue
        old=path.read_text(encoding='utf-8')
        if MARCA in old:continue
        path.write_text(old.rstrip()+f'\n\n{MARCA}\n{txt}',encoding='utf-8')
        feitos.append(rel)
    return feitos
if __name__=='__main__':print('Documentos atualizados:', registrar())
