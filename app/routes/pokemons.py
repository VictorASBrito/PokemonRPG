from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.routes.auth import perfil_obrigatorio
from app.services.box_service import (
    encontrar_box,
    garantir_estrutura_boxes,
    mover_pokemon,
)
from app.services.calculo_atributos import calcular_atributos_pokemon
from app.services.jogador_service import carregar_jogador, salvar_jogador
from app.services.pokemon_service import (
    buscar_por_nome,
    carregar_catalogo_golpes,
    carregar_catalogo_pokemons,
    carregar_regras_pokemon,
    criar_pokemon_na_equipe,
    encontrar_pokemon,
    equipe_detalhada,
    garantir_estrutura_pokemon,
    indexar_catalogo,
    montar_pokemon_do_formulario,
    remover_pokemon,
)

pokemons_bp = Blueprint("pokemons", __name__)


def _contexto() -> tuple[Path, str]:
    return (
        Path(current_app.config["DATA_DIR"]),
        str(current_app.config["CAMPANHA_PADRAO"]),
    )


def _carregar_jogador(jogador_id: str) -> tuple[dict[str, Any] | None, Path, str]:
    data_dir, campanha_id = _contexto()
    jogador = carregar_jogador(data_dir, campanha_id, jogador_id)
    if jogador:
        garantir_estrutura_pokemon(jogador)
    return jogador, data_dir, campanha_id


def _catalogos(data_dir: Path):
    return (
        carregar_catalogo_pokemons(data_dir),
        carregar_catalogo_golpes(data_dir),
        carregar_regras_pokemon(data_dir),
    )


def _nomes_catalogo(catalogo: dict[str, Any], chave: str) -> list[str]:
    return sorted(
        [str(item.get("nome", "")) for item in catalogo.get(chave, [])],
        key=str.casefold,
    )


def _golpes_formulario(
    pokemon: dict[str, Any],
    catalogo_golpes: dict[str, Any],
    limite: int,
) -> list[dict[str, Any]]:
    golpes_por_id = indexar_catalogo(catalogo_golpes, "golpes")
    resultado: list[dict[str, Any]] = []
    for item in pokemon.get("golpes", []):
        golpe = golpes_por_id.get(str(item.get("golpe_id", "")))
        if golpe:
            resultado.append(golpe)
    while len(resultado) < limite:
        resultado.append({"id": "", "nome": ""})
    return resultado[:limite]


def _render_equipe(jogador: dict[str, Any], *, modo_mestre: bool):
    data_dir, _ = _contexto()
    catalogo_pokemons, catalogo_golpes, regras = _catalogos(data_dir)
    limite = int(regras.get("limites", {}).get("tamanho_equipe", 6))
    jogador_id = str(jogador["id"])

    if modo_mestre:
        voltar_url = url_for("mestre.jogadores")
        editar_endpoint = "pokemons.editar_mestre"
        boxes_url = url_for("boxes.boxes_mestre", jogador_id=jogador_id)
    else:
        voltar_url = url_for("jogadores.dashboard")
        editar_endpoint = "pokemons.editar_jogador"
        boxes_url = url_for("boxes.boxes_jogador")

    return render_template(
        "jogador/equipe.html",
        jogador=jogador,
        equipe=equipe_detalhada(
            jogador=jogador,
            catalogo_pokemons=catalogo_pokemons,
            catalogo_golpes=catalogo_golpes,
            regras=regras,
        ),
        limite=limite,
        modo_mestre=modo_mestre,
        voltar_url=voltar_url,
        editar_endpoint=editar_endpoint,
        boxes_url=boxes_url,
    )


