"""Regressões do sprite/atalho da ficha e da altura do quadro de atributos.

Os testes não exigem PostgreSQL nem dados reais de jogadores.
"""
from pathlib import Path
from unittest.mock import patch

import tinycss2
from flask import Flask

from app.services.entrada_personagens_service import sprite_personagem_por_login


RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "static/css/dashboard.css"
JOGADOR = RAIZ / "templates/jogador/dashboard.html"
BASE = RAIZ / "templates/base.html"
MESTRE = RAIZ / "templates/mestre/catalogo/npc_painel.html"
JS = RAIZ / "static/js/dashboard-pokemon.js"


def test_sprite_por_login_usa_mesma_configuracao_da_entrada(tmp_path):
    arquivo = tmp_path / "img/login-personagens/slot-03.png"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_bytes(b"imagem-ficticia")
    app = Flask("teste_sprite", static_folder=str(tmp_path), static_url_path="/static")
    config = [
        {"login": "jogador1", "sprite": "img/login-personagens/slot-03.png"},
        {"login": "jogador2", "sprite": "img/login-personagens/inexistente.png"},
    ]
    with app.test_request_context("/"):
        with patch(
            "app.services.entrada_personagens_service.configuracao_login",
            return_value=config,
        ):
            assert sprite_personagem_por_login(" JOGADOR1 ") == (
                "/static/img/login-personagens/slot-03.png"
            )
            assert sprite_personagem_por_login("jogador2") == ""
            assert sprite_personagem_por_login("ausente") == ""
            assert sprite_personagem_por_login("") == ""


def test_dashboard_e_preview_recebem_sprite_do_proprio_personagem():
    jogador = (RAIZ / "app/routes/jogadores.py").read_text(encoding="utf-8")
    mestre = (RAIZ / "app/routes/mestre.py").read_text(encoding="utf-8")
    assinatura = (
        "sprite_personagem_url=sprite_personagem_por_login("
        "ficha.personagem.usuario.login)"
    )
    assert assinatura in jogador
    assert assinatura in mestre
    # Não modificar o retrato gravado no banco; apenas a exibição do painel.
    assert "personagem.foto_url =" not in jogador
    assert "personagem.foto_url =" not in mestre


def test_retrato_clicavel_abre_ficha_mas_menu_nao_duplica_link():
    base = BASE.read_text(encoding="utf-8")
    dashboard = JOGADOR.read_text(encoding="utf-8")
    assert ">Minha ficha</a>" not in base
    assert "url_for('jogadores.ficha')" in dashboard
    assert "url_for('mestre.ficha_jogador', jogador_id=preview_personagem_id)" in dashboard
    assert '<a class="foto-treinador-link" href="{{ dashboard_ficha_url }}"' in dashboard
    assert 'aria-label="Abrir ficha de {{ treinador.get(' in dashboard
    assert 'href="{{ dashboard_ficha_url }}#atributos"' in dashboard
    assert "sprite_personagem_url|default('')" in dashboard
    assert "sprite_painel or treinador.get('foto_url')" in dashboard
    assert "foto-treinador-sprite" in dashboard
    assert "foto-treinador-placeholder" in dashboard


def test_quadro_preserva_altura_mensurada_antes_da_expansao():
    css = CSS.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert "min-height: var(--dashboard-altura-atributos-original, auto)" in css
    assert (
        "body.dashboard-foco-aberto .dashboard-jogador:not(.npc-painel) "
        ".painel-atributos-treinador"
    ) in css
    assert "getBoundingClientRect().height" in js
    assert "Math.ceil(" in js
    assert "guardarAlturaAtributos();" in js
    assert "restaurarAlturaAtributos();" in js
    assert "--dashboard-altura-atributos-original" in js
    assert js.index("guardarAlturaAtributos();") < js.index("foco = card;")
    assert js.index("restaurarAlturaAtributos();") < js.index(
        "document.body.classList.remove('dashboard-foco-aberto')"
    )


def test_retrato_e_codigo_de_foco_preservam_npc_e_cache():
    css = CSS.read_text(encoding="utf-8")
    jogador = JOGADOR.read_text(encoding="utf-8")
    npc = MESTRE.read_text(encoding="utf-8")
    assert ".dashboard-jogador:not(.npc-painel) .foto-treinador-sprite" in css
    assert ".dashboard-jogador:not(.npc-painel) .foto-treinador-link:focus-visible" in css
    assert "image-rendering: pixelated" in css
    assert "filename='css/dashboard.css', v='10f9-tipos-atributos-r2'" in jogador
    assert "filename='css/dashboard.css', v='10f9-tipos-atributos-r2'" in npc
    assert "filename='js/dashboard-pokemon.js', v='10f5-atributos-altura'" in jogador
    assert "filename='js/dashboard-pokemon.js', v='10f5-atributos-altura'" in npc
    assert not [
        token for token in tinycss2.parse_stylesheet(css) if token.type == "error"
    ]
