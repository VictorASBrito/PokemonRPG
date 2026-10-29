"""Exibe os links das nove fichas configuradas (somente leitura, sem Flask)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def gerar_links(configuracao: Path, base: str = "http://127.0.0.1:5000") -> list[str]:
    doc = json.loads(configuracao.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not doc.get("habilitado") or len(doc.get("slots", [])) != 9:
        raise ValueError("Configure primeiro os nove slots ativos.")
    links = []
    for indice, slot in enumerate(doc["slots"], 1):
        login = str(slot.get("login") or "").strip().lower()
        if not login or not all(x.isascii() and (x.isalnum() or x in "_-." ) for x in login):
            raise ValueError(f"Slot {indice} contém login incompatível com URL.")
        links.append(f"{indice}. @{login}: {base.rstrip('/')}/p/{login}/")
    return links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:5000", help="Endereço público ou local do seu servidor")
    args = parser.parse_args()
    try:
        for linha in gerar_links(RAIZ / "data/entrada_personagens.json", args.base):
            print(linha)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
