"""Atlas visual e somente leitura da região de Ankar."""
from __future__ import annotations

from flask import Blueprint, abort, render_template
from app.routes.auth import perfil_obrigatorio
from app.services.regiao_ankar_service import (
    carregar_catalogo_ankar, carregar_mapa_ankar, localizar_ankar, ponto_no_mapa,
)

regiao_bp = Blueprint("regiao", __name__, url_prefix="/regiao")


@regiao_bp.get("/ankar")
@perfil_obrigatorio("mestre")
def indice_ankar():
    catalogo = carregar_catalogo_ankar()
    return render_template("regiao/indice.html", catalogo=catalogo, mapa=carregar_mapa_ankar())


@regiao_bp.get("/ankar/<slug>")
@perfil_obrigatorio("mestre")
def detalhe_ankar(slug: str):
    local = localizar_ankar(slug)
    if local is None:
        abort(404)
    return render_template("regiao/detalhe.html", local=local,
                           resumo=carregar_catalogo_ankar()["resumo"], ponto_mapa=ponto_no_mapa(slug))
