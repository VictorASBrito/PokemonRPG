from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS}


def slugificar(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(ch for ch in normalizado if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acentos).strip("-").lower()
    return slug or "registro"


def _shared_strings(arquivo: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in arquivo.namelist():
        return []

    raiz = ET.fromstring(arquivo.read("xl/sharedStrings.xml"))
    return [
        "".join(t.text or "" for t in si.iter(f"{{{MAIN_NS}}}t"))
        for si in raiz
    ]


def _mapa_planilhas(arquivo: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(arquivo.read("xl/workbook.xml"))
    relacoes = ET.fromstring(arquivo.read("xl/_rels/workbook.xml.rels"))
    mapa_relacoes = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relacoes.findall(f"{{{PKG_REL_NS}}}Relationship")
    }

    resultado: dict[str, str] = {}
    planilhas = workbook.find("m:sheets", NS)
    if planilhas is None:
        return {}
    for planilha in planilhas:
        rel_id = planilha.attrib[f"{{{REL_NS}}}id"]
        destino = mapa_relacoes[rel_id]
        if not destino.startswith("xl/"):
            destino = f"xl/{destino}"
        resultado[planilha.attrib["name"]] = destino
    return resultado


def _valor_celula(celula: ET.Element, compartilhadas: list[str]) -> Any:
    tipo = celula.attrib.get("t")
    valor = celula.find("m:v", NS)

    if tipo == "inlineStr":
        return "".join(t.text or "" for t in celula.iter(f"{{{MAIN_NS}}}t"))
    if valor is None or valor.text is None:
        return ""
    if tipo == "s":
        return compartilhadas[int(valor.text)]
    if tipo == "b":
        return valor.text == "1"
    return valor.text


def ler_planilha(caminho: Path, nome_planilha: str) -> list[dict[str, Any]]:
    with ZipFile(caminho) as arquivo:
        mapa = _mapa_planilhas(arquivo)
        if nome_planilha not in mapa:
            raise ValueError(f"Planilha '{nome_planilha}' não encontrada em {caminho.name}.")

        compartilhadas = _shared_strings(arquivo)
        raiz = ET.fromstring(arquivo.read(mapa[nome_planilha]))
        linhas: list[dict[str, Any]] = []

        for linha in raiz.findall(".//m:sheetData/m:row", NS):
            dados: dict[str, Any] = {}
            for celula in linha.findall("m:c", NS):
                referencia = celula.attrib.get("r", "")
                coluna = re.match(r"[A-Z]+", referencia)
                if coluna:
                    dados[coluna.group(0)] = _valor_celula(celula, compartilhadas)
            if dados:
                linhas.append(dados)
        return linhas


def _inteiro(valor: Any, padrao: int = 0) -> int:
    try:
        return int(float(str(valor).replace(",", ".")))
    except (TypeError, ValueError):
        return padrao


def _decimal(valor: Any, padrao: float = 0.0) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return padrao


def _ids_unicos(nomes: list[str]) -> list[str]:
    contagem: dict[str, int] = {}
    resultado: list[str] = []
    for nome in nomes:
        base = slugificar(nome)
        contagem[base] = contagem.get(base, 0) + 1
        resultado.append(base if contagem[base] == 1 else f"{base}-{contagem[base]}")
    return resultado


def importar_pokemons(caminho_ficha: Path) -> dict[str, Any]:
    linhas = ler_planilha(caminho_ficha, "Pokemons")
    validas = [
        linha
        for linha in linhas
        if str(linha.get("A", "")).strip() not in {"", "-"}
    ]
    nomes = [str(linha["A"]).strip() for linha in validas]
    ids = _ids_unicos(nomes)

    pokemons: list[dict[str, Any]] = []
    for indice, (linha, registro_id) in enumerate(zip(validas, ids), start=1):
        tipos = [parte.strip() for parte in str(linha.get("B", "")).split("/") if parte.strip()]
        pokemons.append(
            {
                "id": registro_id,
                "ordem_catalogo": indice,
                "nome": str(linha.get("A", "")).strip(),
                "tipos": tipos,
                "atributos_base": {
                    "pv": _inteiro(linha.get("C")),
                    "ataque": _inteiro(linha.get("D")),
                    "defesa": _inteiro(linha.get("E")),
                    "ataque_especial": _inteiro(linha.get("F")),
                    "defesa_especial": _inteiro(linha.get("G")),
                    "velocidade": _inteiro(linha.get("H")),
                },
                "experiencia_base": _inteiro(linha.get("I")),
                "taxa_captura": _decimal(linha.get("J")),
                "imagem": str(linha.get("K", "")).strip(),
                "imagem_shiny": str(linha.get("L", "")).strip(),
            }
        )

    return {
        "schema_version": 1,
        "versao_sistema": "2.5",
        "origem": caminho_ficha.name,
        "total": len(pokemons),
        "pokemons": pokemons,
    }


def _precisao(valor: Any) -> int | None:
    texto = str(valor).strip()
    if not texto or texto == "-":
        return None
    try:
        if texto.endswith("%"):
            return int(round(float(texto[:-1].replace(",", "."))))
        numero = float(texto.replace(",", "."))
        if 0 <= numero <= 1:
            numero *= 100
        return int(round(numero))
    except ValueError:
        return None


def importar_golpes(caminho_ficha: Path) -> dict[str, Any]:
    linhas = ler_planilha(caminho_ficha, "Golpes")
    validas = [
        linha
        for linha in linhas
        if str(linha.get("A", "")).strip() not in {"", "-"}
    ]
    nomes = [str(linha["A"]).strip() for linha in validas]
    ids = _ids_unicos(nomes)

    golpes: list[dict[str, Any]] = []
    for indice, (linha, registro_id) in enumerate(zip(validas, ids), start=1):
        golpes.append(
            {
                "id": registro_id,
                "ordem_catalogo": indice,
                "nome": str(linha.get("A", "")).strip(),
                "tipo": str(linha.get("B", "")).strip(),
                "categoria": str(linha.get("C", "")).strip(),
                "custo_pp": _inteiro(linha.get("D")),
                "dano": str(linha.get("E", "-")).strip() or "-",
                "precisao": _precisao(linha.get("F")),
                "precisao_texto": str(linha.get("F", "-")).strip() or "-",
                "efeito": str(linha.get("G", "")).strip(),
            }
        )

    return {
        "schema_version": 1,
        "versao_sistema": "2.5",
        "origem": caminho_ficha.name,
        "total": len(golpes),
        "golpes": golpes,
    }


def salvar(caminho: Path, dados: dict[str, Any]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Converte os catálogos da Ficha Editável v2.5 para JSON."
    )
    parser.add_argument("ficha", type=Path, help="Caminho da Ficha Editável v2.5.xlsx")
    parser.add_argument(
        "--destino",
        type=Path,
        default=Path("data/catalogo"),
        help="Pasta onde pokemons.json e golpes.json serão gerados.",
    )
    argumentos = parser.parse_args()

    salvar(argumentos.destino / "pokemons.json", importar_pokemons(argumentos.ficha))
    salvar(argumentos.destino / "golpes.json", importar_golpes(argumentos.ficha))
    print(f"Catálogos gerados em {argumentos.destino.resolve()}")


if __name__ == "__main__":
    main()
