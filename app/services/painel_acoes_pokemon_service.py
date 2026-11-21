"""10E.4.1 — Ações de evolução/forma do painel expandido da equipe.

Somente leitura: usa regras existentes e não altera o Pokémon.
Não concede a permissão Mega: ela continua exclusiva do mestre.
"""
from __future__ import annotations

from app.services.consulta_evolucao_service import consultar_evolucoes_pokemon
from app.services.transformacoes_service import listar_formas_temporarias


def _resumir_forma(forma, shiny: bool) -> dict[str, str]:
    return {
        "id": str(forma.id),
        "nome": forma.nome,
        "imagem": (
            (forma.imagem_shiny_url if shiny else forma.imagem_url)
            or forma.imagem_url or forma.imagem_shiny_url or ""
        ),
    }


def carregar_acoes_equipe_dashboard(contexto, equipe: list[dict]) -> list[dict]:
    """Inclui apenas ações permitidas ao Pokémon daquela instância.

    Nunca usa autorização editorial do catálogo como permissão
    narrativa; o Campo não determina o direito a evoluir ou transformar.
    """
    if not equipe:
        return equipe
    personagem = contexto.personagem
    por_id = {
        str(pokemon.id): pokemon for pokemon in personagem.pokemons
        if pokemon.ativo and pokemon.localizacao == "equipe"
    }
    megas_ativas = {
        item.id for item in personagem.pokemons
        if item.ativo and item.tipo_transformacao == "mega"
    }
    for registro in equipe:
        pokemon = por_id.get(registro.get("pokemon", {}).get("id"))
        if pokemon is None:
            registro["acoes"] = {}
            continue
        consulta = consultar_evolucoes_pokemon(pokemon, personagem)
        formas = listar_formas_temporarias(pokemon)
        livre = pokemon.forma_temporaria_id is None
        registro["acoes"] = {
            "evolucoes": [
                {
                    "relacao_id": str(op.relacao_id),
                    "nome": op.destino_nome,
                    "imagem": op.destino_imagem or "",
                    "requisito": op.requisito_texto,
                    "pedra": op.pedra or "",
                }
                for op in consulta.opcoes
                if op.pode_evoluir and livre
            ],
            "alternativas": [
                _resumir_forma(forma, pokemon.shiny)
                for forma in formas["alternativas"]
            ] if pokemon.tipo_transformacao != "mega" else [],
            "megas": [
                _resumir_forma(forma, pokemon.shiny)
                for forma in formas["mega"]
            ] if pokemon.tipo_transformacao is None else [],
            "mega_habilitada": bool(personagem.mega_habilitada),
            "outra_mega_ativa": any(ativa != pokemon.id for ativa in megas_ativas),
            "tipo_transformacao": pokemon.tipo_transformacao,
            "forma_ativa": formas["atual"].nome if formas["atual"] else "",
            "pode_reverter": bool(pokemon.forma_temporaria_id),
            "pode_transformar": pokemon.pv_atual > 0,
        }
    return equipe
