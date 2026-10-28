"""Vínculos explícitos do Atlas com FormaPokemon (somente leitura).

Não altera pokemons.json nem o PostgreSQL. Nomes sem sufixo que podem apontar
para várias formas mantêm TODAS as opções para escolha do mestre.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Iterable, Any

CAMINHO_ALIASES = Path(__file__).resolve().parent.parent / 'data' / 'ankar_formas_aliases.json'


@lru_cache(maxsize=1)
def carregar_aliases() -> dict:
    with CAMINHO_ALIASES.open(encoding='utf-8') as arquivo:
        return json.load(arquivo)


def chave_nome(texto: str | None) -> str:
    # Normalização de acentos e espaços, não transforma Alola/Galar em forma base.
    sem_acentos = ''.join(c for c in unicodedata.normalize('NFKD', str(texto or ''))
                         if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', sem_acentos.casefold().strip())


def opcoes_formas(nome_planilha: str, formas: Iterable[Any]) -> list[dict[str, str]]:
    """Seleciona formas somente por códigos e nomes específicos verificados.

    Para alias conhecido, NÃO retornar espécie base quando o código regional
    estiver ausente. Para espécie simples, aceitar apenas nome exatamente igual.
    """
    nomes = carregar_aliases()['aliases']
    alias = nomes.get(nome_planilha)
    formas_ativas = [f for f in formas if f.ativo]
    opcoes = []
    if alias is not None:
        por_codigo = {chave_nome(f.codigo): f for f in formas_ativas}
        por_nome = {chave_nome(f.nome): f for f in formas_ativas}
        for opcao in alias:
            forma = por_codigo.get(chave_nome(opcao['codigo'])) or por_nome.get(chave_nome(opcao['nome']))
            if forma and str(forma.id) not in {i['id'] for i in opcoes}:
                opcoes.append({
                    'id': str(forma.id), 'codigo': str(forma.codigo),
                    'nome': str(forma.nome), 'imagem': forma.imagem_url or forma.imagem_shiny_url or '',
                })
    else:
        chave = chave_nome(nome_planilha)
        for f in formas_ativas:
            if chave_nome(f.nome) == chave:
                opcoes.append({
                    'id': str(f.id), 'codigo': str(f.codigo),
                    'nome': str(f.nome), 'imagem': f.imagem_url or f.imagem_shiny_url or '',
                })
                break
    return opcoes


def indices_formas_locais(nomes: Iterable[str], formas: Iterable[Any]) -> dict[str, dict]:
    """Prepara os dados dos cards em uma consulta de formas por local."""
    formas = list(formas)
    resultado = {}
    notas = carregar_aliases().get('notas', {})
    for nome in sorted(set(nomes), key=str.casefold):
        opcoes = opcoes_formas(nome, formas)
        if opcoes:
            principal = opcoes[0]
            resultado[str(nome).casefold()] = {
                **principal, 'opcoes': opcoes, 'quantidade': len(opcoes),
                'observacao': notas.get(nome, ''),
            }
    return resultado


def apelidos_pesquisa(nome: str) -> list[str]:
    """Termos adicionais para achar um local pelo nome da forma do catálogo."""
    alias = carregar_aliases()['aliases'].get(nome, [])
    return [i['nome'] for i in alias]
