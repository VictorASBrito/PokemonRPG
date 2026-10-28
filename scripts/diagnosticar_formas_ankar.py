"""Relatório somente leitura dos 33 nomes especiais do Atlas contra PostgreSQL."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from sqlalchemy import select
from app import create_app
from app.extensions import db
from app.models.db import FormaPokemon
from app.services.ankar_formas_service import carregar_aliases, opcoes_formas
from app.services.regiao_ankar_service import carregar_catalogo_ankar


def diagnosticar():
    app=create_app()
    with app.app_context():
        formas=list(db.session.execute(select(FormaPokemon).where(FormaPokemon.ativo.is_(True))).scalars())
        catalogo=carregar_catalogo_ankar()
        contagens=Counter(e['pokemon'] for local in catalogo['locais'] for zona in local['zonas']
                          for tabela in zona['tabelas'] for e in tabela['encontros'] if e.get('pokemon'))
        aliases=carregar_aliases()['aliases']
        linhas=["Atlas de Ankar — diagnóstico dos 33 nomes especiais (somente leitura)",""]
        status=Counter()
        for nome in sorted(aliases,key=str.casefold):
            opcoes=opcoes_formas(nome,formas)
            if not opcoes: situacao='SEM VÍNCULO'
            elif len(opcoes)>1: situacao='ESCOLHA DO MESTRE'
            else: situacao='VINCULADO'
            status[situacao]+=1
            linhas.append(f"[{situacao}] {nome} — {contagens[nome]} encontros")
            for opcao in opcoes:
                linhas.append(f"   • {opcao['nome']} [{opcao['codigo']}] UUID={opcao['id']}")
            if nome.startswith('Shellos'):
                linhas.append('   Atenção: o catálogo contém somente Shellos genérico, não duas formas por cor.')
        linhas.extend(['', 'Resumo: '+', '.join(f'{k}: {v}' for k,v in status.items())])
        return '\n'.join(linhas)+'\n'

if __name__ == '__main__':
    try: print(diagnosticar())
    except Exception as erro:
        raise SystemExit(f'Não foi possível ler o catálogo ativo: {erro}') from erro
