"""Seleção regional dos encontros de Ankar (sem alterar dados do Atlas).

O Atlas mantém a fonte original. Faixas reconstruídas, vazias, ambíguas ou
marcadas não são reinterpretadas: rolagens nessas posições são repetidas e
as exclusões ficam explícitas na prévia. Captura (%) não é peso de encontro.
"""
from __future__ import annotations

import random
import re

from app.services.regiao_ankar_service import carregar_catalogo_ankar


def localidades_ankar():
    return [
        {
            "id": loc["id"], "nome": loc["nome"], "tipo": loc.get("tipo", ""),
            "zonas": [
                {
                    "nome": z["nome"],
                    "tabelas": [{"terreno": t.get("terreno", "")} for t in z.get("tabelas", [])],
                } for z in loc.get("zonas", [])
            ],
        }
        for loc in carregar_catalogo_ankar().get("locais", [])
        if any(z.get("tabelas") for z in loc.get("zonas", []))
    ]


def selecionar_tabela(local_id, zona_index, tabela_index):
    try:
        zi, ti = int(zona_index), int(tabela_index)
        if str(zi) != str(zona_index).strip() or str(ti) != str(tabela_index).strip():
            raise ValueError
        if zi < 0 or ti < 0:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("Selecione uma zona e um terreno válidos.") from None
    local = next((x for x in carregar_catalogo_ankar().get("locais", [])
                  if x.get("id") == local_id), None)
    if not local:
        raise ValueError("Localidade inexistente no Atlas de Ankar.")
    try:
        zona = local["zonas"][zi]
        tabela = zona["tabelas"][ti]
    except (IndexError, KeyError, TypeError):
        raise ValueError("Zona ou terreno não encontrado nesta localidade.") from None
    return local, zona, tabela


_FAIXA = re.compile(r"^\s*(\d{1,3})\s*-\s*(\d{1,3})\s*$")


def rolagens_validas(tabela, nomes_habilitados=None):
    """Lista 1..100; None indica posição inválida/ambígua/não resolvida.

    Não usa a coluna 'captura' e não corrige sobreposições da planilha.
    """
    slots = [[] for _ in range(101)]
    excluidos = {"reconstruidos": 0, "invalidos": 0}
    for encontro in tabela.get("encontros", []):
        nome = str(encontro.get("pokemon") or "").strip()
        if encontro.get("marcador") or nome.casefold() in ("", "x", "random"):
            continue
        if encontro.get("faixa_reconstituida"):
            excluidos["reconstruidos"] += 1
            continue
        if encontro.get("faixa_valida") is False:
            excluidos["invalidos"] += 1
            continue
        match = _FAIXA.fullmatch(str(encontro.get("d100") or ""))
        if not match:
            excluidos["invalidos"] += 1
            continue
        inicio, fim = int(match[1]), int(match[2])
        if not (1 <= inicio <= fim <= 100):
            excluidos["invalidos"] += 1
            continue
        for resultado in range(inicio, fim + 1):
            slots[resultado].append(nome)
    unicos = [candidatos[0] if len(candidatos) == 1 else None for candidatos in slots[1:]]
    ambiguos = sum(len(candidatos) > 1 for candidatos in slots[1:])
    sem_atlas = sum(not candidatos for candidatos in slots[1:])
    sem_catalogo = 0
    if nomes_habilitados is not None:
        sem_catalogo = sum(nome is not None and nome not in nomes_habilitados for nome in unicos)
        unicos = [nome if nome in nomes_habilitados else None for nome in unicos]
    return unicos, {
        **excluidos,
        "rolagens_ambiguas": ambiguos,
        "rolagens_sem_faixa": sem_atlas,
        "rolagens_sem_forma": sem_catalogo,
    }


def sortear_especies(tabela, quantidade, *, nomes_habilitados, permitir_repetidos, rng=None):
    if not isinstance(quantidade, int) or not 1 <= quantidade <= 6:
        raise ValueError("A quantidade deve ser de 1 a 6 Pokémon.")
    slots, avisos = rolagens_validas(tabela, nomes_habilitados)
    especies = set(nome for nome in slots if nome)
    if not especies:
        raise ValueError("Esta tabela não possui encontros compatíveis e inequívocos com o catálogo Pokémon.")
    if not permitir_repetidos and len(especies) < quantidade:
        raise ValueError(
            f"Esta tabela oferece somente {len(especies)} espécies válidas e distintas. "
            "Reduza a quantidade ou permita repetições."
        )
    dado = rng or random.SystemRandom()
    escolhidos = []
    ja = set()
    tentativas = 0
    # 6 Pokémon em 100 faces; impedir loops e informar tabelas problemáticas.
    while len(escolhidos) < quantidade and tentativas < 10000:
        tentativas += 1
        rolagem = dado.randint(1, 100)
        nome = slots[rolagem - 1]
        if not nome or (not permitir_repetidos and nome in ja):
            continue
        ja.add(nome)
        escolhidos.append({"pokemon": nome, "d100": rolagem})
    if len(escolhidos) != quantidade:
        raise ValueError("Não foi possível completar o sorteio desta tabela. Ajuste os filtros.")
    avisos["rolagens_repetidas_ou_descartadas"] = tentativas - quantidade
    return escolhidos, avisos


