"""Registra a etapa 10C.4 nos documentos históricos, sem duplicar entradas."""
from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MARCADOR='<!-- INVENTARIO_USO_VISUAL_10C4 -->'
NOTA=f'''

{MARCADOR}
### Etapa 10C.4 — Uso do item pela linha e escolha visual do Pokémon
- O botão **Usar** fica na linha do item, junto ao nome e quantidade; o painel direito apresenta descrição e transferência.
- Tratamentos de PV destacam Pokémon da equipe feridos; tratamentos de status destacam Pokémon afetados (mesmo com PV cheio). A seleção envia POST ao serviço terapêutico 10C.3, sem afrouxar validações.
- O **Mapa de Ankar** abre no diálogo estático pelo botão Usar e não é consumido.
- Equipar continua disponível em diálogo (equipe/Box), e o ajuste de quantidade fica apenas no gerenciamento do Mestre.
- PENDÊNCIA VISUAL: a área inferior de Adicionar item do Mestre pode aparecer cortada/compactada, especialmente o seletor de catálogo em viewport baixo. Revisar overflow e popup do autocomplete posteriormente.
- Consulte `docs/ETAPA_10C4_INVENTARIO_USO_VISUAL.md` para testes manuais. Sem migrations e sem alteração automática de inventários.
'''

def registrar(raiz=ROOT):
    escritos=[]
    for nome in ('docs/CONTINUIDADE_PROJETO.md','docs/DIARIO_DESENVOLVIMENTO.md'):
        f=Path(raiz)/nome
        if not f.is_file():continue
        src=f.read_text(encoding='utf-8')
        if MARCADOR in src:continue
        f.write_text(src.rstrip()+NOTA+'\n',encoding='utf-8')
        escritos.append(nome)
    return escritos

if __name__=='__main__':
    print('Documentos atualizados:',registrar() or '(já registrados)')
