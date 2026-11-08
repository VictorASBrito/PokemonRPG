"""Reconstrução REVERSÍVEL por backup, mas destrutiva no banco ao confirmar.

Padrão: SIMULAÇÃO. Não executa operações fora da campanha Ankar sem aprovação
explícita; verifica fontes, quantidades, itens equipados, e gera backup JSON.
USO: python scripts/reconstruir_catalogo_10c3.py
     python scripts/reconstruir_catalogo_10c3.py --aplicar --confirmar RECONSTRUIR-ANKAR [--descartar-naturezas]
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import sys
import uuid

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ))
from app import create_app
from app.extensions import db
from app.models.db import (Campanha, CategoriaItem, HistoricoAlteracao, Item, Personagem, PersonagemItem, Pokemon, StatusCondicao)
from sqlalchemy import func, select, text

MANIFESTO = RAIZ/'app/data/itens_padronizados_10c3.json'
PASTA_BACKUP = RAIZ/'relatorios/catalogo_10c3'
PREFIXO_IMAGEM = '/static/img/inventory/itens/'


def _arquivo_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    return path


def _foto(item):
    if not item: return None
    u = str(item.imagem_url or '').strip()
    return u if u not in {'None','null',''} else None


def _campos_item(item):
    return {k:getattr(item,k) for k in ('codigo','nome','descricao','imagem_url','preco','consumivel','equipavel','uso_em_batalha','efeitos','personalizado','ativo')}


def _resolver_efeitos(modelo, status_codes):
    bruto = modelo.get('efeitos_modelo')
    if not bruto:return None
    efeitos=[]
    for src in bruto['efeitos']:
        if src.get('codigos_status'):
            # Each entry uses UUID known to the admin editor; execution validates active status.
            for c in src['codigos_status']:
                obj = status_codes.get(c)
                if obj is None:
                    raise ValueError(f"Status {c!r} não existe na base ativa. Revise o catálogo antes da aplicação.")
                efeitos.append({'tipo':'remover_status','alvo':'pokemon','status_id':str(obj.id),'todos':False})
        else:efeitos.append(src)
    return {'versao':1,'efeitos':efeitos}


def simular_e_preparar(*, descartar_naturezas=False):
    manifesto=json.loads(MANIFESTO.read_text(encoding='utf-8'))
    campanha=db.session.scalar(select(Campanha).where(Campanha.codigo=='ankar',Campanha.ativo.is_(True)))
    if campanha is None:raise ValueError('Campanha Ankar não encontrada.')
    itens=list(db.session.execute(select(Item).order_by(Item.codigo)).scalars())
    if any(not item.ativo for item in itens):
        raise ValueError('Existem itens inativos; revise-os antes da reconstrução para não reativá-los.')
    registros=list(db.session.execute(select(PersonagemItem).order_by(PersonagemItem.personagem_id)).scalars())
    equipados=list(db.session.execute(select(Pokemon).where(Pokemon.item_equipado_id.is_not(None))).scalars())
    pessoas={p.id:p for p in db.session.execute(select(Personagem)).scalars()}
    codigos={x.codigo:x for x in itens}
    origens={x['origem']:x['destino'] for x in manifesto['origens']}
    desconhecidos=sorted(set(codigos)-set(origens))
    if desconhecidos:raise ValueError('Novos itens fora do manifesto; revisão obrigatória antes de aplicar: '+', '.join(desconhecidos))
    faltantes=sorted(set(origens)-set(codigos))
    if faltantes:raise ValueError('O banco já foi alterado desde o relatório; não reconstrua duas vezes. Códigos antigos ausentes: '+', '.join(faltantes[:15]))
    # Existing dependencies of ALL campaigns block the action; this operation is never global.
    outros=[p for p in registros if pessoas.get(p.personagem_id) is None or pessoas[p.personagem_id].campanha_id != campanha.id]
    outros_equipados=[p for p in equipados if pessoas.get(p.personagem_id) is None or pessoas[p.personagem_id].campanha_id != campanha.id]
    if outros or outros_equipados:raise ValueError('Catálogo também é usado por outras campanhas. Reestruturação bloqueada para preservar referências.')
    por_id={i.id:i for i in itens}
    if any(x.item_id not in por_id for x in registros):raise ValueError('Inventário com item não encontrado.')
    suspeitos=[r for r in registros if origens[por_id[r.item_id].codigo] is None and r.quantidade>0]
    suspeitos_equipados=[p for p in equipados if origens[por_id[p.item_equipado_id].codigo] is None]
    if suspeitos_equipados:raise ValueError('Existem naturezas falsas equipadas em Pokémon. Revise esses vínculos antes de reconstruir.')
    if suspeitos and not descartar_naturezas:
        detalhes=', '.join(f"{por_id[r.item_id].nome} ({r.quantidade})" for r in suspeitos)
        raise ValueError(f'Naturezas importadas presentes em inventários: {detalhes}. Para descartá-las intencionalmente, use --descartar-naturezas APÓS conferir o backup.')
    # All references are accounted for, including catalog and old custom image/description.
    grupos=collections.defaultdict(list)
    for i in itens:
        alvo=origens[i.codigo]
        if alvo:grupos[alvo].append(i)
    saida=collections.Counter()
    for r in registros:
        alvo=origens[por_id[r.item_id].codigo]
        if alvo:saida[(str(r.personagem_id),alvo)]+=int(r.quantidade)
    if any(r.quantidade<=0 for r in registros):raise ValueError('Existem quantidades inválidas. Execute inventario verificar primeiro.')
    status={s.codigo:s for s in db.session.execute(select(StatusCondicao).where(StatusCondicao.ativo.is_(True))).scalars()}
    novos=[]
    conflitos=[]
    for modelo in manifesto['padronizados']:
        codigo=modelo['codigo']; existentes=grupos.get(codigo,[])
        imgs=set(filter(None,(_foto(x) for x in existentes)))
        if len(imgs)>1:conflitos.append(f'{codigo}: imagens distintas: {sorted(imgs)}')
        efeitos_existentes={json.dumps(x.efeitos,ensure_ascii=False,sort_keys=True,default=str) for x in existentes if x.efeitos}
        if len(efeitos_existentes)>1 and codigo not in {'pocao','antidoto','despertador','cura-queimaduras','cura-congelamento','cura-paralisia'}:
            conflitos.append(f'{codigo}: efeitos distintos')
        arquivo=modelo.get('imagem_arquivo')
        candidato=(RAIZ/'static/img/inventory/itens'/arquivo) if arquivo else None
        url=(PREFIXO_IMAGEM+arquivo) if candidato is not None and candidato.is_file() else next(iter(imgs),None)
        efeitos=_resolver_efeitos(modelo,status)
        if efeitos is None and efeitos_existentes:
            efeitos=json.loads(next(iter(efeitos_existentes)))
        orig=existentes[0] if existentes else None
        novos.append(dict(modelo,categoria_codigo={'Pokébolas':'pokebolas','Cura':'cura','Frutas':'frutas','Item-chave':'item-chave','Avulsos':'avulsos'}[modelo['categoria']],imagem_url=url,descricao=modelo['descricao'] or next((x.descricao for x in existentes if x.descricao),None),efeitos=efeitos,preco=orig.preco if orig else 0,personalizado=all(x.personalizado for x in existentes) if existentes else True))
    if conflitos:raise ValueError('Divergências que exigem revisão manual: '+'; '.join(conflitos))
    # Current references and data fully captured as a recoverable JSON snapshot.
    backup={
        'gerado_em':dt.datetime.now(dt.timezone.utc).isoformat(),'campanha':'ankar',
        'itens':[{'id':str(i.id),**_campos_item(i),'categoria_id':str(i.categoria_id) if i.categoria_id else None} for i in itens],
        'categorias':[{'id':str(c.id),'codigo':c.codigo,'nome':c.nome,'descricao':c.descricao,'ativo':c.ativo} for c in db.session.execute(select(CategoriaItem)).scalars()],
        'inventarios':[{'id':str(r.id),'personagem_id':str(r.personagem_id),'item_id':str(r.item_id),'quantidade':r.quantidade} for r in registros],
        'equipados':[{'pokemon_id':str(p.id),'personagem_id':str(p.personagem_id),'item_id':str(p.item_equipado_id)} for p in equipados],
    }
    total_antes=sum(x.quantidade for x in registros)
    total_depois=sum(saida.values())
    removidas=sum(x.quantidade for x in suspeitos)
    if total_antes != total_depois + removidas:
        raise ValueError('Falha no balanço de inventário. Reconstrução bloqueada.')
    resumo={'catalogo_antes':len(itens),'catalogo_depois':len(novos),'linhas_inventario_antes':len(registros),'linhas_inventario_depois':len(saida),'unidades_antes':total_antes,'unidades_depois':total_depois,'unidades_suspeitas_descartadas':removidas,'equipados':len(equipados),'com_imagem':sum(bool(x['imagem_url']) for x in novos),'sem_imagem':sum(not x['imagem_url'] for x in novos)}
    return resumo, backup, novos, saida, itens, registros, equipados, origens


def aplicar(descartar_naturezas):
    # Bloqueia mudanças concorrentes na janela de manutenção (PostgreSQL).
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(text('LOCK TABLE itens, personagem_itens, pokemons IN SHARE ROW EXCLUSIVE MODE'))
    resumo,backup,novos,estoques,antigos,linhas,equipados,origens=simular_e_preparar(descartar_naturezas=descartar_naturezas)
    agora=dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_path=_arquivo_json(PASTA_BACKUP/f'backup-pre-reconstrucao-{agora}.json',backup)
    print('Backup gerado:',backup_path)
    ids_atuais={x.id:x.codigo for x in antigos}
    nome_categoria={'pokebolas':'Pokébolas','cura':'Cura','frutas':'Frutas','item-chave':'Item-chave','avulsos':'Avulsos'}
    categorias={c.codigo:c for c in db.session.execute(select(CategoriaItem)).scalars()}
    # Race checks must happen before deleting live items.
    for code in nome_categoria:
        if code not in categorias:
            c=CategoriaItem(codigo=code,nome=nome_categoria[code],ativo=True)
            db.session.add(c);categorias[code]=c
    db.session.flush()
    novos_por_codigo={}
    for d in novos:
        novo=Item(codigo=d['codigo'],nome=d['nome'],categoria_id=categorias[d['categoria_codigo']].id,
                  descricao=d['descricao'],imagem_url=d['imagem_url'],preco=d['preco'],
                  consumivel=d['consumivel'],equipavel=d['equipavel'],uso_em_batalha=d['uso_em_batalha'],
                  efeitos=d['efeitos'],personalizado=d['personalizado'],ativo=True)
        db.session.add(novo);novos_por_codigo[d['codigo']]=novo
    db.session.flush()
    migrados_equipados=[]
    for p in equipados:
        destino=origens[ids_atuais[p.item_equipado_id]]
        if destino is None:raise ValueError('Natureza equipada: operação bloqueada.')
        migrados_equipados.append((p,destino))
        p.item_equipado_id=None
    for row in linhas:db.session.delete(row)
    db.session.flush()
    for p in antigos:db.session.delete(p)
    db.session.flush()
    for (personagem_id,codigo),qtd in estoques.items():
        db.session.add(PersonagemItem(personagem_id=uuid.UUID(personagem_id),item_id=novos_por_codigo[codigo].id,quantidade=qtd))
    for p,codigo in migrados_equipados:p.item_equipado_id=novos_por_codigo[codigo].id
    db.session.add(HistoricoAlteracao(entidade='catalogo_itens',acao='reconstruir_10c3',registro_id=None,usuario_id=None,
      dados_anteriores={'catalogo':resumo['catalogo_antes'],'unidades':resumo['unidades_antes'],'backup':str(backup_path)},
      dados_novos={'catalogo':resumo['catalogo_depois'],'unidades':resumo['unidades_depois'],'descartadas':resumo['unidades_suspeitas_descartadas']}))
    db.session.commit()
    print('APLICADO. Resumo:',json.dumps(resumo,ensure_ascii=False))


def main():
    p=argparse.ArgumentParser(description='Reconstrói catálogo Ankar, com simulação padrão e backup obrigatório')
    p.add_argument('--aplicar',action='store_true')
    p.add_argument('--confirmar',default='')
    p.add_argument('--descartar-naturezas',action='store_true',help='Autoriza perder unidades de naturezas erroneamente importadas, gerando backup antes')
    args=p.parse_args()
    if args.aplicar and args.confirmar != 'RECONSTRUIR-ANKAR':p.error('Para aplicar, informe --confirmar RECONSTRUIR-ANKAR')
    app=create_app()
    with app.app_context():
        try:
            if args.aplicar:
                aplicar(args.descartar_naturezas)
            else:
                resumo,backup,novos,*_=simular_e_preparar(descartar_naturezas=args.descartar_naturezas)
                arquivo=_arquivo_json(PASTA_BACKUP/'simulacao.json',{'resumo':resumo,'plano':[{k:v for k,v in x.items() if k in ('codigo','nome','categoria','imagem_url','consumivel','equipavel','uso_em_batalha','efeitos','origens')} for x in novos]})
                print(json.dumps(resumo,ensure_ascii=False,indent=2));print('SIMULAÇÃO somente leitura do banco. Plano:',arquivo)
        except Exception as exc:
            db.session.rollback()
            print('BLOQUEADO:',str(exc),file=sys.stderr)
            raise SystemExit(2) from exc

if __name__=='__main__':main()
