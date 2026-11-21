"""Prévia reversível, persistência e tema do personagem no Chromium."""
import pytest
from playwright.sync_api import Page, expect


def entrar(page, base, perfil="jogador"):
    page.goto(base + "/login/coringa")
    page.locator("#login").fill("bartz-db" if perfil == "jogador" else "mestre-db")
    page.locator("#senha").fill("abc123" if perfil == "jogador" else "senha-db")
    page.get_by_role("button", name="Entrar").click()
    page.goto(base + ("/jogador/inventario" if perfil == "jogador" else "/mestre/dashboard"))


@pytest.mark.parametrize("largura,altura", [(1366, 768), (320, 700)])
def test_aparencia_previa_cancelamento_e_persistencia(page: Page, live_site_url, largura, altura):
    page.set_viewport_size({"width": largura, "height": altura})
    entrar(page, live_site_url)
    raiz = page.locator("html")
    expect(raiz).to_have_attribute("data-palette", "classico")
    page.locator("#tema-toggle").click()
    dialog = page.locator("#aparencia-dialogo")
    expect(dialog).to_be_visible()
    assert dialog.locator('input[name="paleta"]').count() == 6
    dialog.locator('input[name="paleta"][value="ankar"]').check()
    dialog.locator('input[name="modo"][value="light"]').check()
    expect(raiz).to_have_attribute("data-theme", "light")
    expect(raiz).to_have_attribute("data-palette", "ankar")
    expect(page.locator(".inventario-nds-bag")).to_have_css("background-color", "rgb(240, 244, 241)")
    dialog.get_by_role("button", name="Cancelar").click()
    expect(raiz).to_have_attribute("data-palette", "classico")
    page.locator("#tema-toggle").click()
    dialog.locator('input[name="paleta"][value="personagem"]').check()
    dialog.locator('input[name="modo"][value="dark"]').check()
    expect(raiz).to_have_attribute("data-palette", "personagem")
    assert dialog.evaluate("(el) => el.getBoundingClientRect().width <= innerWidth")
    with page.expect_response(lambda r: r.url.endswith("/preferencias/aparencia")) as resposta:
        dialog.get_by_role("button", name="Salvar aparência").click()
    assert resposta.value.ok
    expect(dialog).not_to_be_visible()
    page.reload()
    expect(raiz).to_have_attribute("data-theme", "dark")
    expect(raiz).to_have_attribute("data-palette", "personagem")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.locator("#tema-toggle").click()
    dialog.locator('input[name="modo"][value="auto"]').check()
    page.emulate_media(color_scheme="light")
    expect(raiz).to_have_attribute("data-theme", "light")
    page.keyboard.press("Escape")
    expect(raiz).to_have_attribute("data-theme", "dark")
