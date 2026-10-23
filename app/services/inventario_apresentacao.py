"""Dados de apresentação da mochila, sem modificar o inventário persistido.

As cinco bolsas são agrupamentos visuais dos itens reais do catálogo.
O catálogo ainda não possui coluna 'bolsa'; por isso usamos categoria/nome,
com descrição apenas como último recurso. Nada é concedido por esta camada.
"""
from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from typing import Any

VERSAO_INTERFACE = "ui2-alinhamento-inventario-20261023"

BOLSAS = (
    {"codigo": "cura", "nome": "Cura", "icone": "icon-cura-hq.png", "arte": "bag-cura.png", "descricao": "Poções, remédios e itens de recuperação."},
    {"codigo": "pokebolas", "nome": "Pokébolas", "icone": "icon-pokebolas-hq.png", "arte": "bag-pokebolas.png", "descricao": "Esferas, acessórios de captura e itens relacionados."},
    {"codigo": "frutas", "nome": "Frutinhas", "icone": "icon-frutas-hq.png", "arte": "bag-frutas.png", "descricao": "Bagas, frutas e alimentos especiais para os Pokémon."},
    {"codigo": "avulsos", "nome": "Avulsos", "icone": "icon-avulsos-hq.png", "arte": "bag-avulsos.png", "descricao": "Objetos gerais, materiais soltos e itens utilitários."},
    {"codigo": "chave", "nome": "Item-chave", "icone": "icon-chave-hq.png", "arte": "bag-chave.png", "descricao": "Objetos importantes da jornada e da campanha."},
)


def _normalizar(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold()


def _contem(texto: str, palavras: Iterable[str]) -> bool:
    return any(palavra in texto for palavra in palavras)


def bolsa_item(item: Any) -> str:
    """Determina bolsa visual sem usar efeitos terapêuticos para reclassificar frutas.

    Ex.: 'Frutinha' com descrição 'Cura 20' continua sendo fruta.
    """
    categoria = getattr(item, "categoria", None)
    codigo_cat = _normalizar(getattr(categoria, "codigo", None))
    nome_cat = _normalizar(getattr(categoria, "nome", None))
    categoria_texto = f"{codigo_cat} {nome_cat}"
    nome = _normalizar(getattr(item, "nome", None))
    codigo = _normalizar(getattr(item, "codigo", None))
    identificacao = f"{nome} {codigo}"

    categorias = (
        ("chave", ("chave", "key-item", "keyitem", "quest", "missao", "insignia")),
        ("pokebolas", ("pokebola", "pokeball", "pokebola", "captura", "bola de captura")),
        ("frutas", ("baga", "berry", "fruta", "frutinha", "doce", "berry")),
        ("cura", ("cura", "pocao", "medic", "heal", "recupera", "restaura")),
    )
    for bolsa, palavras in categorias:
        if _contem(categoria_texto, palavras):
            return bolsa

    por_nome = (
        ("pokebolas", ("pokebola", "pokeball", "poke ball", "great ball", "ultra ball", "master ball", "premier ball", "captura")),
        ("frutas", ("baga", "berry", "frutinha", "fruta", "doce", "berry")),
        ("chave", ("chave", "key", "ticket", "ingresso", "fossil", "insignia")),
        ("cura", ("pocao", "revive", "antidoto", "super potion", "hyper potion", "potion", "restaurador")),
    )
    for bolsa, palavras in por_nome:
        if _contem(identificacao, palavras):
            return bolsa

    descricao = _normalizar(getattr(item, "descricao", None))
    if _contem(descricao, ("poção", "pocao", "restaura pv", "recupera pv", "recupera pontos de vida")):
        return "cura"
    return "avulsos"


def preparar_itens(inventario: Iterable[Any]) -> list[dict[str, Any]]:
    """Entrega a classificação visível junto do nome da bolsa.

    Assim o catálogo legado não mostra "Item avulso" sob a aba de Cura.
    A categoria original do item permanece intacta no banco.
    """
    nomes = {bolsa["codigo"]: bolsa["nome"] for bolsa in BOLSAS}
    resultado = []
    for registro in inventario:
        codigo = bolsa_item(registro.item)
        resultado.append({
            "registro": registro,
            "item": registro.item,
            "bolsa": codigo,
            "bolsa_nome": nomes.get(codigo, "Avulsos"),
        })
    return resultado


def preparar_equipe(pokemons: Iterable[Any], personagem: Any) -> list[dict[str, Any]]:
    """Tenta calcular PV máximo pelas regras atuais. Nunca fabrica PV máximo.

    Alguns catálogos de teste ainda podem ter dados incompletos: nesse caso
    exibimos somente PV atual, sem percentual enganoso.
    """
    equipe = [p for p in pokemons if p.localizacao == "equipe"]
    if not equipe:
        return []
    from app.services.pokemon_db_service import calcular_pokemon, carregar_regras_pokemon_db

    regras = carregar_regras_pokemon_db(personagem.campanha_id)
    resultado = []
    for pokemon in equipe:
        maximo = None
        try:
            valor = calcular_pokemon(pokemon, personagem, regras)["totais"].get("pv")
            maximo = int(valor) if valor and int(valor) > 0 else None
        except (AttributeError, TypeError, ValueError, ArithmeticError, KeyError):
            maximo = None
        atual = int(pokemon.pv_atual)
        percentual = round(max(0, min(100, atual * 100 / maximo))) if maximo else None
        resultado.append({"pokemon": pokemon, "pv_atual": atual, "pv_maximo": maximo, "percentual": percentual})
    return resultado
