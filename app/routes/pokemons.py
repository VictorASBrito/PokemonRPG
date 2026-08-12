from __future__ import annotations

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
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.pokemon_db_service import (
    BOX_ID,
    buscar_forma,
    carregar_contexto_pokemon,
    criar_pokemon_box,
    equipe_detalhada_db,
    golpes_formulario,
    nomes_formas,
    nomes_golpes,
    registro_detalhado,
    remover_pokemon_db,
    atualizar_pokemon_formulario,
)

pokemons_bp = Blueprint("pokemons", __name__)


def _campanha_codigo() -> str:
    return str(current_app.config["CAMPANHA_PADRAO"])


def _carregar(referencia: str):
    return carregar_contexto_pokemon(
        referencia,
        campanha_codigo=_campanha_codigo(),
    )


def _render_equipe(contexto, *, modo_mestre: bool):
    jogador_id = str(contexto.personagem.id)
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
        jogador=contexto.jogador,
        equipe=equipe_detalhada_db(contexto),
        limite=int(contexto.regras["limites"]["tamanho_equipe"]),
        modo_mestre=modo_mestre,
        voltar_url=voltar_url,
        editar_endpoint=editar_endpoint,
        boxes_url=boxes_url,
        inventario_url=url_for("inventario.inventario_mestre", personagem_id=jogador_id) if modo_mestre else url_for("inventario.inventario_jogador"),
        fonte_dados="PostgreSQL",
    )


def _novo(contexto, *, modo_mestre: bool):
    jogador_id = str(contexto.personagem.id)
    voltar_url = url_for(
        "boxes.boxes_mestre" if modo_mestre else "boxes.boxes_jogador",
        **({"jogador_id": jogador_id} if modo_mestre else {}),
        _anchor="box-pokemon",
    )
    destino = str(request.args.get("destino", "")).strip()
    destino_esperado = f"box:{BOX_ID}"
    if destino != destino_esperado:
        flash("Novos Pokémon só podem ser criados em um espaço vazio da Box.", "aviso")
        return redirect(voltar_url)

    ocupados = sum(
        1
        for item in contexto.personagem.pokemons
        if item.ativo and item.localizacao == "box"
    )
    limite_box = int(contexto.regras["boxes"]["espacos"])
    if ocupados >= limite_box:
        flash("A Box está cheia.", "aviso")
        return redirect(voltar_url)

    if request.method == "POST":
        forma = buscar_forma(str(request.form.get("especie_nome", "")))
        if forma is None:
            flash("Selecione uma espécie ou forma existente no banco.", "erro")
        else:
            try:
                pokemon = criar_pokemon_box(
                    personagem=contexto.personagem,
                    forma=forma,
                    regras=contexto.regras,
                    usuario_responsavel_id=session.get("usuario_id"),
                )
            except ValueError as erro:
                db.session.rollback()
                flash(str(erro), "erro")
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception("Falha ao criar Pokémon no PostgreSQL.")
                flash("Não foi possível criar o Pokémon no banco de dados.", "erro")
            else:
                flash(f"{forma.nome} foi criado no final da Box.", "sucesso")
                parametros = {"pokemon_id": str(pokemon.id), "retorno": "boxes"}
                if modo_mestre:
                    parametros["jogador_id"] = jogador_id
                return redirect(
                    url_for(
                        "pokemons.editar_mestre"
                        if modo_mestre
                        else "pokemons.editar_jogador",
                        **parametros,
                    )
                )

    especies = nomes_formas()
    return render_template(
        "jogador/novo_pokemon.html",
        jogador=contexto.jogador,
        especies=especies,
        total_catalogo=len(especies),
        modo_mestre=modo_mestre,
        voltar_url=voltar_url,
        destino=destino_esperado,
        destino_rotulo=contexto.regras["boxes"]["nome"],
        fonte_dados="PostgreSQL",
    )


def _localizar_pokemon(contexto, pokemon_id: str):
    return next(
        (
            item
            for item in contexto.personagem.pokemons
            if item.ativo and str(item.id) == str(pokemon_id)
        ),
        None,
    )


