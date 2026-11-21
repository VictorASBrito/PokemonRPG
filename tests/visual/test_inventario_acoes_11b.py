"""Auditoria visual de inventário com itens heterogêneos e SQLite isolado."""
from pathlib import Path
from uuid import UUID

import pytest
from playwright.sync_api import Page, expect
from sqlalchemy import select

from app.extensions import db
from app.models.db import Campanha, CampanhaMembro, Item, Personagem, PersonagemItem, Pokemon, Usuario
from app.services.senha_service import gerar_hash_senha

EVIDENCIAS = Path("test-results/inventario-11b")


@pytest.fixture()
def inventario_visual(app_visual):
    with app_visual.app_context():
        dono = db.session.get(Personagem, UUID(app_visual.config["TEST_IDS"]["personagem"]))
        campanha = db.session.get(Campanha, dono.campanha_id)
        usuario = Usuario(login="destino-11b", nome="Destinatário visual",
                          senha_hash=gerar_hash_senha("abc123"), perfil="jogador", ativo=True)
        destino = Personagem(usuario=usuario, campanha=campanha, nome="Destino visual",
                             nivel=48, pv_atual=10, ativo=True)
        db.session.add_all([usuario, destino, CampanhaMembro(
            campanha=campanha, usuario=usuario, papel="jogador")])
        pokemon = db.session.scalar(select(Pokemon).where(Pokemon.personagem_id == dono.id))
        pokemon.pv_atual = 1
        itens = [
            Item(codigo="visual-corda", nome="Corda visual", descricao="None", ativo=True),
            Item(codigo="visual-isca", nome="Isca visual", consumivel=True, ativo=True),
            Item(codigo="visual-tonico", nome="Tônico visual", consumivel=True,
                 uso_em_batalha=True, ativo=True,
                 efeitos={"versao": 1, "efeitos": [
                     {"tipo": "recuperar_pv", "alvo": "pokemon", "operacao": "fixo", "valor": 20}]}),
            Item(codigo="visual-amuleto", nome="Amuleto visual", equipavel=True, ativo=True),
        ]
        db.session.add_all(itens)
        db.session.flush()
        for item in itens:
            db.session.add(PersonagemItem(personagem_id=dono.id, item_id=item.id, quantidade=3))
        db.session.commit()
        return {"dono": str(dono.id), "destino": str(destino.id), "pokemon": str(pokemon.id),
                **{i.codigo: str(i.id) for i in itens}}


def abrir(page: Page, base: str, ids, perfil, largura=1720, altura=864):
    page.set_viewport_size({"width": largura, "height": altura})
    page.goto(base + "/login/coringa")
    page.locator("#login").fill("bartz-db" if perfil == "jogador" else "mestre-db")
    page.locator("#senha").fill("abc123" if perfil == "jogador" else "senha-db")
    page.get_by_role("button", name="Entrar").click()
    rota = "/jogador/inventario" if perfil == "jogador" else f"/mestre/jogadores/{ids['dono']}/inventario"
    page.goto(base + rota)
    page.locator('[data-aba-botao="avulsos"]').click()
    expect(page.locator("[data-contador-itens]")).to_have_text("4")
    return rota


def escolher(page, ids, codigo):
    page.locator(f'[data-escolher-item="{ids[codigo]}"]').click()
    detalhe = page.locator(f'[data-detalhe-item="{ids[codigo]}"]')
    expect(detalhe).to_be_visible()
    return detalhe


def capturar(page, nome):
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCIAS / nome), animations="disabled", full_page=True)


def test_diagnostico_antes(page: Page, live_site_url, inventario_visual):
    ids = inventario_visual
    abrir(page, live_site_url, ids, "mestre")
    escolher(page, ids, "visual-isca")
    botoes = page.locator(".inventario-nds-linha-botao:visible")
    dados = botoes.evaluate_all("""els => els.map(el => ({
      nome: el.querySelector('.inventario-nds-linha-nome').textContent.trim(),
      largura: el.getBoundingClientRect().width,
      sombra: getComputedStyle(el).boxShadow
    }))""")
    print("DIAGNOSTICO_ANTES", dados)
    capturar(page, "antes-desktop.png")
    assert max(d["largura"] for d in dados) - min(d["largura"] for d in dados) > 10
    assert any(d["sombra"] != "none" for d in dados)
    assert page.locator(".inventario-nds-lista [data-ativar-uso]").count() > 0