def _novo(jogador: dict[str, Any], *, modo_mestre: bool):
    data_dir, campanha_id = _contexto()
    catalogo_pokemons, _, regras = _catalogos(data_dir)
    garantir_estrutura_boxes(jogador, regras)
    jogador_id = str(jogador["id"])
    box = jogador.get("boxes", [None])[0]

    voltar_url = url_for(
        "boxes.boxes_mestre" if modo_mestre else "boxes.boxes_jogador",
        **({"jogador_id": jogador_id} if modo_mestre else {}),
        _anchor="box-pokemon",
    )

    if not box:
        flash("A Box do jogador não foi encontrada.", "erro")
        return redirect(voltar_url)

    destino = str(request.args.get("destino", "")).strip()
    destino_esperado = f"box:{box['id']}"
    if destino != destino_esperado:
        flash("Novos Pokémon só podem ser criados em um espaço vazio da Box.", "aviso")
        return redirect(voltar_url)

    if len(box.get("pokemon_ids", [])) >= int(box.get("limite", 100)):
        flash("A Box está cheia.", "aviso")
        return redirect(voltar_url)

    if request.method == "POST":
        especie_nome = request.form.get("especie_nome", "").strip()
        especie = buscar_por_nome(catalogo_pokemons, "pokemons", especie_nome)
        if not especie:
            flash("Selecione uma espécie existente no catálogo.", "erro")
        else:
            pokemon = criar_pokemon_na_equipe(
                jogador=jogador,
                especie=especie,
                regras=regras,
            )
            erro_movimento = mover_pokemon(
                jogador,
                regras,
                pokemon_id=str(pokemon["id"]),
                destino=destino_esperado,
            )
            if erro_movimento:
                remover_pokemon(jogador, str(pokemon["id"]))
                flash(erro_movimento, "erro")
                return redirect(voltar_url)

            salvar_jogador(
                data_dir=data_dir,
                campanha_id=campanha_id,
                jogador=jogador,
            )
            flash(f"{especie['nome']} foi criado no último espaço ocupado da Box.", "sucesso")
            parametros = {
                "pokemon_id": pokemon["id"],
                "retorno": "boxes",
            }
            if modo_mestre:
                parametros["jogador_id"] = jogador_id
            return redirect(
                url_for(
                    "pokemons.editar_mestre" if modo_mestre else "pokemons.editar_jogador",
                    **parametros,
                )
            )

    return render_template(
        "jogador/novo_pokemon.html",
        jogador=jogador,
        especies=_nomes_catalogo(catalogo_pokemons, "pokemons"),
        total_catalogo=catalogo_pokemons.get("total", 0),
        modo_mestre=modo_mestre,
        voltar_url=voltar_url,
        destino=destino_esperado,
        destino_rotulo=str(box.get("nome", "Box")),
    )

def _editar(jogador: dict[str, Any], pokemon_id: str, *, modo_mestre: bool):
    data_dir, campanha_id = _contexto()
    catalogo_pokemons, catalogo_golpes, regras = _catalogos(data_dir)
    garantir_estrutura_boxes(jogador, regras)
    especies_por_id = indexar_catalogo(catalogo_pokemons, "pokemons")
    golpes_por_id = indexar_catalogo(catalogo_golpes, "golpes")
    pokemon = encontrar_pokemon(jogador, pokemon_id)
    jogador_id = str(jogador["id"])
    retorno = str(request.form.get("retorno", request.args.get("retorno", "equipe")))
    retorno = "boxes" if retorno == "boxes" else "equipe"

    if retorno == "boxes":
        voltar_url = url_for(
            "boxes.boxes_mestre" if modo_mestre else "boxes.boxes_jogador",
            **({"jogador_id": jogador_id} if modo_mestre else {}),
        )
    else:
        voltar_url = url_for(
            "pokemons.equipe_mestre" if modo_mestre else "pokemons.equipe_jogador",
            **({"jogador_id": jogador_id} if modo_mestre else {}),
        )

    if not pokemon:
        flash("Pokémon não encontrado na ficha deste jogador.", "erro")
        return redirect(voltar_url)

    especie = especies_por_id.get(str(pokemon.get("especie_id")))
    if not especie:
        flash("A espécie vinculada a este Pokémon não existe mais no catálogo.", "erro")
        return redirect(voltar_url)

    treinador = jogador.get("treinador", {})
    estilo = str(treinador.get("estilo_combate", ""))
    nivel_jogador = max(1, int(treinador.get("nivel", 1)))
    erros: list[str] = []
    if request.method == "POST":
        especie_nome = request.form.get("especie_nome", "").strip()
        especie_formulario = buscar_por_nome(
            catalogo_pokemons, "pokemons", especie_nome
        )
        if not especie_formulario:
            erros.append("Selecione uma espécie existente no catálogo.")
        else:
            especie = especie_formulario
            candidato, calculos, erros_formulario = montar_pokemon_do_formulario(
                pokemon_atual=pokemon,
                formulario=request.form,
                especie=especie,
                regras=regras,
                catalogo_golpes=catalogo_golpes,
                nivel_jogador=nivel_jogador,
                estilo_combate=estilo,
            )
            erros.extend(erros_formulario)
            pokemon = candidato

        if not erros:
            for indice, item in enumerate(jogador["pokemons"]):
                if str(item.get("id")) == pokemon_id:
                    jogador["pokemons"][indice] = pokemon
                    break
            salvar_jogador(
                data_dir=data_dir,
                campanha_id=campanha_id,
                jogador=jogador,
            )
            flash("Pokémon atualizado com sucesso.", "sucesso")
            parametros = {"pokemon_id": pokemon_id, "retorno": retorno}
            if modo_mestre:
                parametros["jogador_id"] = jogador_id
            return redirect(
                url_for(
                    "pokemons.editar_mestre" if modo_mestre else "pokemons.editar_jogador",
                    **parametros,
                )
            )

        for erro in erros:
            flash(erro, "erro")

    calculos = calcular_atributos_pokemon(
        pokemon=pokemon,
        especie=especie,
        regras=regras,
        nivel_jogador=nivel_jogador,
        estilo_combate=estilo,
        golpes_catalogo=golpes_por_id,
    )
    limite_golpes = int(regras.get("limites", {}).get("golpes_por_pokemon", 4))
    parametros_acao = {"pokemon_id": pokemon_id, "retorno": retorno}
    if modo_mestre:
        parametros_acao["jogador_id"] = jogador_id

    return render_template(
        "jogador/pokemon.html",
        jogador=jogador,
        pokemon=pokemon,
        especie=especie,
        calculos=calculos,
        regras=regras,
        golpes_selecionados=_golpes_formulario(
            pokemon, catalogo_golpes, limite_golpes
        ),
        especies=_nomes_catalogo(catalogo_pokemons, "pokemons"),
        golpes=_nomes_catalogo(catalogo_golpes, "golpes"),
        modo_mestre=modo_mestre,
        estilo_combate=estilo,
        retorno=retorno,
        voltar_url=voltar_url,
        salvar_url=url_for(
            "pokemons.editar_mestre" if modo_mestre else "pokemons.editar_jogador",
            **parametros_acao,
        ),
        excluir_url=url_for(
            "pokemons.excluir_mestre" if modo_mestre else "pokemons.excluir_jogador",
            **parametros_acao,
        ),
    )


