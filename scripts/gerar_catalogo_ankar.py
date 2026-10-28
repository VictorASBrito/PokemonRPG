"""Gera um catálogo de leitura da região de Ankar a partir das planilhas oficiais.

Executar manualmente. Não altera os XLSX, banco de dados ou informações do jogo.
Uso:
 python scripts/gerar_catalogo_ankar.py --rotas "...xlsx" --cidades "...xlsx"

Esta rotina utiliza apenas a biblioteca padrão, lendo os valores brutos do XLSX.
Em especial, evita a conversão incorreta de faixas d100 para datas do Excel.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import unicodedata
from xml.etree import ElementTree as ET
from zipfile import ZipFile

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DOC_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
COL_RX = re.compile(r"([A-Z]+)(\d+)")
INTERVALO_RX = re.compile(r"^\s*(\d{1,3})\s*[-–—]\s*(\d{1,3})\s*$")
ZONA_RX = re.compile(r"^\s*ZONA\s*0*([0-9]+)\b", re.IGNORECASE)


def normalizar(s: str) -> str:
    txt = unicodedata.normalize("NFKD", str(s))
    return re.sub(r"[^a-z0-9]+", "-", "".join(c for c in txt if not unicodedata.combining(c)).lower()).strip("-")


def indice_coluna(ref: str) -> int:
    letras = COL_RX.match(ref).group(1)
    n = 0
    for letra in letras:
        n = n * 26 + ord(letra) - 64
    return n


def ref_celula(col: int, row: int) -> str:
    letras = ""
    while col:
        col, n = divmod(col - 1, 26)
        letras = chr(65 + n) + letras
    return f"{letras}{row}"


class LeitorXlsx:
    def __init__(self, caminho: Path):
        self.caminho = caminho
        self.zip = ZipFile(caminho)
        shared = []
        if "xl/sharedStrings.xml" in self.zip.namelist():
            root = ET.fromstring(self.zip.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{MAIN}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{MAIN}t")))
        self.shared = shared
        raiz = ET.fromstring(self.zip.read("xl/workbook.xml"))
        rels = ET.fromstring(self.zip.read("xl/_rels/workbook.xml.rels"))
        destinos = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        self.abas = []
        for s in raiz.find(f"{MAIN}sheets"):
            target = destinos[s.attrib[f"{DOC_REL}id"]].lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            self.abas.append((s.attrib["name"], target))

    def linhas(self, local_xml: str) -> dict[tuple[int, int], str | int | float]:
        raiz = ET.fromstring(self.zip.read(local_xml))
        saida = {}
        dados = raiz.find(f"{MAIN}sheetData")
        if dados is None:
            return saida
        for row in dados:
            for cell in row:
                if cell.tag != f"{MAIN}c":
                    continue
                ref = cell.get("r", "")
                match = COL_RX.fullmatch(ref)
                if not match:
                    continue
                r = int(match.group(2))
                c = indice_coluna(ref)
                tipo = cell.get("t")
                v = cell.find(f"{MAIN}v")
                if tipo == "inlineStr":
                    inline = cell.find(f"{MAIN}is")
                    valor = "".join(t.text or "" for t in inline.iter(f"{MAIN}t")) if inline is not None else ""
                elif v is None or v.text is None:
                    continue
                elif tipo == "s":
                    valor = self.shared[int(v.text)]
                elif tipo == "b":
                    valor = "Sim" if v.text == "1" else "Não"
                elif tipo in ("str", "e"):
                    valor = v.text
                else:
                    try:
                        valor = float(v.text)
                        if valor.is_integer():
                            valor = int(valor)
                    except ValueError:
                        valor = v.text
                if str(valor).strip():
                    saida[(r, c)] = valor
        return saida


def texto(val) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val).strip()


def faixa_d100(valor) -> tuple[str, bool, bool]:
    """Texto para exibição, recuperado de data, e faixa sintaticamente válida."""
    if valor is None or texto(valor) in {"", "-"}:
        return "", False, False
    recuperado = False
    if isinstance(valor, (int, float)) and 20000 <= valor < 100000:
        # As células com '1-10' foram gravadas pelo Excel como datas (dia/mês).
        data = datetime(1899, 12, 30) + timedelta(days=float(valor))
        exibido = f"{data.day}-{data.month}"
        recuperado = True
    else:
        exibido = texto(valor)
    match = INTERVALO_RX.fullmatch(exibido)
    if match:
        inicio, fim = map(int, match.groups())
        valido = 1 <= inicio <= fim <= 100
    else:
        valido = exibido.isdigit() and 1 <= int(exibido) <= 100
    return exibido, recuperado, valido


def cabecalho_tabela(celulas, r, c) -> bool:
    a = normalizar(texto(celulas.get((r, c))))
    meio = texto(celulas.get((r, c + 1)))
    d100 = normalizar(texto(celulas.get((r, c + 2))))
    return a in {"captura", "captura-pct"} or ("captura" in a and meio and d100 == "d100")


def obter(celulas, linha, coluna):
    return texto(celulas.get((linha, coluna)))


def classificar(nome_aba: str):
    n = nome_aba.strip().upper()
    if n.startswith("ROTA "):
        return "rota", "Rota"
    if n.startswith("GYM "):
        return "cidade", "Cidade de ginásio"
    if n.startswith("AUX "):
        return "cidade", "Cidade auxiliar"
    return "interesse", "Ponto de interesse"


def metadados(celulas, nome_aba, origem):
    nome = obter(celulas, 1, 1) or nome_aba
    tipo, categoria = classificar(nome_aba)
    principal = obter(celulas, 3, 3)
    secundario = obter(celulas, 4, 3)
    terrenos = []
    for col in range(5, 9):
        t = obter(celulas, 4, col)
        if t and t != "-" and t not in terrenos:
            terrenos.append(t)
    # Algumas planilhas têm terreno apenas em F4.
    valor_deslocamento = ""
    rotulo_deslocamento = ""
    for col in range(9, 12):
        rotulo = obter(celulas, 3, col)
        if any(k in normalizar(rotulo) for k in ("tempo", "viagem", "tamanho", "dias")):
            rotulo_deslocamento = rotulo
            valor_deslocamento = obter(celulas, 4, col)
            break
    coluna_acesso = next((c for c in range(11, 21) if normalizar(obter(celulas, 3, c)) == "acessos"), None)
    acessos = []
    if coluna_acesso:
        for col in range(coluna_acesso, 23):
            a = obter(celulas, 4, col)
            if a and a not in {"-", "x"}:
                acessos.append({"nome": a, "destino_id": None})
    desc_col = next((c for c in range(1, 17) if normalizar(obter(celulas, 6, c)) == "descricao"), None)
    descricao = obter(celulas, 7, desc_col) if desc_col else ""
    # Alguns registros possuem descrição com quebra de linha dentro da célula; conservar.
    return {"id": normalizar(nome_aba), "nome": nome, "aba": nome_aba.strip(), "origem": origem,
            "tipo": tipo, "categoria": categoria, "habitat_principal": principal,
            "habitat_secundario": secundario, "terrenos": terrenos,
            "deslocamento_rotulo": rotulo_deslocamento, "deslocamento_valor": valor_deslocamento,
            "acessos": acessos, "descricao": descricao, "zonas": [], "tabelas": 0,
            "encontros": 0, "pokemons_distintos": 0}


def extrair_local(celulas, nome_aba, origem):
    local = metadados(celulas, nome_aba, origem)
    max_linha = max((r for r, _ in celulas), default=0)
    max_coluna = max((c for _, c in celulas), default=0)
    headings = [(r, c, texto(v)) for (r, c), v in celulas.items()
                if isinstance(v, str) and ZONA_RX.match(v.strip())]
    headings.sort()
    blocos = []
    for r in range(1, max_linha + 1):
        for c in range(1, max_coluna - 1):
            if (r, c) not in celulas or not cabecalho_tabela(celulas, r, c):
                continue
            if normalizar(obter(celulas, r, c + 2)) != "d100":
                continue
            zona_atual = [h for h in headings if h[0] <= r and h[1] <= c]
            if zona_atual:
                zona = max(zona_atual, key=lambda h: (h[0], h[1]))[2]
            else:
                zona = "Área geral"
            terreno = obter(celulas, r, c + 1) or "Não identificado"
            proximos = [h[0] for h in headings if h[0] > r and (h[1] == 1 or h[1] == c)]
            outros_cabecalhos = [y for y in range(r + 1, max_linha + 1) if cabecalho_tabela(celulas, y, c)
                                 and normalizar(obter(celulas, y, c + 2)) == "d100"]
            limite = min(proximos + outros_cabecalhos + [max_linha + 1])
            entradas = []
            vazias_consecutivas = 0
            for y in range(r + 1, limite):
                p = celulas.get((y, c + 1))
                raw = celulas.get((y, c + 2))
                capt = celulas.get((y, c))
                if p is None and raw is None and capt is None:
                    vazias_consecutivas += 1
                    if vazias_consecutivas >= 2:
                        break
                    continue
                vazias_consecutivas = 0
                # Não confundir com textos de locais fora da tabela.
                if raw is None and p is None:
                    continue
                faixa, data_excel, sintaxe = faixa_d100(raw)
                pokemon = texto(p)
                if not faixa and not pokemon and capt is None:
                    continue
                if not faixa and pokemon and pokemon.lower() not in {"x"} and capt is None:
                    continue
                captura = float(capt) if isinstance(capt, (int, float)) else texto(capt)
                if isinstance(captura, float) and captura.is_integer():
                    captura = int(captura)
                entradas.append({"pokemon": pokemon, "d100": faixa, "captura": captura if captura != "" else None,
                                 "marcador": pokemon.lower() == "x", "faixa_reconstituida": data_excel,
                                 "faixa_valida": sintaxe, "origem": ref_celula(c + 1, y),
                                 "origem_d100": ref_celula(c + 2, y), "d100_original": texto(raw)})
            blocos.append({"zona": zona, "terreno": terreno, "coluna": c,
                           "cabecalho": ref_celula(c, r), "encontros": entradas})
    # Mesma zona tem vários terrenos, inclusive quando tabelas estão lado a lado.
    for bloco in blocos:
        nome_zona = bloco["zona"]
        zona = next((z for z in local["zonas"] if z["nome"] == nome_zona), None)
        if zona is None:
            zona = {"id": f"zona-{len(local['zonas']) + 1}", "nome": nome_zona, "tabelas": []}
            local["zonas"].append(zona)
        zona["tabelas"].append({k: v for k, v in bloco.items() if k != "zona"})
    local["terrenos_encontro"] = list(dict.fromkeys(b["terreno"] for b in blocos))
    local["pokemon_nomes"] = list(dict.fromkeys(e["pokemon"] for b in blocos for e in b["encontros"]
                                            if e["pokemon"] and not e["marcador"] and e["pokemon"].casefold() != "random"))
    local["tabelas"] = len(blocos)
    local["encontros"] = sum(len(b["encontros"]) for b in blocos)
    local["pokemons_distintos"] = len({e["pokemon"].casefold() for b in blocos for e in b["encontros"]
                                      if e["pokemon"] and not e["marcador"] and e["pokemon"].casefold() != "random"})
    return local


def relacionar_acessos(locais):
    aliases = {}
    for local in locais:
        aliases[normalizar(local["nome"])] = local["id"]
        aliases[normalizar(local["aba"])] = local["id"]
        match = re.search(r"CIDADE GINÁSIO\s+(\d+)\s+-\s+(.+)", local["nome"], re.I)
        if match:
            n, nome = match.groups()
            aliases[f"cidade-{int(n)}"] = local["id"]
            aliases[normalizar(nome)] = local["id"]
        match = re.search(r"CIDADE AUXILIAR\s+(\d+)\s+-\s+(.+)", local["nome"], re.I)
        if match:
            aliases[normalizar(match.group(2))] = local["id"]
    for local in locais:
        for acesso in local["acessos"]:
            raw = acesso["nome"]
            chave = normalizar(raw)
            destino = aliases.get(chave)
            if destino is None:
                destino = aliases.get(normalizar(re.sub(r"\([^)]*\)", "", raw)))
            if destino is None:
                match = re.fullmatch(r"cidade\s+0*(\d+)", raw, re.I)
                if match:
                    destino = aliases.get(f"cidade-{int(match.group(1))}")
            acesso["destino_id"] = destino


def montar_catalogo(rotas: Path, cidades: Path):
    locais = []
    guia = ""
    for path, eh_rotas in ((rotas, True), (cidades, False)):
        wb = LeitorXlsx(path)
        try:
            for nome_aba, origem_aba in wb.abas:
                celulas = wb.linhas(origem_aba)
                if not eh_rotas and normalizar(nome_aba) == "regiao-de-ankar":
                    guia = obter(celulas, 3, 2) or obter(celulas, 3, 1)
                    continue
                locais.append(extrair_local(celulas, nome_aba, path.name))
        finally:
            wb.zip.close()
    relacionar_acessos(locais)
    resumo = {"locais": len(locais), "rotas": sum(l["tipo"] == "rota" for l in locais),
              "cidades": sum(l["tipo"] == "cidade" for l in locais),
              "interesses": sum(l["tipo"] == "interesse" for l in locais),
              "tabelas": sum(l["tabelas"] for l in locais),
              "encontros": sum(l["encontros"] for l in locais)}
    return {"versao": 1, "fontes": [rotas.name, cidades.name],
            "observacao": "Dados preservados; este catálogo não corrige conflitos nem aplica regras de encontro/captura.",
            "apresentacao": guia, "resumo": resumo, "locais": locais}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rotas", required=True, type=Path)
    ap.add_argument("--cidades", required=True, type=Path)
    ap.add_argument("--saida", type=Path,
                    default=Path(__file__).resolve().parent.parent / "app/data/catalogo_ankar_visual.json")
    args = ap.parse_args(argv)
    for path in (args.rotas, args.cidades):
        if not path.is_file():
            ap.error(f"Planilha não encontrada: {path}")
    dados = montar_catalogo(args.rotas, args.cidades)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Catálogo visual gerado (somente leitura):", dados["resumo"])
    print("Arquivo:", args.saida)


if __name__ == "__main__":
    main()