def _editar(contexto, pokemon_id: str, *, modo_mestre: bool):
    jogador_id = str(contexto.personagem.id)
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

    pokemon_model = _localizar_pokemon(contexto, pokemon_id)
    if pokemon_model is None:
        flash("Pokémon não encontrado na ficha deste jogador.", "erro")
        return redirect(voltar_url)

    if request.method == "POST":
        try:
            _, erros = atualizar_pokemon_formulario(
                contexto=contexto,
                pokemon_id=pokemon_id,
                formulario=request.form,
                usuario_responsavel_id=session.get("usuario_id"),
            )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Falha ao atualizar Pokémon no PostgreSQL.")
            erros = ["Não foi possível salvar o Pokémon no banco de dados."]
        if not erros:
            flash("Pokémon atualizado com sucesso no PostgreSQL.", "sucesso")
            parametros = {"pokemon_id": pokemon_id, "retorno": retorno}
            if modo_mestre:
                parametros["jogador_id"] = jogador_id
            return redirect(
                url_for(
                    "pokemons.editar_mestre"
                    if modo_mestre
                    else "pokemons.editar_jogador",
                    **parametros,
                )
            )
        for erro in erros:
            flash(erro, "erro")
        contexto = _carregar(jogador_id)
        if contexto is None:
            return redirect(voltar_url)
        pokemon_model = _localizar_pokemon(contexto, pokemon_id)
        if pokemon_model is None:
            return redirect(voltar_url)

    registro = registro_detalhado(
        pokemon_model,
        contexto.personagem,
        contexto.regras,
    )
    pokemon = registro["pokemon"]
    limite_golpes = int(contexto.regras["limites"]["golpes_por_pokemon"])
    parametros_acao = {"pokemon_id": pokemon_id, "retorno": retorno}
    if modo_mestre:
        parametros_acao["jogador_id"] = jogador_id

    return render_template(
        "jogador/pokemon.html",
        jogador=contexto.jogador,
        pokemon=pokemon,
        especie=registro["especie"],
        calculos=registro["calculos"],
        regras=contexto.regras,
        golpes_selecionados=golpes_formulario(pokemon_model, limite_golpes),
        especies=nomes_formas(),
        golpes=nomes_golpes(),
        modo_mestre=modo_mestre,
        estilo_combate=contexto.personagem.estilo_combate or "",
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
        inventario_url=(
            url_for("inventario.inventario_mestre", personagem_id=jogador_id)
            if modo_mestre
            else url_for("inventario.inventario_jogador")
        ),
        fonte_dados="PostgreSQL",
    )


def _excluir(contexto, pokemon_id: str, *, modo_mestre: bool):
    jogador_id = str(contexto.personagem.id)
    retorno = str(request.form.get("retorno", request.args.get("retorno", "equipe")))
    retorno = "boxes" if retorno == "boxes" else "equipe"
    try:
        removido = remover_pokemon_db(
            contexto=contexto,
            pokemon_id=pokemon_id,
            usuario_responsavel_id=session.get("usuario_id"),
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao remover Pokémon do PostgreSQL.")
        removido = False
    flash(
        "Pokémon removido da ficha." if removido else "Pokémon não encontrado.",
        "sucesso" if removido else "erro",
    )
    endpoint = (
        "boxes.boxes_mestre" if modo_mestre else "boxes.boxes_jogador"
    ) if retorno == "boxes" else (
        "pokemons.equipe_mestre" if modo_mestre else "pokemons.equipe_jogador"
    )
    return redirect(
        url_for(endpoint, **({"jogador_id": jogador_id} if modo_mestre else {}))
    )


@pokemons_bp.get("/jogador/equipe")
@perfil_obrigatorio("jogador")
def equipe_jogador():
    personagem_id = str(session.get("personagem_id", ""))
    contexto = _carregar(personagem_id)
    if contexto is None:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _render_equipe(contexto, modo_mestre=False)


@pokemons_bp.route("/jogador/equipe/novo", methods=["GET", "POST"])
@perfil_obrigatorio("jogador")
def novo_jogador():
    contexto = _carregar(str(session.get("personagem_id", "")))
    if contexto is None:
        flash("Sua ficha ainda não foi vinculada a este usuário.", "erro")
        return redirect(url_for("jogadores.dashboard"))
    return _novo(contexto, modo_mestre=False)


@pokemons_bp.route("/jogador/pokemon/<pokemon_id>", methods=["GET", "POST"])
@perfil_obrigatorio("jogador")
def editar_jogador(pokemon_id: str):
    contexto = _carregar(str(session.get("personagem_id", "")))
    if contexto is None:
        return redirect(url_for("jogadores.dashboard"))
    return _editar(contexto, pokemon_id, modo_mestre=False)


@pokemons_bp.post("/jogador/pokemon/<pokemon_id>/excluir")
@perfil_obrigatorio("jogador")
def excluir_jogador(pokemon_id: str):
    contexto = _carregar(str(session.get("personagem_id", "")))
    if contexto is None:
        return redirect(url_for("jogadores.dashboard"))
    return _excluir(contexto, pokemon_id, modo_mestre=False)


@pokemons_bp.get("/mestre/jogadores/<jogador_id>/equipe")
@perfil_obrigatorio("mestre")
def equipe_mestre(jogador_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        flash("Jogador não encontrado.", "erro")
        return redirect(url_for("mestre.jogadores"))
    return _render_equipe(contexto, modo_mestre=True)


@pokemons_bp.route(
    "/mestre/jogadores/<jogador_id>/equipe/novo", methods=["GET", "POST"]
)
@perfil_obrigatorio("mestre")
def novo_mestre(jogador_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        return redirect(url_for("mestre.jogadores"))
    return _novo(contexto, modo_mestre=True)


@pokemons_bp.route(
    "/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>", methods=["GET", "POST"]
)
@perfil_obrigatorio("mestre")
def editar_mestre(jogador_id: str, pokemon_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        return redirect(url_for("mestre.jogadores"))
    return _editar(contexto, pokemon_id, modo_mestre=True)


@pokemons_bp.post(
    "/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>/excluir"
)
@perfil_obrigatorio("mestre")
def excluir_mestre(jogador_id: str, pokemon_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        return redirect(url_for("mestre.jogadores"))
    return _excluir(contexto, pokemon_id, modo_mestre=True)