def tabelas_de_ankar(*, local_id="", zona_index="", tabela_index=""):
    """Retorna tabelas de Ankar; localização/zona/terreno são filtros opcionais.

    Sem filtro: todas as rotas, cidades e pontos de interesse. A seleção de
    tabela é uniforme entre tabelas utilizáveis; dentro dela vale o d100.
    """
    local_id = str(local_id or "").strip()
    zi_raw = str(zona_index or "").strip()
    ti_raw = str(tabela_index or "").strip()
    if (zi_raw or ti_raw) and not local_id:
        raise ValueError("Escolha a localidade antes de filtrar zona ou terreno.")
    if ti_raw and not zi_raw:
        raise ValueError("Escolha uma zona antes de filtrar o terreno.")
    locais = carregar_catalogo_ankar().get("locais", [])
    if local_id:
        locais = [loc for loc in locais if loc.get("id") == local_id]
        if not locais:
            raise ValueError("Localidade inexistente no Atlas de Ankar.")
    candidatos = []
    for loc in locais:
        for zi, zona in enumerate(loc.get("zonas", [])):
            if zi_raw and str(zi) != zi_raw:
                continue
            for ti, tabela in enumerate(zona.get("tabelas", [])):
                if ti_raw and str(ti) != ti_raw:
                    continue
                candidatos.append({
                    "local_id": loc["id"], "local_nome": loc["nome"],
                    "zona_index": zi, "zona_nome": zona["nome"],
                    "tabela_index": ti, "terreno": str(tabela.get("terreno") or ""),
                    "tabela": tabela,
                })
    if not candidatos:
        raise ValueError("O filtro escolhido não possui tabelas de encontro.")
    return candidatos


def sortear_encontros_regionais(tabelas, quantidade, *, nomes_habilitados,
                                permitir_repetidos=False, rng=None, usados=None):
    """Sorteia pelas tabelas d100, não por espécie nem taxa de captura.

    Sorteia uma tabela válida uniformemente e então uma face de 1 a 100.
    Repete rolagens sem correspondência; preserva origem e o d100 da escolha.
    """
    if not isinstance(quantidade, int) or not 1 <= quantidade <= 6:
        raise ValueError("Escolha entre 1 e 6 Pokémon.")
    usados = set(usados or ())
    pools = []
    todos = set()
    alertas = {
        "rolagens_ambiguas": 0, "rolagens_sem_faixa": 0,
        "rolagens_sem_forma": 0, "reconstruidos": 0, "invalidos": 0,
        "tabelas_consultadas": len(tabelas),
    }
    for meta in tabelas:
        slots, avisos = rolagens_validas(meta["tabela"], nomes_habilitados)
        for campo in ("rolagens_ambiguas","rolagens_sem_faixa","rolagens_sem_forma",
                      "reconstruidos","invalidos"):
            alertas[campo] += avisos[campo]
        especies = set(x for x in slots if x)
        if especies:
            pools.append((meta, slots))
            todos.update(especies)
    if not pools:
        raise ValueError("Não há espécies com correspondência inequívoca nesse filtro de Ankar.")
    disponiveis = todos - usados
    if not permitir_repetidos and len(disponiveis) < quantidade:
        raise ValueError("O filtro não possui espécies distintas suficientes para a equipe.")
    rand = rng or random.SystemRandom()
    resultado, tentativas = [], 0
    while len(resultado) < quantidade and tentativas < 20000:
        tentativas += 1
        meta, slots = rand.choice(pools)
        face = rand.randint(1, 100)
        nome = slots[face - 1]
        if not nome or (not permitir_repetidos and nome in usados):
            continue
        usados.add(nome)
        resultado.append({
            "pokemon": nome, "d100": face, "local_id": meta["local_id"],
            "local_nome": meta["local_nome"], "zona_nome": meta["zona_nome"],
            "terreno": meta["terreno"],
        })
    if len(resultado) < quantidade:
        raise ValueError("Sorteio não concluído; reduza os filtros ou permita repetições.")
    alertas["rolagens_repetidas_ou_descartadas"] = tentativas - quantidade
    return resultado, alertas
