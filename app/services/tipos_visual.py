"""Identidade visual dos tipos: mini-etiquetas textuais, sem imagens.

As regras e os códigos originais do catálogo não são modificados. Esta camada
apenas normaliza nomes/aliases conhecidos e devolve código visual + tradução.
Tipos personalizados preservam seu nome original e recebem estilo neutro.
"""
from __future__ import annotations

import re
import unicodedata

# Código CSS estável -> nome apresentado na interface / aliases do catálogo.
_TIPOS: dict[str, tuple[str, tuple[str, ...]]] = {
    "normal": ("Normal", ("normal",)),
    "fire": ("Fogo", ("fogo", "fire")),
    "water": ("Água", ("agua", "water")),
    "electric": ("Elétrico", ("eletrico", "electric")),
    "grass": ("Grama", ("grama", "planta", "grass")),
    "ice": ("Gelo", ("gelo", "ice")),
    "fighting": ("Lutador", ("lutador", "lutadora", "lutador(a)", "luta", "fighting")),
    "poison": ("Veneno", ("veneno", "poison")),
    "ground": ("Terra", ("terra", "ground")),
    "flying": ("Voador", ("voador", "voadora", "flying")),
    "psychic": ("Psíquico", ("psiquico", "psychic")),
    "bug": ("Inseto", ("inseto", "bug")),
    "rock": ("Pedra", ("pedra", "rocha", "rock")),
    "ghost": ("Fantasma", ("fantasma", "ghost")),
    "dragon": ("Dragão", ("dragao", "dragon")),
    "dark": ("Noturno", ("noturno", "sombrio", "escuro", "dark")),
    "steel": ("Metal", ("metal", "aco", "steel")),
    "fairy": ("Fada", ("fada", "fairy")),
}


def _normalizar(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor.strip().lower())
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"\s+", " ", texto)


_ALIASES = {
    _normalizar(alias): (codigo, nome)
    for codigo, (nome, aliases) in _TIPOS.items()
    for alias in aliases
}


def tipo_visual(tipo: str | None) -> dict[str, str]:
    """Retorna um identificador CSS seguro e o nome localizado para o selo.

    Nunca utiliza conteúdo do catálogo como classe CSS; novos tipos usam
    'personalizado', mas exibem o texto definido pelo mestre (autoescapado).
    """
    original = str(tipo or "").strip()
    encontrado = _ALIASES.get(_normalizar(original))
    if encontrado:
        codigo, nome = encontrado
        return {"codigo": codigo, "nome": nome}
    return {"codigo": "personalizado", "nome": original or "Sem tipo"}
