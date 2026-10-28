"""Compara NOMES de encontros no Atlas com formas ativas no PostgreSQL.

Somente leitura: nao altera o banco, o JSON nem as planilhas originais.
Execute a partir da raiz do projeto:
    python scripts/listar_pokemon_pendentes_ankar.py
"""
from __future__ import annotations

import csv
from collections import defaultdict
from difflib import get_close_matches
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
ARQUIVO_ATLAS = RAIZ / 'app' / 'data' / 'catalogo_ankar_visual.json'
PASTA_SAIDA = RAIZ / 'relatorios'


def coletar() -> tuple[dict[str, dict], dict[str, int]]:
    with ARQUIVO_ATLAS.open(encoding='utf-8') as f:
        atlas = json.load(f)
    registros = {}
    especiais = {'marcador_x': 0, 'random': 0, 'vazio': 0}
    for local in atlas['locais']:
        for zona in local.get('zonas', []):
            for tabela in zona.get('tabelas', []):
                for encontro in tabela.get('encontros', []):
                    nome = str(encontro.get('pokemon') or '').strip()
                    if encontro.get('marcador') or nome.casefold() == 'x':
                        especiais['marcador_x'] += 1
                        continue
                    if nome.casefold() == 'random':
                        especiais['random'] += 1
                        continue
                    if not nome:
                        especiais['vazio'] += 1
                        continue
                    chave = nome.casefold()
                    info = registros.setdefault(chave, {
                        'nome': nome, 'ocorrencias': 0, 'locais': set(), 'detalhes': set(),
                    })
                    info['ocorrencias'] += 1
                    info['locais'].add(local['nome'])
                    info['detalhes'].add((local['nome'], zona.get('nome', ''),
                                         tabela.get('terreno', ''), encontro.get('origem', '')))
    return registros, especiais


def consultar_formas() -> tuple[dict[str, str], dict[str, str]]:
    from sqlalchemy import select
    from app import create_app
    from app.extensions import db
    from app.models.db import FormaPokemon
    app = create_app()
    with app.app_context():
        linhas = list(db.session.execute(select(FormaPokemon.nome, FormaPokemon.ativo)).all())
    ativas = {nome.strip().casefold(): nome.strip() for nome, ativo in linhas if nome and ativo}
    inativas = {nome.strip().casefold(): nome.strip() for nome, ativo in linhas if nome and not ativo}
    return ativas, inativas


def montar_linhas(registros: dict[str, dict], ativas: dict[str, str], inativas: dict[str, str]) -> list[dict]:
    ausentes = []
    for chave, item in registros.items():
        if chave in ativas:
            continue
        sugestoes = [ativas[k] for k in get_close_matches(chave, ativas.keys(), n=3, cutoff=0.62)]
        # Uma possível forma inativa não deve ser considerada como disponível.
        situacao = 'Existe apenas inativo' if chave in inativas else 'Sem nome correspondente ativo'
        ausentes.append({
            'pokemon': item['nome'],
            'situacao': situacao,
            'ocorrencias': item['ocorrencias'],
            'qtd_locais': len(item['locais']),
            'locais': '; '.join(sorted(item['locais'])),
            'sugestoes': '; '.join(sugestoes),
            'detalhes': '; '.join(' | '.join(t) for t in sorted(item['detalhes'])),
        })
    return sorted(ausentes, key=lambda x: x['pokemon'].casefold())


def main() -> int:
    if not ARQUIVO_ATLAS.exists():
        print(f'Atlas não encontrado: {ARQUIVO_ATLAS}', file=sys.stderr)
        return 2
    registros, especiais = coletar()
    try:
        ativas, inativas = consultar_formas()
    except Exception as e:
        print('Não foi possível consultar o catálogo de formas no PostgreSQL.', file=sys.stderr)
        print(f'{type(e).__name__}: {e}', file=sys.stderr)
        return 3
    ausentes = montar_linhas(registros, ativas, inativas)
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    csv_alvo = PASTA_SAIDA / 'pokemon_pendentes_ankar.csv'
    md_alvo = PASTA_SAIDA / 'pokemon_pendentes_ankar.md'
    with csv_alvo.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['pokemon','situacao','ocorrencias','qtd_locais','locais','sugestoes','detalhes'], delimiter=';')
        writer.writeheader()
        writer.writerows(ausentes)
    with md_alvo.open('w', encoding='utf-8') as f:
        f.write('# Pokémon sem correspondência de nome no catálogo ativo\n\n')
        f.write('Gerado em modo somente leitura: Atlas de Ankar × PostgreSQL local.\n\n')
        f.write(f'**{len(ausentes)} nomes sem correspondência ativa**, entre {len(registros)} nomes únicos de Pokémon.\n\n')
        f.write(f'Marcadores ignorados: X={especiais["marcador_x"]}, Random={especiais["random"]}, vazios={especiais["vazio"]}.\n\n')
        f.write('| Nome do Atlas | Ocorrências | Locais | Sugestões do catálogo |\n|---|---:|---|---|\n')
        for item in ausentes:
            def md(s): return str(s).replace('|', '\\|').replace('\n', ' ')
            f.write(f'| {md(item["pokemon"])} | {item["ocorrencias"]} | {md(item["locais"])} | {md(item["sugestoes"])} |\n')
        f.write('\n## Notas\n- Sugestões são aproximações de escrita, não correções automáticas.\n')
        f.write('- O Atlas só habilita geração para uma forma ativa cujo nome corresponda ao do encontro.\n')
        f.write('- A imagem exibida depende da URL configurada na forma correspondente.\n')
        f.write('- O relatório NÃO altera dados nem adiciona aliases.\n')
    print(f'Nomes distintos de Pokémon no Atlas: {len(registros)}')
    print(f'Formas ativas no banco: {len(ativas)}')
    print(f'Nomes sem correspondência ativa: {len(ausentes)}')
    print('Itens não-Pokémon ignorados: ' + ', '.join(f'{k}={v}' for k,v in especiais.items()))
    print(f'Relatórios: {md_alvo} e {csv_alvo}')
    if ausentes:
        print('\nPokémon pendentes por nome:')
        for item in ausentes:
            print(f'  - {item["pokemon"]} ({item["ocorrencias"]} registros; {item["qtd_locais"]} locais)')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