def _excluir(jogador: dict[str, Any], pokemon_id: str, *, modo_mestre: bool):
    data_dir, campanha_id = _contexto()
    jogador_id = str(jogador["id"])
    retorno = str(request.form.get("retorno", request.args.get("retorno", "equipe")))
    retorno = "boxes" if retorno == "boxes" else "equipe"
    if remover_pokemon(jogador, pokemon_id):
        salvar_jogador(
            data_dir=data_dir,
            campanha_id=campanha_id,
            jogador=jogador,
        )
        flash("Pokémon removido da ficha.", "sucesso")
    else:
        flash("Pokémon não encontrado.", "erro")

    endpoint = (
        "boxes.boxes_mestre" if modo_mestre else "boxes.boxes_jogador"
    ) if retorno == "boxes" else (
        "pokemons.equipe_mestre" if modo_mestre else "pokemons.equipe_jogador"
    )
    return redirect(
        url_for(
            endpoint,
            **({"jogador_id": jogador_id} if modo_mestre else {}),
        )
    )


@pokemons_bp.get("/jogador/equipe")
@perfil_obrigatorio("jogador")
def equipe_jogador():
    jogador_id = str(session.get("jogador_id", ""))
    jogador, _, _ = _carregar_jogador(jogador_id)
    if not jogador:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _render_equipe(jogador, modo_mestre=False)


@pokemons_bp.route("/jogador/equipe/novo", methods=["GET", "POST"])
@perfil_obrigatorio("jogador")
def novo_jogador():
    jogador_id = str(session.get("jogador_id", ""))
    jogador, _, _ = _carregar_jogador(jogador_id)
    if not jogador:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _novo(jogador, modo_mestre=False)


@pokemons_bp.route("/jogador/pokemon/<pokemon_id>", methods=["GET", "POST"])
@perfil_obrigatorio("jogador")
def editar_jogador(pokemon_id: str):
    jogador_id = str(session.get("jogador_id", ""))
    jogador, _, _ = _carregar_jogador(jogador_id)
    if not jogador:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _editar(jogador, pokemon_id, modo_mestre=False)


@pokemons_bp.post("/jogador/pokemon/<pokemon_id>/excluir")
@perfil_obrigatorio("jogador")
def excluir_jogador(pokemon_id: str):
    jogador_id = str(session.get("jogador_id", ""))
    jogador, _, _ = _carregar_jogador(jogador_id)
    if not jogador:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _excluir(jogador, pokemon_id, modo_mestre=False)


@pokemons_bp.get("/mestre/jogadores/<jogador_id>/equipe")
@perfil_obrigatorio("mestre")
def equipe_mestre(jogador_id: str):
    jogador, _, _ = _carregar_jogador(jogador_id)
    if not jogador:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.jogadores"))
    return _render_equipe(jogador, modo_mestre=True)


@pokemons_bp.route(
    "/mestre/jogadores/<jogador_id>/equipe/novo", methods=["GET", "POST"]
)
@perfil_obrigatorio("mestre")
def novo_mestre(jogador_id: str):
    jogador, _, _ = _carregar_jogador(jogador_id)
    if not jogador:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.jogadores"))
    return _novo(jogador, modo_mestre=True)


@pokemons_bp.route(
    "/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>", methods=["GET", "POST"]
)
@perfil_obrigatorio("mestre")
def editar_mestre(jogador_id: str, pokemon_id: str):
    jogador, _, _ = _carregar_jogador(jogador_id)
    if not jogador:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.jogadores"))
    return _editar(jogador, pokemon_id, modo_mestre=True)


@pokemons_bp.post(
    "/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>/excluir"
)
@perfil_obrigatorio("mestre")
def excluir_mestre(jogador_id: str, pokemon_id: str):
    jogador, _, _ = _carregar_jogador(jogador_id)
    if not jogador:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.jogadores"))
    return _excluir(jogador, pokemon_id, modo_mestre=True)
