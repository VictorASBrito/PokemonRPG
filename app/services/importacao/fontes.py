from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.json_service import ler_json


@dataclass(slots=True)
class FontesImportacao:
    data_dir: Path
    usuarios: dict[str, Any] = field(init=False)
    catalogo_pokemons: dict[str, Any] = field(init=False)
    catalogo_golpes: dict[str, Any] = field(init=False)
    regras_pokemon: dict[str, Any] = field(init=False)
    regras_treinador: dict[str, Any] = field(init=False)
    campanhas: list[dict[str, Any]] = field(init=False, default_factory=list)
    jogadores: list[dict[str, Any]] = field(init=False, default_factory=list)
    avisos: list[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.usuarios = ler_json(self.data_dir / "usuarios.json", {"usuarios": []})
        self.catalogo_pokemons = ler_json(
            self.data_dir / "catalogo" / "pokemons.json", {"pokemons": []}
        )
        self.catalogo_golpes = ler_json(
            self.data_dir / "catalogo" / "golpes.json", {"golpes": []}
        )
        self.regras_pokemon = ler_json(
            self.data_dir / "catalogo" / "regras_pokemon.json", {}
        )
        self.regras_treinador = ler_json(
            self.data_dir / "catalogo" / "regras_treinador.json", {}
        )
        self._carregar_campanhas()

    def _carregar_campanhas(self) -> None:
        pasta = self.data_dir / "campanhas"
        if not pasta.exists():
            self.avisos.append("A pasta data/campanhas não foi encontrada.")
            return

        jogadores_por_id: dict[str, dict[str, Any]] = {}
        for pasta_campanha in sorted(item for item in pasta.iterdir() if item.is_dir()):
            arquivo_campanha = pasta_campanha / "campanha.json"
            if not arquivo_campanha.exists():
                self.avisos.append(
                    f"Campanha ignorada: {pasta_campanha.name} não possui campanha.json."
                )
                continue

            campanha = ler_json(arquivo_campanha, {})
            campanha["_pasta"] = pasta_campanha
            self.campanhas.append(campanha)

            ids_referenciados = {str(item) for item in campanha.get("jogadores", [])}
            pasta_jogadores = pasta_campanha / "jogadores"
            arquivos = sorted(pasta_jogadores.glob("*.json")) if pasta_jogadores.exists() else []

            for arquivo in arquivos:
                jogador = ler_json(arquivo, {})
                jogador["_arquivo"] = arquivo
                jogador.setdefault("campanha_id", campanha.get("id", pasta_campanha.name))
                jogador_id = str(jogador.get("id") or arquivo.stem)
                jogadores_por_id[jogador_id] = jogador

            for jogador_id in sorted(ids_referenciados):
                if jogador_id not in jogadores_por_id:
                    self.avisos.append(
                        f'A campanha "{campanha.get("nome", pasta_campanha.name)}" '
                        f'referencia o jogador "{jogador_id}", mas o JSON não foi encontrado.'
                    )

        self.jogadores = list(jogadores_por_id.values())

    def analisar(self) -> dict[str, Any]:
        pokemons_catalogo = self.catalogo_pokemons.get("pokemons", [])
        golpes_catalogo = self.catalogo_golpes.get("golpes", [])
        tipos = {
            str(tipo).strip()
            for pokemon in pokemons_catalogo
            for tipo in pokemon.get("tipos", [])
            if str(tipo).strip()
        }
        tipos.update(
            str(golpe.get("tipo", "")).strip()
            for golpe in golpes_catalogo
            if str(golpe.get("tipo", "")).strip()
        )
        categorias = {
            str(golpe.get("categoria", "")).strip()
            for golpe in golpes_catalogo
            if str(golpe.get("categoria", "")).strip()
        }
        pokemon_jogadores = sum(len(j.get("pokemons", [])) for j in self.jogadores)

        return {
            "usuarios": len(self.usuarios.get("usuarios", [])),
            "campanhas": len(self.campanhas),
            "jogadores": len(self.jogadores),
            "pokemon_jogadores": pokemon_jogadores,
            "formas_pokemon": len(pokemons_catalogo),
            "golpes": len(golpes_catalogo),
            "tipos": len(tipos),
            "categorias_golpe": len(categorias),
            "naturezas": len(self.regras_pokemon.get("naturezas", [])),
            "status": len(
                [
                    item
                    for item in self.regras_pokemon.get("status", [])
                    if str(item.get("nome", "")).strip().casefold() != "nenhum"
                ]
            ),
            "atributos": len(
                {
                    str(item.get("id"))
                    for item in self.regras_treinador.get("atributos", [])
                    + self.regras_pokemon.get("atributos", [])
                    if item.get("id")
                }
            ),
            "avisos": list(self.avisos),
        }
