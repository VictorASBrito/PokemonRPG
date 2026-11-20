"""10E.4 — Transformações reversíveis de Pokémon.

A forma permanente nunca muda. Mega: autorização do MESTRE ao TREINADOR,
sem qualquer pedra/item; só em Campo, uma ativa por treinador. Alternativas:
o dono pode escolher entre as formas existentes da espécie, como Morpeko.
As condições naturais de habilidades/turnos não são automatizadas.
"""
from __future__ import annotations

import json
import uuid
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    CampanhaMembro, FormaPokemon, HistoricoAlteracao, Personagem,
    Pokemon, PokemonEmCampo, Usuario,
)
from app.services.permissoes_service import PERFIS_JOGADOR, PERFIS_MESTRE


@lru_cache(maxsize=1)
def _referencias() -> dict:
    path = Path(__file__).resolve().parents[2] / "data" / "referencias" / "transformacoes_10e4.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _uuid(raw, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(raw))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"Identificador de {label} inválido.") from exc


def _validar_usuario(usuario_id: uuid.UUID | str) -> Usuario:
    user = db.session.get(Usuario, _uuid(usuario_id, "usuário"))
    if user is None or not user.ativo:
        raise PermissionError("A conta conectada deve estar ativa.")
    return user


def _auditar(
    *, usuario_id: uuid.UUID | None, entidade: str,
    registro_id: uuid.UUID, acao: str, anterior: dict, novo: dict,
) -> None:
    db.session.add(HistoricoAlteracao(
        usuario_id=usuario_id, entidade=entidade, registro_id=registro_id,
        acao=acao, dados_anteriores=anterior, dados_novos=novo,
    ))


def _opcoes_por_codigo(pokemon: Pokemon) -> tuple[set[str], set[str]]:
    base = pokemon.forma_pokemon
    if base is None:
        return set(), set()
    code = base.codigo
    refs = _referencias()
    mega_codes = {x["dest"] for x in refs["mega"] if x["source"] == code}
    # Grupos conexos: aceita alternar de MORPEKO faminto para satisfeito
    # e vice-versa, mesmo que o primeiro esteja salvo como forma principal.
    edges = [(x["source"], x["dest"]) for x in refs["alternativas"]]
    component = {code}
    changed = True
    while changed:
        expanded = component | {
            y for x, y in edges if x in component
        } | {
            x for x, y in edges if y in component
        }
        changed = len(expanded) != len(component)
        component = expanded
    return mega_codes, component


def listar_formas_temporarias(pokemon: Pokemon) -> dict:
    """Somente opções reais e ativas, da espécie exata (nunca Alola/Galar)."""
    mega_codes, alt_codes = _opcoes_por_codigo(pokemon)
    atual = pokemon.forma_temporaria
    if atual is not None and pokemon.tipo_transformacao == "alternativa":
        alt_codes.add(atual.codigo)
    alternativas = list(db.session.scalars(
        select(FormaPokemon)
        .where(
            FormaPokemon.especie_id == pokemon.forma_pokemon.especie_id,
            FormaPokemon.ativo.is_(True),
        )
        .options(selectinload(FormaPokemon.especie))
        .order_by(FormaPokemon.nome)
    ))
    # Membros do mesmo grupo explicitamente revisado e variantes com
    # categoria alternativa do mesmo Pokémon; nunca Mega/regional.
    alt = [
        f for f in alternativas
        if f.categoria not in {"mega", "regional"}
        and (f.codigo in alt_codes or f.categoria == "alternativa")
        and f.id != pokemon.forma_pokemon_id
    ]
    megas = [
        f for f in alternativas if f.categoria == "mega" and f.codigo in mega_codes
    ]
    return {
        "mega": megas, "alternativas": alt,
        "atual": atual, "tipo": pokemon.tipo_transformacao,
        "forma_original": pokemon.forma_pokemon,
    }


