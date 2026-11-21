"""Acervo visual de itens, sem acessar o banco de dados.

Busca no índice versionado; downloads são explícitos, na versão fixada.
Os ícones existentes de Ankar nunca são substituídos.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.request import urlopen

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "app/data"
LOCAL = RAIZ / "static/img/inventory/itens"
ACERVO = RAIZ / "static/img/inventory/acervo-pokeapi"
PNG = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1024 * 1024


def carregar_indice():
    return json.loads((DADOS / "acervo_icones_itens_11a.json").read_text(encoding="utf-8"))


def baixar(nome, indice, *, destino=ACERVO):
    if not re.fullmatch(r"[a-z0-9-]+\.png", nome) or nome not in indice["arquivos"]:
        raise ValueError(f"Ícone não consta no índice: {nome}")
    arquivo = destino / nome
    if arquivo.exists():
        if not arquivo.read_bytes().startswith(PNG):
            raise ValueError(f"Arquivo local inválido: {arquivo}")
        return "existente"
    commit = indice["commit"]
    url = f"https://raw.githubusercontent.com/PokeAPI/sprites/{commit}/sprites/items/{nome}"
    with urlopen(url, timeout=20) as resposta:
        conteudo = resposta.read(MAX_BYTES + 1)
    if len(conteudo) > MAX_BYTES or not conteudo.startswith(PNG):
        raise ValueError(f"Resposta não é um PNG válido no limite permitido: {nome}")
    destino.mkdir(parents=True, exist_ok=True)
    # Criação exclusiva: nunca sobrescrever um arquivo existente.
    with arquivo.open("xb") as saida:
        saida.write(conteudo)
    return "baixado"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    grupo = p.add_mutually_exclusive_group()
    grupo.add_argument("--buscar", help="Busca por nome de arquivo do acervo")
    grupo.add_argument("--baixar", nargs="+", metavar="PNG")
    grupo.add_argument("--baixar-lote", action="store_true",
                       help="Baixa somente os ícones externos do primeiro lote")
    args = p.parse_args()
    indice = carregar_indice()
    if args.baixar or args.baixar_lote:
        nomes = args.baixar
        if args.baixar_lote:
            dados = json.loads((DADOS / "novos_itens_11a.json").read_text(encoding="utf-8"))
            nomes = sorted({i["icone"] for i in dados["itens"]
                            if i["origem_icone"] == "pokeapi"})
        for nome in nomes:
            print(nome, baixar(nome, indice))
    else:
        print(f"Acervo: {len(indice['arquivos'])} PNGs indexados; commit {indice['commit']}")
        print(f"Ankar: {len(list(LOCAL.glob('*.png')))} PNGs próprios")
        if args.buscar:
            termo = args.buscar.lower().strip().replace(" ", "-")
            for nome in indice["arquivos"]:
                if termo in nome:
                    print(nome)


if __name__ == "__main__":
    main()
