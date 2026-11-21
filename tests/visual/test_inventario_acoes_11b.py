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


@pytest.mark.parametrize("perfil,largura,altura,tema", [
    ("mestre", 1720, 864, "dark"),
    ("jogador", 1366, 768, "light"),
    ("jogador", 390, 844, "dark"),
    ("mestre", 320, 700, "light"),
])
def test_lista_e_etiquetas_estaveis(page: Page, live_site_url, inventario_visual,
                                   perfil, largura, altura, tema):
    ids = inventario_visual
    page.add_init_script(f"localStorage.setItem('pokemon-rpg-tema', '{tema}')")
    erros = []
    page.on("pageerror", lambda e: erros.append(str(e)))
    abrir(page, live_site_url, ids, perfil, largura, altura)
    expect(page.locator("html")).to_have_attribute("data-theme", tema)
    botoes = page.locator(".inventario-nds-linha-botao:visible")
    expect(botoes).to_have_count(4)
    assert page.locator(".inventario-nds-lista [data-ativar-uso], .inventario-nds-lista [data-equipar-item]").count() == 0
    alturas = []
    for codigo in ("visual-corda", "visual-isca", "visual-tonico", "visual-amuleto"):
        detalhe = escolher(page, ids, codigo)
        selecionado = page.locator(f'[data-escolher-item="{ids[codigo]}"]')
        expect(selecionado).to_have_attribute("aria-pressed", "true")
        medidas = botoes.evaluate_all("""els => els.map(el => ({
            w: el.getBoundingClientRect().width,
            h: el.getBoundingClientRect().height,
            sombra: getComputedStyle(el).boxShadow
        }))""")
        assert max(d["w"] for d in medidas) - min(d["w"] for d in medidas) <= 1, medidas
        assert max(d["h"] for d in medidas) - min(d["h"] for d in medidas) <= 1, medidas
        assert all(d["sombra"] == "none" for d in medidas), medidas
        assert detalhe.locator(".inventario-nds-etiquetas span").count() >= 1
        header = detalhe.locator(".inventario-nds-item-cabecalho").bounding_box()
        alturas.append(header["height"])
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        if codigo == "visual-corda":
            expect(detalhe.locator(".inventario-nds-item-descricao")).to_have_text("Sem descrição cadastrada.")
        if codigo == "visual-tonico":
            expect(detalhe.locator(".inventario-nds-etiquetas span")).to_have_count(2)
            expect(detalhe.locator("[data-ativar-uso]")).to_be_visible()
            capturar(page, f"depois-{perfil}-{largura}-{tema}.png")
    assert max(alturas) - min(alturas) <= 1, alturas
    assert not erros, erros


def quantidade(app, ids, codigo, destinatario="dono"):
    with app.app_context():
        resultado = db.session.scalar(select(PersonagemItem.quantidade).where(
            PersonagemItem.item_id == UUID(ids[codigo]),
            PersonagemItem.personagem_id == UUID(ids[destinatario])))
        return resultado or 0


