"""Importação incremental do primeiro lote de itens de Ankar (11A).

Por padrão, simulação somente leitura. O catálogo é global. A aplicação
explícita cria apenas registros faltantes; nunca altera itens cadastrados,
quantidades, equipamentos ou personagens. Não reexecuta a reconstrução 10C.3.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from app import create_app
from app.extensions import db
from app.models.db import CategoriaItem, HistoricoAlteracao, Item, StatusCondicao
from app.services.consulta_evolucao_service import _normalizar
from app.services.materiais_evolucao_service import material_por_identificador
from sqlalchemy import select, text

DADOS = RAIZ / "app/data/novos_itens_11a.json"
CATEGORIAS = {"cura": "Cura", "item-chave": "Item-chave"}
PASTAS = {"local": "itens", "pokeapi": "acervo-pokeapi"}
CONFIRMACAO = "ADICIONAR-ITENS-11A"


def carregar_lote():
    return json.loads(DADOS.read_text(encoding="utf-8"))["itens"]


def _aliases(modelo):
    valores = {modelo["codigo"], modelo["nome"], *modelo["aliases"]}
    material = material_por_identificador(modelo["codigo"])
    if material:
        valores.update(material.aliases)
    return {_normalizar(v) for v in valores}


def _efeitos(modelo, status_ativos):
    efeitos = list(modelo.get("efeitos", []))
    for codigo in modelo.get("status", []):
        if codigo not in status_ativos:
            raise ValueError(f"Status ativo ausente: {codigo}")
        efeitos.append({
            "tipo": "remover_status", "alvo": "pokemon",
            "status_id": str(status_ativos[codigo].id), "todos": False,
        })
    return {"versao": 1, "efeitos": efeitos} if efeitos else None


def preparar(modelos=None, *, raiz=RAIZ):
    modelos = carregar_lote() if modelos is None else modelos
    itens = list(db.session.scalars(select(Item)).all())
    gatos = list(db.session.scalars(select(CategoriaItem)).all())
    status = {s.codigo: s for s in db.session.scalars(
        select(StatusCondicao).where(StatusCondicao.ativo.is_(True))
    )}
    plano = []
    codigos = set()
    for m in modelos:
        if m["codigo"] in codigos:
            raise ValueError(f"Código duplicado no lote: {m['codigo']}")
        codigos.add(m["codigo"])
        aliases = _aliases(m)
        existentes = [i for i in itens if _normalizar(i.codigo) in aliases
                      or _normalizar(i.nome) in aliases]
        registro = {"codigo": m["codigo"], "nome": m["nome"],
                    "funcionalidade": m["funcionalidade"], "preco": m["preco"]}
        if len(existentes) > 1:
            plano.append({**registro, "acao": "bloqueado",
                          "motivo": "Mais de um item corresponde aos aliases.",
                          "correspondencias": sorted(i.codigo for i in existentes)})
            continue
        if existentes:
            i = existentes[0]
            plano.append({**registro, "acao": "preservar",
                          "existente": i.codigo, "id": str(i.id),
                          "ativo_atual": i.ativo, "preco_atual": i.preco,
                          "consumivel_atual": i.consumivel,
                          "imagem_atual": i.imagem_url, "efeitos_atuais": i.efeitos,
                          "motivo": "Já cadastrado; revisar campos sem sobrescrever."})
            continue
        try:
            cat = m["categoria"]
            if cat not in CATEGORIAS:
                raise ValueError("Categoria fora do primeiro lote.")
            if m["funcionalidade"] not in {"cura", "evolucao"}:
                raise ValueError("Funcionalidade fora do primeiro lote.")
            if not isinstance(m["preco"], int) or m["preco"] < 0:
                raise ValueError("Preço inválido.")
            if Path(m["icone"]).name != m["icone"] or not m["icone"].endswith(".png"):
                raise ValueError("Nome de ícone inválido.")
            caminho = Path("static/img/inventory") / PASTAS[m["origem_icone"]] / m["icone"]
            imagem = raiz / caminho
            if not imagem.is_file() or not imagem.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError(f"Ícone local ausente ou inválido: {caminho.as_posix()}")
            categorias = [c for c in gatos if c.codigo == cat
                          or _normalizar(c.nome) == _normalizar(CATEGORIAS[cat])]
            if len(categorias) > 1 or any(not c.ativo for c in categorias):
                raise ValueError(f"Categoria ambígua ou inativa: {cat}")
            efeitos = _efeitos(m, status)
            if m["funcionalidade"] == "cura" and not efeitos:
                raise ValueError("Cura sem efeito automático.")
            if m["funcionalidade"] == "evolucao" and not material_por_identificador(m["codigo"]):
                raise ValueError("Material não reconhecido pela evolução.")
            plano.append({**registro, "acao": "criar", "categoria": cat,
                          "categoria_existente": str(categorias[0].id) if categorias else None,
                          "descricao": m["descricao"],
                          "imagem_url": "/" + caminho.as_posix(),
                          "efeitos": efeitos, "consumivel": True, "equipavel": False,
                          "uso_em_batalha": m["funcionalidade"] == "cura"})
        except (KeyError, ValueError) as exc:
            plano.append({**registro, "acao": "bloqueado", "motivo": str(exc)})
    return plano


def aplicar(modelos=None, *, raiz=RAIZ):
    """Transação única; qualquer bloqueio reverte toda a importação."""
    from uuid import UUID
    try:
        if db.engine.dialect.name == "postgresql":
            db.session.execute(text(
                "LOCK TABLE categorias_item, itens IN SHARE ROW EXCLUSIVE MODE"
            ))
        plano = preparar(modelos, raiz=raiz)
        if any(p["acao"] == "bloqueado" for p in plano):
            raise ValueError("Lote bloqueado. Revise a simulação; nenhuma criação aplicada.")
        categorias = {}
        for p in plano:
            if p["acao"] != "criar":
                continue
            codigo = p["categoria"]
            if codigo not in categorias:
                if p["categoria_existente"]:
                    categoria = db.session.get(CategoriaItem, UUID(p["categoria_existente"]))
                else:
                    categoria = CategoriaItem(codigo=codigo, nome=CATEGORIAS[codigo], ativo=True)
                    db.session.add(categoria)
                    db.session.flush()
                categorias[codigo] = categoria
            i = Item(
                codigo=p["codigo"], nome=p["nome"], categoria_id=categorias[codigo].id,
                descricao=p["descricao"], imagem_url=p["imagem_url"],
                preco=p["preco"], efeitos=p["efeitos"], consumivel=p["consumivel"],
                equipavel=p["equipavel"], uso_em_batalha=p["uso_em_batalha"],
                personalizado=False, ativo=True,
            )
            db.session.add(i)
            db.session.flush()
            db.session.add(HistoricoAlteracao(
                entidade="item", registro_id=i.id, usuario_id=None,
                acao="importar_catalogo_11a", dados_anteriores=None,
                dados_novos={"codigo": i.codigo, "nome": i.nome, "preco": i.preco,
                             "imagem_url": i.imagem_url, "efeitos": i.efeitos},
            ))
        db.session.commit()
        return plano
    except Exception:
        db.session.rollback()
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aplicar", action="store_true")
    p.add_argument("--confirmar", default="")
    p.add_argument("--somente", nargs="+", metavar="CODIGO",
                   help="Limita o lote a códigos explícitos, ex.: super-pocao max-pocao")
    args = p.parse_args()
    if args.aplicar and args.confirmar != CONFIRMACAO:
        p.error(f"Após backup e revisão, use --confirmar {CONFIRMACAO}.")
    modelos = carregar_lote()
    if args.somente:
        faltantes = set(args.somente) - {m["codigo"] for m in modelos}
        if faltantes:
            p.error("Códigos fora do lote: " + ", ".join(sorted(faltantes)))
        modelos = [m for m in modelos if m["codigo"] in args.somente]
    app = create_app()
    with app.app_context():
        try:
            plano = aplicar(modelos) if args.aplicar else preparar(modelos)
            print(json.dumps(plano, ensure_ascii=False, indent=2, default=str))
            if not args.aplicar:
                db.session.rollback()
            print("APLICADO" if args.aplicar else "SIMULAÇÃO — nenhum dado gravado")
        except Exception as exc:
            db.session.rollback()
            p.exit(2, f"BLOQUEADO: {exc}\n")


if __name__ == "__main__":
    main()
