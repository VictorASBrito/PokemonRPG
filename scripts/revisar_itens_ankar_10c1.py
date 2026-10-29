"""Etapa 10C.1: relatório de catálogo/inventários, estritamente somente leitura.

Executar da raiz: python scripts/revisar_itens_ankar_10c1.py
Para conferência da origem congelada (NÃO do banco atual): --fonte-seed
Não faz alterações de ORM, não cria migrations e não distribui itens.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent

# Correspondências propostas. Não são aplicadas ao catálogo.
SINONIMOS = {
    "pokebola": "Poké Bola", "pokebolas": "Poké Bola", "pokeball": "Poké Bola",
    "pokeballs": "Poké Bola", "pokebolas": "Poké Bola",
    "grandebola": "Grande Bola", "greatball": "Grande Bola", "greatballs": "Grande Bola",
    "ultrabola": "Ultra Bola", "ultraball": "Ultra Bola", "ultrapokebola": "Ultra Bola",
    "pokedex": "Pokédex", "pocao": "Poção", "pocoes": "Poção",
    "antidoto": "Antídoto", "incubadoracomum": "Incubadora Comum",
    "despertador": "Despertador", "elixir": "Elixir",
    "curacongelamento": "Cura Congelamento", "curaparalisia": "Cura Paralisia",
}


def chave(nome: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", str(nome).casefold())
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]", "", sem_acento)


def sugestao(nome: str) -> str:
    return SINONIMOS.get(chave(nome), "")


def status_imagem(url: str | None, pasta_static: Path | None = None) -> str:
    if not url or not url.strip():
        return "sem imagem"
    u = url.strip()
    parsed = urlsplit(u)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return "externa (não verificada)"
    if not u.startswith("/static/") and not u.startswith("static/"):
        return "URL inválida ou caminho desconhecido"
    if pasta_static is None:
        return "local (não verificada)"
    rel = unquote(parsed.path).lstrip("/")
    rel = rel[7:] if rel.startswith("static/") else rel
    base = pasta_static.resolve()
    path = (base / rel).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return "caminho inseguro"
    return "local encontrada" if path.is_file() else "arquivo local ausente"


def escrever_csv(destino: Path, rows: list[dict], campos: list[str]) -> None:
    with destino.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=campos, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def exportar_relatorio(*, destino: Path, catalogo: list[dict], inventarios: list[dict], origem: str, pasta_static: Path | None = None) -> dict:
    destino.mkdir(parents=True, exist_ok=True)
    grupos: dict[str, set[str]] = defaultdict(set)
    contagens = Counter()
    for linha in inventarios:
        grupos[sugestao(linha["nome_item"]) or chave(linha["nome_item"])].add(linha["nome_item"])
        contagens[linha["nome_item"]] += int(linha["quantidade"])
    for linha in catalogo:
        nome = linha["nome"]
        grupos[sugestao(nome) or chave(nome)].add(nome)
        linha["sugestao_nome"] = sugestao(nome)
        linha["status_imagem"] = status_imagem(linha.get("imagem_url"), pasta_static)
    for linha in inventarios:
        linha["sugestao_nome"] = sugestao(linha["nome_item"])
    grupos_revisao = []
    for grupo, nomes in sorted(grupos.items()):
        if len(nomes) > 1:
            grupos_revisao.append({
                "grupo": grupo,
                "nomes_encontrados": " | ".join(sorted(nomes)),
                "quantidade_historica_ou_atual": sum(contagens[n] for n in nomes),
                "decisao": "REVISAR (não unificado)",
            })
    cols_cat = ["codigo", "nome", "categoria", "preco", "consumivel", "equipavel", "uso_em_batalha", "ativo", "personalizado", "imagem_url", "status_imagem", "sugestao_nome", "inventario_unidades", "equipados"]
    cols_inv = ["login", "personagem", "item_codigo", "nome_item", "categoria", "quantidade", "imagem_url", "sugestao_nome"]
    escrever_csv(destino / "catalogo_itens.csv", catalogo, cols_cat)
    escrever_csv(destino / "inventarios_por_jogador.csv", inventarios, cols_inv)
    escrever_csv(destino / "possiveis_duplicatas.csv", grupos_revisao, ["grupo", "nomes_encontrados", "quantidade_historica_ou_atual", "decisao"])
    imagens_pendentes = [x for x in catalogo if x["status_imagem"] not in {"local encontrada", "externa (não verificada)"}]
    escrever_csv(destino / "imagens_pendentes.csv", imagens_pendentes, cols_cat)
    # Modelos em branco: não representam alterações solicitadas/aprovadas.
    escrever_csv(destino / "modelo_novos_itens.csv", [], ["codigo", "nome", "categoria_codigo", "descricao", "preco", "consumivel", "equipavel", "uso_em_batalha", "imagem_url_ou_nome_arquivo", "observacoes"])
    escrever_csv(destino / "modelo_distribuicao.csv", [], ["login_jogador", "codigo_item", "quantidade_adicionar", "observacoes"])
    resumo = {
        "origem": origem, "registros_catalogo": len(catalogo),
        "registros_inventario": len(inventarios),
        "unidades_inventario": sum(int(i["quantidade"]) for i in inventarios),
        "jogadores": len(set(i["login"] for i in inventarios)),
        "grupos_para_revisar": len(grupos_revisao),
        "itens_sem_imagem_ou_local_invalido": len(imagens_pendentes),
        "imagens_externas_nao_verificadas": sum(i["status_imagem"] == "externa (não verificada)" for i in catalogo),
    }
    (destino / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    itens_problematicos = [x for x in catalogo if x["status_imagem"] in {"arquivo local ausente", "URL inválida ou caminho desconhecido", "caminho inseguro"}]
    texto = [
        "# Revisão de itens de Ankar — somente leitura", "",
        f"**Origem:** {origem}. Não representa mudanças aplicadas ao banco.", "",
        f"- {len(catalogo)} itens no catálogo consultado; {len(inventarios)} linhas de inventário e {resumo['unidades_inventario']} unidades.",
        f"- {len(grupos_revisao)} grupos de nomes para conferir.",
        f"- {len(imagens_pendentes)} registros sem imagem ou com imagem local que precisa de análise.",
        f"- {len(itens_problematicos)} URLs/caminhos locais problemáticos (sem validar links externos).", "",
        "## Critérios", "",
        "- NUNCA fundir códigos ou alterar quantidades automaticamente.",
        "- Equipamentos de Pokémon não podem ser descartados ao unificar nomes.",
        "- Itens narrativos e personalizados exigem aprovação individual.",
        "- Imagens externas só são classificadas como externas; disponibilidade não é verificada.",
        "- Antes de qualquer adição, identificar o item e o jogador pelos códigos/logins atuais.", "",
        "## Arquivos gerados", "",
        "`catalogo_itens.csv`, `inventarios_por_jogador.csv`, `possiveis_duplicatas.csv`, `imagens_pendentes.csv`,",
        "`modelo_novos_itens.csv`, `modelo_distribuicao.csv` e `resumo.json`.", "",
        "**Nenhum registro foi criado, corrigido ou distribuído.**", "",
    ]
    (destino / "LEIA_PRIMEIRO.md").write_text("\n".join(texto), encoding="utf-8")
    return resumo


def carregar_origem_seed(caminho: Path) -> tuple[list[dict], list[dict]]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    inventarios = []
    for jogador in dados["jogadores"]:
        for item in jogador.get("inventario", []):
            inventarios.append({
                "login": jogador["login"], "personagem": jogador["personagem"]["nome"],
                "item_codigo": "(origem sem código)", "nome_item": item["nome"], "categoria": "",
                "quantidade": item["quantidade"], "imagem_url": "",
            })
    return [], inventarios


def carregar_postgres(campanha_codigo: str):
    # Importar somente em modo banco: --fonte-seed dispensa o Flask.
    sys.path.insert(0, str(ROOT))
    from app import create_app
    from app.extensions import db
    from app.models.db import Campanha, CategoriaItem, Item, Personagem, PersonagemItem, Pokemon
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    app = create_app()
    with app.app_context():
        campanha = db.session.execute(select(Campanha).where(Campanha.codigo == campanha_codigo)).scalar_one_or_none()
        if campanha is None:
            raise ValueError(f"Campanha não encontrada: {campanha_codigo}")
        personagens = list(db.session.execute(select(Personagem).where(Personagem.campanha_id == campanha.id).options(selectinload(Personagem.usuario))).scalars())
        ids = {p.id for p in personagens}
        lookup = {p.id: p for p in personagens}
        itens = list(db.session.execute(select(Item).options(selectinload(Item.categoria))).scalars())
        registros = list(db.session.execute(select(PersonagemItem).where(PersonagemItem.personagem_id.in_(ids))).scalars()) if ids else []
        equipados = list(db.session.execute(select(Pokemon).where(Pokemon.personagem_id.in_(ids), Pokemon.item_equipado_id.is_not(None))).scalars()) if ids else []
        por_item = Counter()
        for r in registros: por_item[r.item_id] += r.quantidade
        qtd_equip = Counter(x.item_equipado_id for x in equipados)
        lookup_item = {i.id: i for i in itens}
        catalogo = [{"codigo": x.codigo, "nome": x.nome, "categoria": x.categoria.nome if x.categoria else "",
            "preco": x.preco, "consumivel": x.consumivel, "equipavel": x.equipavel,
            "uso_em_batalha": x.uso_em_batalha, "ativo": x.ativo,
            "personalizado": x.personalizado, "imagem_url": x.imagem_url or "",
            "inventario_unidades": por_item[x.id], "equipados": qtd_equip[x.id]} for x in itens]
        inventarios = []
        for r in registros:
            p, it = lookup[r.personagem_id], lookup_item.get(r.item_id)
            if it is None: continue  # catálogo inconsistente: diagnosticar com comando padrão
            inventarios.append({"login": p.usuario.login if p.usuario else "", "personagem": p.nome,
                "item_codigo": it.codigo, "nome_item": it.nome,
                "categoria": it.categoria.nome if it.categoria else "", "quantidade": r.quantidade, "imagem_url": it.imagem_url or ""})
        return catalogo, inventarios, Path(app.static_folder)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exportação apenas de leitura da revisão de itens de Ankar.")
    parser.add_argument("--campanha", default="ankar", help="Código da campanha")
    parser.add_argument("--fonte-seed", action="store_true", help="Usar JSON histórico, NÃO o PostgreSQL atual")
    parser.add_argument("--saida", type=Path, default=None)
    args = parser.parse_args()
    if args.fonte_seed:
        origem = "JSON histórico congelado, NÃO catálogo/banco atual"
        cat, inv = carregar_origem_seed(ROOT / "app/seed/fichas_jogadores_ankar.json")
        destino = args.saida or ROOT / "relatorios/revisao_itens_ankar_seed"
        pasta_static = None
    else:
        origem = f"PostgreSQL ativo, campanha {args.campanha}"
        cat, inv, pasta_static = carregar_postgres(args.campanha)
        destino = args.saida or ROOT / "relatorios/revisao_itens_ankar"
    res = exportar_relatorio(destino=destino, catalogo=cat, inventarios=inv, origem=origem, pasta_static=pasta_static)
    print(f"Relatórios gerados em: {destino}")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print("SOMENTE LEITURA — nenhum item ou inventário foi alterado.")


if __name__ == "__main__":
    main()