@pytest.mark.parametrize("perfil,largura,altura", [
    ("jogador", 390, 844),
    ("mestre", 1720, 864),
])
def test_confirmar_uso_transferencia_e_equipamento(page: Page, live_site_url,
                                                    inventario_visual, app_visual,
                                                    perfil, largura, altura):
    ids = inventario_visual
    rota = abrir(page, live_site_url, ids, perfil, largura, altura)
    posts = []
    page.on("request", lambda req: posts.append(req.url) if
            req.method == "POST" and "/inventario/" in req.url else None)
    modal = page.locator("#inventario-confirmacao-11b")
    confirm = modal.locator("[data-confirmar-operacao]")
    cancelar = modal.locator("[data-uso-cancelar]")

    detalhe = escolher(page, ids, "visual-isca")
    detalhe.locator("[data-ativar-uso]").click()
    expect(modal).to_be_visible()
    expect(modal).to_contain_text("Isca visual")
    assert not posts and quantidade(app_visual, ids, "visual-isca") == 3
    cancelar.click()
    expect(modal).not_to_be_visible()
    assert not posts and quantidade(app_visual, ids, "visual-isca") == 3
    detalhe.locator("[data-ativar-uso]").click()
    capturar(page, f"confirmacao-uso-{perfil}-{largura}.png")
    assert modal.evaluate("(el) => el.getBoundingClientRect().width <= innerWidth")
    with page.expect_navigation():
        confirm.click()
    assert len(posts) == 1 and posts[-1].endswith("/usar")
    assert quantidade(app_visual, ids, "visual-isca") == 2

    page.locator('[data-aba-botao="avulsos"]').click()
    detalhe = escolher(page, ids, "visual-tonico")
    detalhe.locator("[data-ativar-uso]").click()
    expect(modal).to_be_visible()
    expect(confirm).to_be_disabled()
    modal.locator("[data-confirmacao-pokemon]").select_option(ids["pokemon"])
    expect(confirm).to_be_enabled()
    page.keyboard.press("Escape")
    expect(modal).not_to_be_visible()
    assert len(posts) == 1 and quantidade(app_visual, ids, "visual-tonico") == 3
    detalhe.locator("[data-ativar-uso]").click()
    modal.locator("[data-confirmacao-pokemon]").select_option(ids["pokemon"])
    with page.expect_navigation():
        confirm.click()
    assert len(posts) == 2 and quantidade(app_visual, ids, "visual-tonico") == 2
    with app_visual.app_context():
        assert db.session.get(Pokemon, UUID(ids["pokemon"])).pv_atual > 1

    page.locator('[data-aba-botao="avulsos"]').click()
    detalhe = escolher(page, ids, "visual-corda")
    form = detalhe.locator("form[data-confirmacao='transferir']")
    form.locator("select").select_option(ids["destino"])
    form.locator("input[name='quantidade']").fill("2")
    form.get_by_role("button", name="Enviar").click()
    expect(modal).to_contain_text("Destino visual")
    expect(modal).to_contain_text("2 × Corda visual")
    capturar(page, f"confirmacao-transferir-{perfil}-{largura}.png")
    cancelar.click()
    assert len(posts) == 2 and quantidade(app_visual, ids, "visual-corda") == 3
    form.get_by_role("button", name="Enviar").click()
    with page.expect_navigation():
        confirm.click()
    assert len(posts) == 3 and posts[-1].endswith("/transferir")
    assert quantidade(app_visual, ids, "visual-corda") == 1
    assert quantidade(app_visual, ids, "visual-corda", "destino") == 2

    page.locator('[data-aba-botao="avulsos"]').click()
    detalhe = escolher(page, ids, "visual-amuleto")
    detalhe.locator("[data-equipar-item]").click()
    equip = page.locator("#inventario-equipar-10c4")
    expect(equip).to_be_visible()
    expect(equip).to_contain_text("Amuleto visual")
    equip.locator("select").select_option(ids["pokemon"])
    equip.locator("[data-equipar-cancelar]").click()
    assert len(posts) == 3
    detalhe.locator("[data-equipar-item]").click()
    equip.locator("select").select_option(ids["pokemon"])
    with page.expect_navigation():
        equip.get_by_role("button", name="Confirmar equipamento").click()
    assert len(posts) == 4 and posts[-1].endswith("/equipar")
    assert quantidade(app_visual, ids, "visual-amuleto") == 2

    devolucao = page.locator(".inventario-nds-equipados")
    devolucao.locator("summary").click()
    devolucao.get_by_role("button", name="Devolver").click()
    expect(modal).to_contain_text("Amuleto visual")
    cancelar.click()
    assert len(posts) == 4
    devolucao.get_by_role("button", name="Devolver").click()
    with page.expect_navigation():
        confirm.click()
    assert len(posts) == 5 and posts[-1].endswith("/desequipar")
    assert quantidade(app_visual, ids, "visual-amuleto") == 3
