"""Identificação conservadora de materiais evolutivos de Ankar.

Não deduz itens a partir de texto narrativo livre. Usamos os códigos
oficiais (da importação versionada) e nomes conhecidos do manual
PKMRPG v2.5, capítulos 9/16. Item desconhecido impede a evolução,
mesmo com autorização, até revisão do mestre.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.consulta_evolucao_service import PEDRAS_COMUNS, _normalizar


@dataclass(frozen=True, slots=True)
class MaterialEvolucao:
    codigo: str
    nome: str
    aliases: frozenset[str]


# Mapeamento manual, sem inferir itens inexistentes em Ankar.
MATERIAIS_ESPECIAIS: dict[str, tuple[str, ...]] = {
    "galarica-cuff": ("Bracelete Galariano", "Bracelete de Galárica", "Galarica Cuff"),
    "galarica-wreath": ("Coroa Galariana", "Coroa de Galárica", "Galarica Wreath"),
    "up-grade": ("Atualização", "Upgrade", "Up-Grade"),
    "dubious-disc": ("Disco Dúbio", "Disco Duvidoso", "Dubious Disc"),
    "kings-rock": ("Pedra Rei", "King's Rock"),
    "metal-coat": ("Revestimento Metálico", "Metal Coat"),
    "dragon-scale": ("Escama de Dragão", "Dragon Scale"),
    "deep-sea-tooth": ("Presa Marinha", "Deep Sea Tooth"),
    "deep-sea-scale": ("Escama Marinha", "Deep Sea Scale"),
    "prism-scale": ("Escama Prismática", "Prism Scale"),
    "razor-claw": ("Garra Navalha", "Razor Claw"),
    "razor-fang": ("Presa Navalha", "Razor Fang"),
    "protector": ("Protetor", "Protector"),
    "electirizer": ("Eletrizador", "Electirizer"),
    "magmarizer": ("Magmarizador", "Magmarizer"),
    "reaper-cloth": ("Capa do Ceifador", "Reaper Cloth"),
    "oval-stone": ("Pedra Oval", "Oval Stone"),
    "sachet": ("Sachê", "Sachet"),
    "whipped-dream": ("Sonho Confeitado", "Whipped Dream"),
    "tart-apple": ("Maçã Azeda", "Tart Apple"),
    "sweet-apple": ("Maçã Doce", "Sweet Apple"),
    "cracked-pot": ("Bule Rachado", "Cracked Pot"),
    "strawberry-sweet": ("Docinho", "Strawberry Sweet"),
    "scroll-of-darkness": ("Pergaminho das Trevas", "Scroll of Darkness"),
    "scroll-of-waters": ("Pergaminho das Águas", "Scroll of Waters"),
}

MATERIAIS: dict[str, MaterialEvolucao] = {}
_ALIAS_TO_MATERIAL: dict[str, str] = {}
for nome, codigos in PEDRAS_COMUNS.items():
    codigo = codigos[0]
    apelidos = frozenset(_normalizar(x) for x in (nome, *codigos))
    MATERIAIS[codigo] = MaterialEvolucao(codigo, nome, apelidos)
    for alias in apelidos:
        _ALIAS_TO_MATERIAL[alias] = codigo
for codigo, nomes in MATERIAIS_ESPECIAIS.items():
    apelidos = frozenset(_normalizar(x) for x in (codigo, *nomes))
    MATERIAIS[codigo] = MaterialEvolucao(codigo, nomes[0], apelidos)
    for alias in apelidos:
        if alias in _ALIAS_TO_MATERIAL and _ALIAS_TO_MATERIAL[alias] != codigo:
            raise RuntimeError(f"Nome de material ambíguo: {alias}")
        _ALIAS_TO_MATERIAL[alias] = codigo


def material_por_identificador(identificador: str | None) -> MaterialEvolucao | None:
    if not identificador:
        return None
    codigo = _ALIAS_TO_MATERIAL.get(_normalizar(str(identificador)))
    return MATERIAIS.get(codigo) if codigo else None


def material_requerido_evolucao(tipo_requisito: str, req: dict[str, Any]) -> MaterialEvolucao | None:
    """Falha fechada se metadata anuncia material não reconhecido.

    Exige material quando qualquer dos campos oficiais o indicar,
    ou quando o tipo da relação for 'item'. Não confunde condições
    de tempo/local/amizade com materiais; essas são resolvidas pelo mestre.
    """
    identificadores = [
        req.get("item_especifico_pokeapi"),
        req.get("item_codigo_pokeapi"),
        req.get("item_nome"),
    ]
    encontrados = [str(x) for x in identificadores if x]
    if not encontrados:
        if tipo_requisito == "item" or (
            str(req.get("gatilho_pokeapi") or "") == "3"
            or (isinstance(req.get("detalhes_pokeapi"), dict)
                and req["detalhes_pokeapi"].get("held_item_id"))
        ):
            raise ValueError("Material evolutivo não identificado: revisão do mestre necessária.")
        return None
    materiais = [material_por_identificador(x) for x in encontrados]
    if any(m is None for m in materiais) or len({m.codigo for m in materiais if m}) != 1:
        raise ValueError("Material evolutivo desconhecido ou divergente: revisão do mestre necessária.")
    return materiais[0]


def item_corresponde_material(codigo: str, nome: str, material: MaterialEvolucao) -> bool:
    """Não usar correspondência parcial: evitar consumir objeto homônimo."""
    return (
        _normalizar(codigo) in material.aliases
        or _normalizar(nome) in material.aliases
    )


def item_e_material_evolutivo(item: Any) -> bool:
    """Pode ser descontado apenas pelo fluxo autorizado de evolução."""
    return bool(material_por_identificador(item.codigo)
                or material_por_identificador(item.nome))
