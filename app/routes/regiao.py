"""Atlas de Ankar: consulta visual e atalho seguro para o fluxo de capturáveis."""
from __future__ import annotations

import hmac
import secrets

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.routes.auth import perfil_obrigatorio
from app.services.capturaveis_service import carregar_painel_capturaveis_mestre, criar_capturavel_campo
from app.services.regiao_ankar_service import (
    carregar_catalogo_ankar, carregar_mapa_ankar, encontro_por_indices, catalogo_com_busca_pokemon,
    formas_presentes_no_atlas, localizar_ankar, ponto_no_mapa, paragrafos_da_descricao,
)

regiao_bp = Blueprint("regiao", __name__, url_prefix="/regiao")


@regiao_bp.get("/ankar")
@perfil_obrigatorio("mestre")
def indice_ankar():
    return render_template("regiao/indice.html", catalogo=catalogo_com_busca_pokemon(carregar_catalogo_ankar()), mapa=carregar_mapa_ankar())


@regiao_bp.get("/ankar/<slug>")
@perfil_obrigatorio("mestre")
def detalhe_ankar(slug: str):
    local = localizar_ankar(slug)
    if local is None:
        abort(404)
    formas: dict = {}
    encontrados_por: list = []
    try:
        formas = formas_presentes_no_atlas(local)
        painel = carregar_painel_capturaveis_mestre(
            campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"])
        )
        encontrados_por = painel.encontrados_por
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Não foi possível consultar os encontros do Atlas no catálogo.")
        flash("Catálogo de Pokémon indisponível: geração de encontros temporariamente desativada.", "aviso")
    return render_template(
        "regiao/detalhe.html", local=local,
        resumo=carregar_catalogo_ankar()["resumo"], ponto_mapa=ponto_no_mapa(slug),
        formas=formas, encontrados_por=encontrados_por,
        descricao_paragrafos=paragrafos_da_descricao(local.get("descricao")),
        atlas_csrf=session.setdefault("atlas_ankar_gerar_csrf", secrets.token_urlsafe(32)),
    )


@regiao_bp.post("/ankar/<slug>/gerar-encontro")
@perfil_obrigatorio("mestre")
def gerar_encontro_atlas(slug: str):
    """Valida origem e CSRF, depois delega toda a geração ao serviço já existente."""
    local = localizar_ankar(slug)
    if local is None:
        abort(404)
    retorno = url_for("regiao.detalhe_ankar", slug=slug)
    esperado = str(session.get("atlas_ankar_gerar_csrf") or "")
    enviado = str(request.form.get("csrf_token") or "")
    if not esperado or not hmac.compare_digest(esperado, enviado):
        flash("Confirmação expirada. Reabra a ficha do local.", "erro")
        return redirect(retorno)
    try:
        zona = int(request.form.get("zona", ""))
        tabela = int(request.form.get("tabela", ""))
        indice = int(request.form.get("indice", ""))
    except (TypeError, ValueError):
        flash("Encontro inválido. Selecione um Pokémon da lista.", "erro")
        return redirect(retorno)
    encontro = encontro_por_indices(local, zona, tabela, indice)
    if encontro is None:
        flash("Esse registro não representa um Pokémon gerável.", "erro")
        return redirect(retorno)
    try:
        # A escolha enviada pelo navegador não é confiável: conferir novamente
        # as opções permitidas para o nome exato da planilha.
        vinculo = formas_presentes_no_atlas(local).get(str(encontro["pokemon"]).casefold())
        opcoes = vinculo['opcoes'] if vinculo else []
        if not opcoes:
            raise ValueError("Esta espécie ainda não está vinculada a uma forma ativa no catálogo.")
        forma_id_enviada = str(request.form.get('forma_id') or '').strip()
        if forma_id_enviada:
            escolhida = next((forma for forma in opcoes if forma['id'] == forma_id_enviada), None)
        elif len(opcoes) == 1:
            escolhida = opcoes[0]
        else:
            escolhida = None
        if escolhida is None:
            raise ValueError("Escolha uma das formas válidas para esse Pokémon.")
        criar_capturavel_campo(
            campanha_codigo=str(current_app.config["CAMPANHA_PADRAO"]),
            forma_id=escolhida['id'],
            forma_nome=escolhida['nome'],
            encontrado_por_personagem_id=request.form.get("encontrado_por_personagem_id"),
            usuario_responsavel_id=session.get("usuario_id"),
        )
    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), "erro")
        return redirect(retorno)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao gerar Pokémon capturável pelo Atlas.")
        flash("Não foi possível adicionar o Pokémon ao campo. Tente novamente.", "erro")
        return redirect(retorno)
    flash(f"{escolhida['nome']} adicionado aos capturáveis!", "sucesso")
    return redirect(url_for("capturas.campo_mestre"))