def _ajustar_forma(pokemon: Pokemon, destino: FormaPokemon | None, tipo: str | None, usuario_id: uuid.UUID, *, acao: str):
    """Muda só overlay e preserva dano; não faz COMMIT."""
    from app.services.pokemon_db_service import calcular_pokemon, carregar_regras_pokemon_db
    dono = pokemon.personagem
    regras = carregar_regras_pokemon_db(dono.campanha_id)
    pv_anterior = int(calcular_pokemon(pokemon, dono, regras)["totais"]["pv"])
    if pv_anterior < 1:
        raise ValueError("Forma atual sem PV válidos.")
    dano = max(0, pv_anterior - min(pokemon.pv_atual, pv_anterior))
    original = {
        "forma_pokemon_id": str(pokemon.forma_pokemon_id),
        "forma_temporaria_id": str(pokemon.forma_temporaria_id) if pokemon.forma_temporaria_id else None,
        "tipo_transformacao": pokemon.tipo_transformacao,
        "pv_atual": pokemon.pv_atual,
        "pv_maximo": pv_anterior,
    }
    ko = pokemon.pv_atual == 0
    pokemon.forma_temporaria_id = destino.id if destino else None
    pokemon.tipo_transformacao = tipo
    db.session.flush()
    db.session.expire(pokemon, ["forma_temporaria"])
    pv_novo_max = int(calcular_pokemon(pokemon, dono, regras)["totais"]["pv"])
    if pv_novo_max < 1:
        raise ValueError("Forma destino sem PV válidos.")
    pokemon.pv_atual = 0 if ko else min(pv_novo_max, max(1, pv_novo_max - dano))
    _auditar(
        usuario_id=usuario_id, entidade="pokemon", registro_id=pokemon.id,
        acao=acao, anterior=original,
        novo={
            "forma_pokemon_id": str(pokemon.forma_pokemon_id),
            "forma_temporaria_id": str(destino.id) if destino else None,
            "tipo_transformacao": tipo,
            "pv_atual": pokemon.pv_atual,
            "pv_maximo": pv_novo_max,
        },
    )


def _restaurar(pokemon: Pokemon, usuario_id: uuid.UUID, motivo: str) -> bool:
    if not pokemon.forma_temporaria_id:
        return False
    _ajustar_forma(pokemon, None, None, usuario_id, acao="reverter_forma_" + motivo)
    return True


def transformar_pokemon(
    *, pokemon_id: str | uuid.UUID, destino_id: str | uuid.UUID | None,
    tipo: str, usuario_id: str | uuid.UUID, personagem_id: str | uuid.UUID,
    campanha_id: str | uuid.UUID,
) -> str:
    """Ação pessoal do treinador; pré-condições verificadas sob locks."""
    usuario = _validar_usuario(usuario_id)
    if usuario.perfil not in PERFIS_JOGADOR:
        raise PermissionError("Somente o jogador ou tester dono pode transformar este Pokémon.")
    dono_id, cid = _uuid(personagem_id, "treinador"), _uuid(campanha_id, "campanha")
    dono = db.session.scalar(select(Personagem).where(
        Personagem.id == dono_id,
        Personagem.campanha_id == cid,
        Personagem.usuario_id == usuario.id,
        Personagem.ativo.is_(True),
    ).with_for_update())
    if not dono or not dono.campanha.ativo:
        raise PermissionError("Treinador não pertence à sessão/campanha.")
    pokemon = db.session.scalar(select(Pokemon).where(
        Pokemon.id == _uuid(pokemon_id, "Pokémon"),
        Pokemon.personagem_id == dono.id, Pokemon.ativo.is_(True),
    ).with_for_update())
    if pokemon is None:
        raise ValueError("Pokémon não encontrado na ficha do treinador.")

    if tipo == "reverter":
        if not _restaurar(pokemon, usuario.id, "manual"):
            return "Este Pokémon já está em sua forma original."
        db.session.flush()
        return "Pokémon retornou à sua forma original."

    if tipo not in {"mega", "alternativa"}:
        raise ValueError("Tipo de transformação inválido.")
    if not destino_id:
        raise ValueError("Selecione a forma desejada.")
    opcoes = listar_formas_temporarias(pokemon)
    permitido = opcoes["mega" if tipo == "mega" else "alternativas"]
    destino_uuid = _uuid(destino_id, "forma")
    destino = next((f for f in permitido if f.id == destino_uuid), None)
    if destino is None:
        raise ValueError("Forma não habilitada para este Pokémon.")
    if pokemon.pv_atual == 0:
        raise ValueError("Pokémon desmaiado não pode se transformar.")
    if pokemon.forma_temporaria_id == destino.id and pokemon.tipo_transformacao == tipo:
        return "Esta forma já está ativa."

    if tipo == "mega":
        if not dono.mega_habilitada:
            raise PermissionError("O mestre ainda não habilitou Mega Evolução para este treinador.")
        if not db.session.scalar(select(PokemonEmCampo.id).where(
            PokemonEmCampo.pokemon_id == pokemon.id,
            PokemonEmCampo.campanha_id == cid,
        )):
            raise ValueError("Mega Evolução só pode ser ativada no Campo.")
        if pokemon.tipo_transformacao == "alternativa":
            raise ValueError("Reverta a forma alternativa antes de ativar uma Mega.")
        outra = db.session.scalar(select(Pokemon.id).where(
            Pokemon.personagem_id == dono.id, Pokemon.id != pokemon.id,
            Pokemon.tipo_transformacao == "mega", Pokemon.ativo.is_(True),
        ))
        if outra is not None:
            raise ValueError("O treinador já possui uma Mega Evolução ativa.")
    elif pokemon.tipo_transformacao == "mega":
        raise ValueError("Reverta a Mega Evolução antes de escolher uma forma alternativa.")

    _ajustar_forma(pokemon, destino, tipo, usuario.id, acao="ativar_" + tipo)
    db.session.flush()
    return f"{pokemon.apelido or pokemon.forma_pokemon.nome} assumiu a forma {destino.nome}."


