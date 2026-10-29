"""Seleciona explicitamente as nove contas de jogador exibidas na entrada visual.

python scripts/configurar_entrada_personagens.py listar
python scripts/configurar_entrada_personagens.py auto   # apenas se houver EXATAMENTE nove
python scripts/configurar_entrada_personagens.py definir login1 ... login9
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from app import create_app
from app.services.entrada_personagens_service import candidatos_a_slots, caminho_configuracao


def definir(logins: list[str], *, sobrescrever: bool = False, campanha_codigo: str = "ankar"):
    candidatos = {login.lower(): nome for login, nome in candidatos_a_slots(campanha_codigo=campanha_codigo)}
    nomes = [login.strip().lower() for login in logins]
    if len(nomes) != 9 or len(set(nomes)) != 9:
        raise ValueError("Informe exatamente nove logins distintos.")
    invalidos = [n for n in nomes if n not in candidatos]
    if invalidos:
        raise ValueError(f"Logins não elegíveis como jogador comum ativo: {', '.join(invalidos)}")
    destino = caminho_configuracao()
    if destino.exists() and not sobrescrever:
        raise ValueError("Configuração já existe. Use --substituir após revisar os logins.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        shutil.copy2(destino, destino.with_suffix(".json.bak"))
    corpo = {
        "versao": 1,
        "habilitado": True,
        "slots": [
            {"login": login, "sprite": f"img/login-personagens/slot-{i:02}.png"}
            for i, login in enumerate(nomes, start=1)
        ],
    }
    destino.write_text(json.dumps(corpo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Configuração criada:", destino)
    for indice, login in enumerate(nomes, start=1):
        print(f"  {indice}. {candidatos[login]} (@{login}) — slot-{indice:02}.png")
    print("Sem imagem de sprite, será usada a foto_url existente na ficha; se ausente, inicial.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="operacao", required=True)
    comandos.add_parser("listar", help="Lista candidatos, sem configurar nada")
    auto = comandos.add_parser("auto", help="Configura apenas se houver exatamente 9 candidatos")
    defp = comandos.add_parser("definir", help="Define explicitamente os nove jogadores")
    defp.add_argument("logins", nargs=9, metavar="LOGIN")
    for item in (auto, defp):
        item.add_argument("--substituir", action="store_true", help="Faz backup antes de substituir configuração existente")
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        codigo = str(app.config["CAMPANHA_PADRAO"])
        candidatos = candidatos_a_slots(campanha_codigo=codigo)
        if args.operacao == "listar":
            print(f"Jogadores elegíveis ({len(candidatos)}):")
            for login, nome in candidatos:
                print(f"  @{login} — {nome}")
            print("Perfis de mestre, administrador e tester não são elegíveis.")
            return
        if args.operacao == "auto":
            if len(candidatos) != 9:
                raise SystemExit(f"Encontrados {len(candidatos)} jogadores elegíveis, não 9. Use 'listar' e depois 'definir' para impedir uma seleção incorreta.")
            nomes = [login for login, _ in candidatos]
        else:
            nomes = args.logins
        definir(nomes, sobrescrever=args.substituir, campanha_codigo=codigo)


if __name__ == "__main__":
    main()
