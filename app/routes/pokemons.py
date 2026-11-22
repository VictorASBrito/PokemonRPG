from __future__ import annotations

import hmac
import secrets

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import login_obrigatorio, perfil_obrigatorio
from app.services.autorizacao_evolucao_service import (
    autorizar_evolucao_individual,
    revogar_evolucao_individual,
)
from app.services.evolucao_efetiva_service import evoluir_pokemon
from app.services.transformacoes_service import listar_formas_temporarias, transformar_pokemon
from app.services.consulta_evolucao_service import consultar_evolucoes_pokemon
from app.services.permissoes_service import pode_criar_pokemon, pode_editar_identidade_pokemon
from app.services.pokemon_db_service import (
    BOX_ID,
    buscar_forma,
    carregar_contexto_pokemon,
    criar_pokemon_box,
    equipe_detalhada_db,
    golpes_formulario,
    pesquisar_formas_autocomplete,
    pesquisar_golpes_autocomplete,
    pesquisar_itens_autocomplete,
    total_formas_ativas,
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
        voltar_url = url_for("mestre.dashboard")
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

    return render_template(
        "jogador/novo_pokemon.html",
        jogador=contexto.jogador,
        total_catalogo=total_formas_ativas(),
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

    pode_editar_identidade = pode_editar_identidade_pokemon(session.get("usuario_id"))
    # Nunca aceitar campos bloqueados vindos de HTML adulterado ou POST manual.
    if request.method == "POST":
        if not pode_editar_identidade and any(
            campo in request.form for campo in ("especie_nome", "genero", "natureza", "shiny")
        ):
            return ("Apenas Admin/Mestre ou Tester pode alterar espécie, gênero, natureza ou Shiny.", 403)
        try:
            _, erros = atualizar_pokemon_formulario(
                contexto=contexto,
                pokemon_id=pokemon_id,
                formulario=request.form,
                usuario_responsavel_id=session.get("usuario_id"),
                permitir_identidade=pode_editar_identidade,
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
    # 10E.3.1: consulta não escreve no banco e não disponibiliza evolução.
    consulta_evolucao = consultar_evolucoes_pokemon(
        pokemon_model, contexto.personagem
    )
    limite_golpes = int(contexto.regras["limites"]["golpes_por_pokemon"])
    parametros_acao = {"pokemon_id": pokemon_id, "retorno": retorno}
    if modo_mestre:
        parametros_acao["jogador_id"] = jogador_id

    return render_template(
        "jogador/pokemon.html",
        jogador=contexto.jogador,
        pokemon=pokemon,
        jogador_id=jogador_id,
        csrf_evolucao=(
            session.setdefault("csrf_autorizacao_evolucao", secrets.token_urlsafe(32))
            if modo_mestre else None
        ),
        consulta_evolucao=consulta_evolucao,
        formas_temporarias=listar_formas_temporarias(pokemon_model),
        mega_permitida=bool(contexto.personagem.mega_habilitada),
        forma_visivel=registro["forma_visivel"],
        tipo_transformacao=registro["transformacao"],
        csrf_acao_evolucao=(
            session.setdefault("csrf_acao_evolucao", secrets.token_urlsafe(32))
            if not modo_mestre else None
        ),
        especie=registro["especie"],
        calculos=registro["calculos"],
        regras=contexto.regras,
        golpes_selecionados=golpes_formulario(pokemon_model, limite_golpes),
        modo_mestre=modo_mestre,
        pode_editar_identidade=pode_editar_identidade,
        estilo_combate=contexto.personagem.estilo_combate or "",
        retorno=retorno,
        voltar_url=voltar_url,
        salvar_url=url_for(
            "pokemons.editar_mestre" if modo_mestre else "pokemons.editar_jogador",
            **parametros_acao,
        ),
        csrf_exclusao=session.setdefault("csrf_exclusao_pokemon", secrets.token_urlsafe(32)),
        nome_exclusao=(pokemon_model.apelido or "").strip() or pokemon_model.forma_pokemon.nome.strip(),
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
    token = session.get("csrf_exclusao_pokemon")
    recebido = request.form.get("csrf_token", "")
    if not token or not hmac.compare_digest(token.encode("utf-8"), recebido.encode("utf-8")):
        abort(403)
    try:
        removido = remover_pokemon_db(
            contexto=contexto,
            pokemon_id=pokemon_id,
            usuario_responsavel_id=session.get("usuario_id"),
            nome_confirmacao=request.form.get("nome_confirmacao", ""),
        )
    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), "erro")
        parametros = {"pokemon_id": pokemon_id, "retorno": retorno}
        if modo_mestre:
            parametros["jogador_id"] = jogador_id
        return redirect(url_for(
            "pokemons.editar_mestre" if modo_mestre else "pokemons.editar_jogador",
            **parametros,
        ), code=303)
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


@pokemons_bp.get("/api/catalogo/formas")
@login_obrigatorio
def autocomplete_formas():
    try:
        itens = pesquisar_formas_autocomplete(request.args.get("q", ""), limite=20)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao pesquisar formas para autocomplete.")
        return jsonify({"itens": []}), 503
    return jsonify({"itens": itens})


@pokemons_bp.get("/api/catalogo/golpes")
@login_obrigatorio
def autocomplete_golpes():
    try:
        itens = pesquisar_golpes_autocomplete(request.args.get("q", ""), limite=20)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao pesquisar golpes para autocomplete.")
        return jsonify({"itens": []}), 503
    return jsonify({"itens": itens})


@pokemons_bp.get("/api/catalogo/itens")
@perfil_obrigatorio("mestre")
def autocomplete_itens():
    try:
        itens = pesquisar_itens_autocomplete(request.args.get("q", ""), limite=20)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao pesquisar itens para seleção visual.")
        return jsonify({"itens": []}), 503
    return jsonify({"itens": itens})


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
    # Nunca confiar apenas no botão: POST direto e sessão antiga também bloqueados.
    if not pode_criar_pokemon(session.get("usuario_id")):
        return ("Apenas contas Tester ou Admin podem criar Pokémon na Box.", 403)
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


@pokemons_bp.post("/jogador/pokemon/<pokemon_id>/evolucoes/<relacao_id>/evoluir")
@perfil_obrigatorio("jogador")
def evoluir_jogador(pokemon_id: str, relacao_id: str):
    """Evolução voluntária: valida CSRF e propriedade no serviço sob locks."""
    token = session.get("csrf_acao_evolucao", "")
    informado = request.form.get("csrf_token", "")
    if not token or not informado or not hmac.compare_digest(token, informado):
        return ("Confirmação da evolução inválida.", 403)
    personagem_id = str(session.get("personagem_id", ""))
    contexto = _carregar(personagem_id)
    if contexto is None:
        return ("Treinador não encontrado nesta campanha.", 403)
    pokemon = _localizar_pokemon(contexto, pokemon_id)
    if pokemon is None:
        return ("Pokémon não pertence ao treinador autenticado.", 404)
    retorno = "boxes" if request.form.get("retorno") == "boxes" else "equipe"
    destino = (
        url_for("jogadores.dashboard", foco=pokemon_id)
        if request.form.get("origem") == "painel"
        else url_for(
            "pokemons.editar_jogador",
            pokemon_id=pokemon_id,
            retorno=retorno,
            _anchor="consulta-evolucao",
        )
    )
    try:
        resultado = evoluir_pokemon(
            pokemon_id=pokemon.id,
            relacao_id=relacao_id,
            personagem_id=contexto.personagem.id,
            campanha_id=contexto.personagem.campanha_id,
            usuario_id=session.get("usuario_id"),
        )
        db.session.commit()
    except PermissionError:
        db.session.rollback()
        current_app.logger.warning(
            "Evolução negada: perfil ou propriedade do Pokémon não conferem "
            "(usuario_id=%s, personagem_id=%s, pokemon_id=%s).",
            session.get("usuario_id"), contexto.personagem.id, pokemon_id,
        )
        flash(
            "Não foi possível evoluir: a conta conectada precisa ser dona "
            "deste Pokémon e estar ativa como jogador ou tester.",
            "erro",
        )
        return redirect(destino)
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "erro")
        return redirect(destino)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao evoluir Pokémon no PostgreSQL.")
        flash("Falha ao registrar a evolução; nenhum item foi consumido.", "erro")
        return redirect(destino)
    flash(
        f"{resultado.origem_nome} evoluiu para {resultado.destino_nome}! "
        + (
            f"Material utilizado: {resultado.item_consumido}. "
            if resultado.item_consumido else ""
        )
        + f"PV: {resultado.pv_novo}/{resultado.pv_maximo_novo}.",
        "sucesso",
    )
    return redirect(destino)


@pokemons_bp.post("/jogador/pokemon/<pokemon_id>/transformar")
@perfil_obrigatorio("jogador")
def transformar_jogador(pokemon_id: str):
    token = session.get("csrf_acao_evolucao", "")
    informado = request.form.get("csrf_token", "")
    if not token or not informado or not hmac.compare_digest(token, informado):
        return ("Confirmação de transformação inválida.", 403)
    referencia = str(session.get("personagem_id", ""))
    contexto = _carregar(referencia)
    if contexto is None:
        return ("Treinador não encontrado nesta campanha.", 403)
    pokemon = _localizar_pokemon(contexto, pokemon_id)
    if pokemon is None:
        return ("Pokémon não pertence ao treinador autenticado.", 404)
    retorno = "boxes" if request.form.get("retorno") == "boxes" else "equipe"
    destino = (
        url_for("jogadores.dashboard", foco=pokemon_id)
        if request.form.get("origem") == "painel"
        else url_for(
            "pokemons.editar_jogador",
            pokemon_id=pokemon_id,
            retorno=retorno,
            _anchor="transformacoes-temporarias",
        )
    )
    try:
        mensagem = transformar_pokemon(
            pokemon_id=pokemon.id, destino_id=request.form.get("destino_id"),
            tipo=str(request.form.get("tipo", "")),
            usuario_id=session.get("usuario_id"),
            personagem_id=contexto.personagem.id,
            campanha_id=contexto.personagem.campanha_id,
        )
        db.session.commit()
        flash(mensagem, "sucesso")
    except (ValueError, PermissionError) as exc:
        db.session.rollback()
        flash(str(exc), "erro")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha na transformação temporária.")
        flash("Não foi possível transformar este Pokémon.", "erro")
    return redirect(destino)


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
        return redirect(url_for("mestre.dashboard"))
    return _render_equipe(contexto, modo_mestre=True)


@pokemons_bp.route(
    "/mestre/jogadores/<jogador_id>/equipe/novo", methods=["GET", "POST"]
)
@perfil_obrigatorio("mestre")
def novo_mestre(jogador_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        return redirect(url_for("mestre.dashboard"))
    return _novo(contexto, modo_mestre=True)


@pokemons_bp.route(
    "/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>", methods=["GET", "POST"]
)
@perfil_obrigatorio("mestre")
def editar_mestre(jogador_id: str, pokemon_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        return redirect(url_for("mestre.dashboard"))
    return _editar(contexto, pokemon_id, modo_mestre=True)


def _decidir_autorizacao_evolucao_mestre(
    jogador_id: str, pokemon_id: str, relacao_id: str, *, revogar: bool
):
    """Autoriza ou revoga somente na ficha real do mestre, com CSRF."""
    contexto = _carregar(jogador_id)
    if contexto is None:
        return ("Personagem fora da campanha ativa.", 404)
    pokemon = _localizar_pokemon(contexto, pokemon_id)
    if pokemon is None:
        return ("Pokémon não pertence ao personagem informado.", 404)
    token_atual = session.get("csrf_autorizacao_evolucao", "")
    token_enviado = request.form.get("csrf_token", "")
    if not token_atual or not token_enviado or not hmac.compare_digest(token_atual, token_enviado):
        return ("Confirmação de formulário inválida.", 403)
    destino = url_for(
        "pokemons.editar_mestre",
        jogador_id=jogador_id,
        pokemon_id=pokemon_id,
        retorno="boxes" if request.form.get("retorno") == "boxes" else "equipe",
        _anchor="consulta-evolucao",
    )
    try:
        dados = {
            "pokemon_id": pokemon.id,
            "relacao_id": relacao_id,
            "usuario_id": session.get("usuario_id"),
            "campanha_id": contexto.personagem.campanha_id,
            "motivo": request.form.get("motivo", ""),
        }
        if revogar:
            alterado = revogar_evolucao_individual(**dados)
        else:
            _, alterado = autorizar_evolucao_individual(**dados)
        db.session.commit()
    except PermissionError:
        db.session.rollback()
        return ("Apenas mestre autorizado na campanha pode realizar esta operação.", 403)
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "erro")
        return redirect(destino)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao registrar autorização evolutiva.")
        flash("Não foi possível registrar a decisão evolutiva no PostgreSQL.", "erro")
        return redirect(destino)
    if alterado:
        flash(
            "Autorização evolutiva revogada para este Pokémon."
            if revogar else "Evolução especial liberada para este Pokémon.",
            "sucesso",
        )
    else:
        flash("Nenhuma alteração necessária nessa autorização.", "aviso")
    return redirect(destino)


@pokemons_bp.post(
    "/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>/evolucoes/<relacao_id>/autorizar"
)
@perfil_obrigatorio("mestre")
def autorizar_evolucao_mestre(jogador_id: str, pokemon_id: str, relacao_id: str):
    return _decidir_autorizacao_evolucao_mestre(
        jogador_id, pokemon_id, relacao_id, revogar=False,
    )


@pokemons_bp.post(
    "/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>/evolucoes/<relacao_id>/revogar"
)
@perfil_obrigatorio("mestre")
def revogar_evolucao_mestre(jogador_id: str, pokemon_id: str, relacao_id: str):
    return _decidir_autorizacao_evolucao_mestre(
        jogador_id, pokemon_id, relacao_id, revogar=True,
    )


@pokemons_bp.post(
    "/mestre/jogadores/<jogador_id>/pokemon/<pokemon_id>/excluir"
)
@perfil_obrigatorio("mestre")
def excluir_mestre(jogador_id: str, pokemon_id: str):
    contexto = _carregar(jogador_id)
    if contexto is None:
        return redirect(url_for("mestre.dashboard"))
    return _excluir(contexto, pokemon_id, modo_mestre=True)