def permitir_mega_treinador(
    *, personagem_id: str | uuid.UUID, campanha_id: str | uuid.UUID,
    usuario_id: str | uuid.UUID, habilitar: bool,
) -> str:
    """Apenas mestre daquela campanha concede ou revoga a permissão."""
    user = _validar_usuario(usuario_id)
    if user.perfil not in PERFIS_MESTRE:
        raise PermissionError("Somente mestre ou administrador pode conceder Mega.")
    pid, cid = _uuid(personagem_id, "treinador"), _uuid(campanha_id, "campanha")
    if user.perfil == "mestre" and not db.session.scalar(select(CampanhaMembro.id).where(
        CampanhaMembro.campanha_id == cid,
        CampanhaMembro.usuario_id == user.id,
        CampanhaMembro.papel == "mestre",
    )):
        raise PermissionError("Mestre não autorizado nesta campanha.")
    dono = db.session.scalar(select(Personagem).where(
        Personagem.id == pid, Personagem.campanha_id == cid,
        Personagem.ativo.is_(True),
    ).with_for_update())
    if not dono:
        raise ValueError("Treinador não encontrado na campanha.")
    if dono.mega_habilitada == habilitar:
        return "A permissão Mega já estava neste estado."
    anterior = dono.mega_habilitada
    dono.mega_habilitada = habilitar
    if not habilitar:
        for p in db.session.scalars(
            select(Pokemon).where(
                Pokemon.personagem_id == dono.id,
                Pokemon.tipo_transformacao == "mega",
            ).with_for_update()
        ):
            _restaurar(p, user.id, "permissao_revogada")
    _auditar(
        usuario_id=user.id, entidade="personagem", registro_id=dono.id,
        acao="habilitar_mega" if habilitar else "revogar_mega",
        anterior={"mega_habilitada": anterior},
        novo={"mega_habilitada": habilitar},
    )
    db.session.flush()
    return ("Mega Evolução habilitada para " if habilitar else "Mega Evolução revogada de ") + dono.nome + "."


def reverter_mega_campo(pokemon: Pokemon, usuario_id: str | uuid.UUID | None, motivo: str) -> None:
    """Chamado na mesma transação ao retirar/limpar o Campo."""
    if pokemon.tipo_transformacao == "mega":
        _restaurar(pokemon, _uuid(usuario_id, "usuário") if usuario_id else None, motivo)


def encerrar_mega_desmaio(pokemon: Pokemon, usuario_id: str | uuid.UUID | None) -> None:
    if pokemon.tipo_transformacao == "mega" and pokemon.pv_atual == 0:
        reverter_mega_campo(pokemon, usuario_id, "desmaio")
