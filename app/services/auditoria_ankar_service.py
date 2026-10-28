"""Leitor e auditor SOMENTE LEITURA da geografia e encontros de Ankar.

Nenhuma entrada e interpretada como encontro jogavel neste modulo. As faixas
invalidas, as datas automaticas e o marcador 'x' exigem revisao humana.
Nao ha importacao, persistencia, SQLAlchemy, ou gravacao de planilhas.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


_FAIXA = re.compile(r"^\s*(\d{1,3})\s*[-–—]\s*(\d{1,3})\s*$")
_ZONA = re.compile(r"^\s*ZONA\s+0*(\d+)\b", re.IGNORECASE)


@dataclass
class Achado:
    nivel: str
    codigo: str
    arquivo: str
    aba: str
    celula: str
    local: str
    zona: str | None
    terreno: str | None
    mensagem: str
    valor_original: str | None = None


@dataclass
class Entrada:
    celula_pokemon: str
    celula_d100: str
    pokemon: str | None
    captura_original: str | None
    d100_original: str | None
    inicio: int | None
    fim: int | None


@dataclass
class Tabela:
    arquivo: str
    aba: str
    local: str
    zona: str | None
    terreno: str
    cabecalho: str
    entradas: list[Entrada] = field(default_factory=list)


@dataclass
class Local:
    arquivo: str
    aba: str
    tipo: str
    nome: str
    habitat_principal: str | None
    habitat_secundario: str | None
    terrenos_informados: list[str]
    tempo_ou_tamanho: str | None
    acessos: list[str]
    zonas: list[str] = field(default_factory=list)


@dataclass
class Relatorio:
    locais: list[Local] = field(default_factory=list)
    tabelas: list[Tabela] = field(default_factory=list)
    achados: list[Achado] = field(default_factory=list)
    arquivos: list[str] = field(default_factory=list)

    @property
    def erros(self) -> int:
        return sum(a.nivel == "ERRO" for a in self.achados)

    @property
    def avisos(self) -> int:
        return sum(a.nivel == "AVISO" for a in self.achados)

    @property
    def entradas(self) -> int:
        return sum(len(t.entradas) for t in self.tabelas)

    def como_dict(self) -> dict[str, Any]:
        return {
            "modo": "somente_leitura",
            "arquivos": self.arquivos,
            "resumo": {
                "locais": len(self.locais), "tabelas": len(self.tabelas),
                "entradas": self.entradas, "erros": self.erros,
                "avisos": self.avisos,
            },
            "locais": [asdict(x) for x in self.locais],
            "tabelas": [asdict(x) for x in self.tabelas],
            "achados": [asdict(x) for x in self.achados],
        }

    def texto(self, *, limite: int | None = 50) -> str:
        linhas = [
            "Auditoria de Ankar — SOMENTE LEITURA (sem importacao, sem banco de dados)",
            f"Arquivos: {len(self.arquivos)} | Locais: {len(self.locais)} | "
            f"Tabelas: {len(self.tabelas)} | Entradas: {self.entradas}",
            f"Resultado: {self.erros} ERRO(S), {self.avisos} AVISO(S).",
        ]
        exibidos = self.achados if limite is None else self.achados[:limite]
        for item in exibidos:
            contexto = f"{item.arquivo} / {item.aba} / {item.celula}"
            if item.zona:
                contexto += f" / {item.zona}"
            if item.terreno:
                contexto += f" / {item.terreno}"
            original = f" [original: {item.valor_original}]" if item.valor_original is not None else ""
            linhas.append(f"[{item.nivel}] {item.codigo}: {contexto}: {item.mensagem}{original}")
        if limite is not None and len(self.achados) > limite:
            linhas.append(f"... mais {len(self.achados) - limite} achado(s); use --todos.")
        return "\n".join(linhas)


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    saida = str(valor).strip()
    return saida or None


def _original(valor: Any) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, (date, datetime)):
        return f"{type(valor).__name__}({valor.isoformat()})"
    return repr(valor)


def _valor(linha: tuple[Any, ...], coluna: int) -> Any:
    """Coluna 1-based; tolera linhas curtas e planilhas irregulares."""
    return linha[coluna - 1] if 0 < coluna <= len(linha) else None


def _linha(linhas: list[tuple[Any, ...]], numero: int) -> tuple[Any, ...]:
    return linhas[numero - 1] if 0 < numero <= len(linhas) else ()


def _geografia(arquivo: str, aba: str, origem: str,
               linhas: list[tuple[Any, ...]]) -> Local:
    r1, r2, r3, r4 = (_linha(linhas, i) for i in range(1, 5))
    nome = _texto(_valor(r1, 1)) or aba
    tipo = "rota" if origem == "rotas" else (
        "cidade_ginasio" if aba.startswith("GYM ") else
        "cidade_auxiliar" if aba.startswith("AUX ") else
        "ponto_interesse" if aba.startswith("P ") else "regiao"
    )
    cabecalhos = [(col, str(v).upper()) for col, v in enumerate(r3, 1) if isinstance(v, str)]
    terr_col = next((col for col, val in cabecalhos if "TIPOS DE TERRENO" in val), None)
    tempo_col = next((col for col, val in cabecalhos
                      if "TEMPO DE VIAGEM" in val or "TAMANHO" in val), None)
    acessos_col = next((col for col, val in cabecalhos if "ACESSOS" in val), None)
    terrenos: list[str] = []
    if terr_col:
        fim = min([c for c in (tempo_col, acessos_col) if c and c > terr_col] or [len(r4) + 1])
        terrenos = [_texto(_valor(r4, i)) for i in range(terr_col, fim)]
        terrenos = [v for v in terrenos if v]
    acessos = [_texto(v) for v in r4[acessos_col - 1:]] if acessos_col else []
    return Local(
        arquivo=arquivo, aba=aba, tipo=tipo, nome=nome,
        habitat_principal=_texto(_valor(r3, 3)),
        habitat_secundario=_texto(_valor(r4, 3)),
        terrenos_informados=terrenos,
        tempo_ou_tamanho=_texto(_valor(r4, tempo_col)) if tempo_col else None,
        acessos=[v for v in acessos if v],
    )


def _intervalo(valor: Any) -> tuple[int, int] | None:
    if isinstance(valor, bool) or isinstance(valor, (date, datetime)):
        return None
    if isinstance(valor, int) or (isinstance(valor, float) and valor.is_integer()):
        n = int(valor)
        return (n, n)
    if isinstance(valor, str):
        encontrado = _FAIXA.fullmatch(valor)
        if encontrado:
            return int(encontrado.group(1)), int(encontrado.group(2))
        if valor.strip().isdigit() and len(valor.strip()) <= 3:
            n = int(valor.strip())
            return n, n
    return None


def _captura_valida(valor: Any) -> bool:
    if isinstance(valor, bool) or isinstance(valor, (date, datetime)):
        return False
    try:
        texto = str(valor).strip().replace(",", ".")
        if texto.endswith("%"):
            texto = texto[:-1].strip()
        return 0 <= float(texto) <= 100
    except (TypeError, ValueError):
        return False


def _zonas(linhas: list[tuple[Any, ...]]) -> list[tuple[int, int, str]]:
    resultado = []
    for num, row in enumerate(linhas, 1):
        for col, valor in enumerate(row, 1):
            if isinstance(valor, str) and _ZONA.match(valor):
                resultado.append((num, col, valor.strip()))
    return resultado


def _zona_para(zonas: list[tuple[int, int, str]],
               linha_cabecalho: int, coluna_pokemon: int) -> str | None:
    elegiveis = [z for z in zonas if z[0] <= linha_cabecalho and z[1] < coluna_pokemon]
    # A zona declarada na mesma linha para a coluna correspondente tem prioridade;
    # zonas de linhas anteriores continuam valendo para outros terrenos.
    if elegiveis:
        return max(elegiveis, key=lambda z: (z[0], z[1]))[2]
    return None


def _anotar(relatorio: Relatorio, nivel: str, codigo: str, tab: Tabela | None,
            arquivo: str, aba: str, celula: str, mensagem: str,
            valor: Any = None) -> None:
    relatorio.achados.append(Achado(
        nivel=nivel, codigo=codigo, arquivo=arquivo, aba=aba,
        celula=celula, local=tab.local if tab else aba,
        zona=tab.zona if tab else None,
        terreno=tab.terreno if tab else None,
        mensagem=mensagem,
        valor_original=_original(valor),
    ))


def _validar_tabela(relatorio: Relatorio, tabela: Tabela) -> None:
    arquivo, aba = tabela.arquivo, tabela.aba
    validas = [e for e in tabela.entradas if e.inicio is not None and e.fim is not None
               and 1 <= e.inicio <= e.fim <= 100]
    for i, anterior in enumerate(validas):
        for atual in validas[i + 1:]:
            inicio = max(anterior.inicio, atual.inicio)
            fim = min(anterior.fim, atual.fim)
            if inicio <= fim:
                faixa = str(inicio) if inicio == fim else f"{inicio}-{fim}"
                _anotar(relatorio, "ERRO", "sobreposicao", tabela, arquivo, aba,
                        atual.celula_d100,
                        f"Faixa {faixa} pertence a {anterior.pokemon!r} "
                        f"({anterior.celula_d100}) e {atual.pokemon!r} "
                        f"({atual.celula_d100}).")
            if (anterior.pokemon and atual.pokemon and
                    anterior.pokemon.casefold() not in {"x", "random"} and
                    anterior.pokemon.casefold() == atual.pokemon.casefold()):
                _anotar(relatorio, "AVISO", "especie_repetida", tabela,
                        arquivo, aba, atual.celula_pokemon,
                        f"{atual.pokemon!r} repetido na mesma tabela; confirmar intencao.")

    cobertos = set()
    for e in validas:
        cobertos.update(range(e.inicio, e.fim + 1))
    faltantes = sorted(set(range(1, 101)) - cobertos)
    if faltantes:
        blocos = []
        inicio = fim = faltantes[0]
        for n in faltantes[1:]:
            if n == fim + 1:
                fim = n
            else:
                blocos.append(str(inicio) if inicio == fim else f"{inicio}-{fim}")
                inicio = fim = n
        blocos.append(str(inicio) if inicio == fim else f"{inicio}-{fim}")
        _anotar(relatorio, "AVISO", "lacunas_d100", tabela, arquivo, aba,
                tabela.cabecalho,
                f"Valores sem cobertura d100: {', '.join(blocos)}. "
                "Se houver intervalos invalidos, a lacuna e apenas aparente.")


def _ler_aba(relatorio: Relatorio, ws: Any, arquivo: str, origem: str) -> None:
    linhas = list(ws.iter_rows(values_only=True))
    nome_aba = ws.title
    local = _geografia(arquivo, nome_aba, origem, linhas)
    relatorio.locais.append(local)
    zonas = _zonas(linhas)
    local.zonas = list(dict.fromkeys(z[2] for z in zonas))
    cabecalhos: list[tuple[int, int, str]] = []
    for nr, row in enumerate(linhas, 1):
        for col, valor in enumerate(row, 1):
            if not (isinstance(valor, str) and valor.strip().casefold() == "d100"):
                continue
            nome_terreno = _texto(_valor(row, col - 1))
            if col < 3 or not nome_terreno:
                _anotar(relatorio, "ERRO", "cabecalho_incompleto", None,
                        arquivo, nome_aba, f"{get_column_letter(col)}{nr}",
                        "Cabecalho d100 sem coluna de terreno/Pokemon imediatamente anterior.", valor)
                continue
            cabecalhos.append((nr, col, nome_terreno))

    if not cabecalhos and local.tipo != "regiao":
        _anotar(relatorio, "AVISO", "sem_tabelas", None, arquivo, nome_aba,
                "A1", "Aba nao possui cabecalhos de encontro d100.")

    # Cada tabela usa a tripla (% Captura, Pokemon, d100). A localizacao
    # pode incluir varias zonas lado a lado, e tambem zonas em linhas distintas.
    for nr, col, terreno in cabecalhos:
        tabela = Tabela(arquivo, nome_aba, local.nome,
                        _zona_para(zonas, nr, col - 1), terreno,
                        f"{get_column_letter(col)}{nr}")
        relatorio.tabelas.append(tabela)
        for rownum in range(nr + 1, len(linhas) + 1):
            row = _linha(linhas, rownum)
            if any((isinstance(_valor(row, c), str) and
                    str(_valor(row, c)).strip().casefold() == "d100")
                   for c in (col,)):
                break
            # Um novo cabecalho de zona na faixa deste terreno encerra sua tabela.
            if any(z[0] == rownum and z[1] <= col - 2 for z in zonas):
                break
            captura, pokemon, dado = (_valor(row, c) for c in (col - 2, col - 1, col))
            if captura is None and pokemon is None and dado is None:
                break
            pos_pkm = f"{get_column_letter(col - 1)}{rownum}"
            pos_dado = f"{get_column_letter(col)}{rownum}"
            pos_capt = f"{get_column_letter(col - 2)}{rownum}"
            nome = _texto(pokemon)
            faixa = _intervalo(dado)
            entrada = Entrada(pos_pkm, pos_dado, nome, _original(captura),
                              _original(dado), faixa[0] if faixa else None,
                              faixa[1] if faixa else None)
            tabela.entradas.append(entrada)
            marcador_x = nome is not None and nome.casefold() == "x"
            if nome is not None and nome.casefold() in {"random", "aleatorio", "aleatório", "?", "???", "a definir"}:
                _anotar(relatorio, "AVISO", "nome_ambiguo", tabela, arquivo,
                        nome_aba, pos_pkm, "Campo Pokemon contem marcador nao identificado como especie.", pokemon)
            if marcador_x:
                _anotar(relatorio, "AVISO", "marcador_x", tabela, arquivo,
                        nome_aba, pos_pkm,
                        "Marcador 'x' ainda sem significado confirmado; nao converter em encontro vazio.", pokemon)
            elif nome is None:
                _anotar(relatorio, "ERRO", "pokemon_ausente", tabela, arquivo,
                        nome_aba, pos_pkm, "Nome do Pokemon ausente.", pokemon)
            if dado is None:
                _anotar(relatorio, "ERRO", "d100_ausente", tabela, arquivo,
                        nome_aba, pos_dado, "Intervalo d100 ausente.")
            elif faixa is None:
                codigo = ("data_excel" if isinstance(dado, (date, datetime)) else
                          "formula_d100" if isinstance(dado, str) and dado.startswith("=") else
                          "d100_invalido")
                _anotar(relatorio, "ERRO", codigo, tabela, arquivo, nome_aba,
                        pos_dado, "Valor d100 nao interpretavel sem revisao manual.", dado)
            elif faixa[0] > faixa[1]:
                _anotar(relatorio, "ERRO", "faixa_invertida", tabela,
                        arquivo, nome_aba, pos_dado, "Intervalo d100 invertido.", dado)
            elif faixa[0] < 1 or faixa[1] > 100:
                _anotar(relatorio, "ERRO", "fora_d100", tabela, arquivo,
                        nome_aba, pos_dado, "Intervalo fora de 1 a 100.", dado)
            if not marcador_x:
                if captura is None:
                    _anotar(relatorio, "AVISO", "captura_ausente", tabela,
                            arquivo, nome_aba, pos_capt,
                            "Percentual de captura ausente (nao e peso de encontro).")
                elif not _captura_valida(captura):
                    _anotar(relatorio, "ERRO", "captura_invalida", tabela,
                            arquivo, nome_aba, pos_capt,
                            "Percentual de captura nao numerico ou fora de 0-100.", captura)
        if not tabela.entradas:
            _anotar(relatorio, "ERRO", "tabela_vazia", tabela, arquivo,
                    nome_aba, tabela.cabecalho, "Cabecalho sem entradas de encontro.")
        else:
            _validar_tabela(relatorio, tabela)


def auditar_planilhas(rotas: str | Path, cidades: str | Path) -> Relatorio:
    """Audita os dois XLSX, sem modificar arquivos ou acessar PostgreSQL.

    Falhas de abertura/arquivo propagam ao chamador e sao tratadas pela CLI.
    """
    relatorio = Relatorio()
    for origem, caminho in (("rotas", rotas), ("cidades", cidades)):
        caminho = Path(caminho)
        arquivo = caminho.name
        workbook = load_workbook(caminho, read_only=True, data_only=False, keep_links=False)
        try:
            relatorio.arquivos.append(arquivo)
            for ws in workbook.worksheets:
                _ler_aba(relatorio, ws, arquivo, origem)
        finally:
            workbook.close()
    return relatorio
