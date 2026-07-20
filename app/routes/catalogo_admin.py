from __future__ import annotations

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.catalogo_admin_service import (
    CATEGORIAS_FORMA,
    alterar_atividade_forma,
    atualizar_forma_admin,
    carregar_forma_admin,
    criar_forma_admin,
    duplicar_forma_admin,
    listar_formas_admin,
    opcoes_catalogo,
    resumo_catalogo,
    simular_atributos_forma,
)

catalogo_admin_bp = Blueprint("catalogo_admin", __name__, url_prefix="/mestre/catalogo")


def _erro_banco(mensagem: str):
    db.session.rollback()
    current_app.logger.exception(mensagem)
    flash("Não foi possível concluir a operação no catálogo.", "erro")


@catalogo_admin_bp.get("")
@perfil_obrigatorio("mestre")
def dashboard():
    try:
        resumo = resumo_catalogo()
    except SQLAlchemyError:
        _erro_banco("Falha ao carregar o resumo do catálogo.")
        resumo = {"especies": 0, "especies_ativas": 0, "formas": 0, "formas_ativas": 0, "tipos": 0}
    return render_template("mestre/catalogo/dashboard.html", resumo=resumo)


@catalogo_admin_bp.get("/pokemons")
@perfil_obrigatorio("mestre")
def pokemons():
    filtros = {
        "q": request.args.get("q", "").strip(),
        "categoria": request.args.get("categoria", "").strip(),
        "situacao": request.args.get("situacao", "ativas").strip(),
        "tipo_id": request.args.get("tipo_id", "").strip(),
    }
    try:
        pagina_atual = max(1, int(request.args.get("pagina", "1")))
    except ValueError:
        pagina_atual = 1
    try:
        pagina = listar_formas_admin(
            termo=filtros["q"],
            categoria=filtros["categoria"],
            situacao=filtros["situacao"],
            tipo_id=filtros["tipo_id"],
            pagina=pagina_atual,
        )
        opcoes = opcoes_catalogo(session.get("campanha_id"))
    except SQLAlchemyError:
        _erro_banco("Falha ao listar formas Pokémon.")
        return render_template(
            "mestre/catalogo/pokemons.html",
            pagina=None,
            tipos=[],
            categorias=CATEGORIAS_FORMA,
            filtros=filtros,
        ), 503
    return render_template(
        "mestre/catalogo/pokemons.html",
        pagina=pagina,
        tipos=opcoes.tipos,
        categorias=CATEGORIAS_FORMA,
        filtros=filtros,
    )


@catalogo_admin_bp.route("/pokemons/novo", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def novo_pokemon():
    try:
        opcoes = opcoes_catalogo(session.get("campanha_id"))
    except SQLAlchemyError:
        _erro_banco("Falha ao carregar opções do catálogo.")
        return redirect(url_for("catalogo_admin.pokemons"))

    dados = request.form.to_dict(flat=True) if request.method == "POST" else {}
    if request.method == "POST":
        try:
            forma, erros = criar_forma_admin(request.form, usuario_id=session.get("usuario_id"))
        except SQLAlchemyError:
            _erro_banco("Falha ao criar forma Pokémon.")
            erros = ["Não foi possível gravar a forma no banco de dados."]
            forma = None
        if not erros and forma is not None:
            flash(f"{forma.nome} foi criada no catálogo.", "sucesso")
            return redirect(url_for("catalogo_admin.editar_pokemon", forma_id=str(forma.id)))
        for erro in erros:
            flash(erro, "erro")

    return render_template(
        "mestre/catalogo/pokemon_form.html",
        forma=None,
        dados=dados,
        opcoes=opcoes,
        categorias=CATEGORIAS_FORMA,
        modo="novo",
    )


@catalogo_admin_bp.route("/pokemons/<forma_id>/editar", methods=["GET", "POST"])
@perfil_obrigatorio("mestre")
def editar_pokemon(forma_id: str):
    try:
        forma = carregar_forma_admin(forma_id)
        opcoes = opcoes_catalogo(session.get("campanha_id"))
    except SQLAlchemyError:
        _erro_banco("Falha ao carregar forma Pokémon para edição.")
        return redirect(url_for("catalogo_admin.pokemons"))
    if forma is None:
        flash("Forma Pokémon não encontrada.", "erro")
        return redirect(url_for("catalogo_admin.pokemons"))

    dados = request.form.to_dict(flat=True) if request.method == "POST" else {}
    if request.method == "POST":
        try:
            erros = atualizar_forma_admin(forma, request.form, usuario_id=session.get("usuario_id"))
        except SQLAlchemyError:
            _erro_banco("Falha ao atualizar forma Pokémon.")
            erros = ["Não foi possível salvar as alterações no banco de dados."]
        if not erros:
            flash("Forma Pokémon atualizada com sucesso.", "sucesso")
            return redirect(url_for("catalogo_admin.editar_pokemon", forma_id=forma_id))
        for erro in erros:
            flash(erro, "erro")

    return render_template(
        "mestre/catalogo/pokemon_form.html",
        forma=forma,
        dados=dados,
        opcoes=opcoes,
        categorias=CATEGORIAS_FORMA,
        modo="editar",
    )


@catalogo_admin_bp.post("/pokemons/<forma_id>/atividade")
@perfil_obrigatorio("mestre")
def atividade_pokemon(forma_id: str):
    forma = carregar_forma_admin(forma_id)
    if forma is None:
        flash("Forma Pokémon não encontrada.", "erro")
        return redirect(url_for("catalogo_admin.pokemons"))
    ativo = request.form.get("ativo") == "1"
    try:
        alterar_atividade_forma(forma, ativo=ativo, usuario_id=session.get("usuario_id"))
    except SQLAlchemyError:
        _erro_banco("Falha ao alterar atividade da forma Pokémon.")
    else:
        flash(f"{forma.nome} foi {'reativada' if ativo else 'desativada'}.", "sucesso")
    return redirect(url_for("catalogo_admin.editar_pokemon", forma_id=forma_id))


@catalogo_admin_bp.post("/pokemons/<forma_id>/duplicar")
@perfil_obrigatorio("mestre")
def duplicar_pokemon(forma_id: str):
    forma = carregar_forma_admin(forma_id)
    if forma is None:
        flash("Forma Pokémon não encontrada.", "erro")
        return redirect(url_for("catalogo_admin.pokemons"))
    try:
        copia = duplicar_forma_admin(forma, usuario_id=session.get("usuario_id"))
    except SQLAlchemyError:
        _erro_banco("Falha ao duplicar forma Pokémon.")
        return redirect(url_for("catalogo_admin.editar_pokemon", forma_id=forma_id))
    flash("Cópia criada como inativa. Revise os dados antes de ativá-la.", "sucesso")
    return redirect(url_for("catalogo_admin.editar_pokemon", forma_id=str(copia.id)))


@catalogo_admin_bp.post("/pokemons/simular")
@perfil_obrigatorio("mestre")
def simular_pokemon():
    payload = request.get_json(silent=True) or {}
    try:
        resultado = simular_atributos_forma(
            campanha_id=session.get("campanha_id"),
            atributos_base=payload.get("atributos", {}),
            nivel=int(payload.get("nivel", 1)),
            shiny=bool(payload.get("shiny")),
            natureza_id=payload.get("natureza_id"),
            estilo=str(payload.get("estilo", "")),
        )
    except (SQLAlchemyError, TypeError, ValueError) as erro:
        db.session.rollback()
        return jsonify({"erro": str(erro) or "Não foi possível simular os atributos."}), 400
    return jsonify({"atributos": resultado})
