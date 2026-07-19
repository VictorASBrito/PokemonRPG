from __future__ import annotations

from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    Atributo,
    Campanha,
    FormaPokemon,
    Golpe,
    Natureza,
    Personagem,
    Pokemon,
    StatusCondicao,
    TipoPokemon,
    Usuario,
)


class ValidacaoImportacao:
    def __init__(self, fontes) -> None:
        self.fontes = fontes

    @staticmethod
    def _contar(modelo) -> int:
        return int(db.session.execute(select(func.count()).select_from(modelo)).scalar_one())

    def executar(self) -> dict:
        fonte = self.fontes.analisar()
        banco = {
            "usuarios": self._contar(Usuario),
            "campanhas": self._contar(Campanha),
            "jogadores": self._contar(Personagem),
            "pokemon_jogadores": self._contar(Pokemon),
            "formas_pokemon": self._contar(FormaPokemon),
            "golpes": self._contar(Golpe),
            "tipos": self._contar(TipoPokemon),
            "naturezas": self._contar(Natureza),
            "status": self._contar(StatusCondicao),
            "atributos": self._contar(Atributo),
        }
        comparacoes = {}
        divergencias = []
        for chave, valor_fonte in fonte.items():
            if chave == "avisos" or chave == "categorias_golpe":
                continue
            valor_banco = banco.get(chave)
            if valor_banco is None:
                continue
            ok = valor_fonte == valor_banco
            comparacoes[chave] = {
                "fonte": valor_fonte,
                "banco": valor_banco,
                "ok": ok,
            }
            if not ok:
                divergencias.append(
                    f"{chave}: fonte {valor_fonte} | banco {valor_banco}"
                )
        return {
            "sucesso": not divergencias,
            "comparacoes": comparacoes,
            "divergencias": divergencias,
            "avisos": fonte.get("avisos", []),
        }
