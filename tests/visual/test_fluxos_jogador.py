"""Fluxos reais no Chromium: Flask de testes, usuário e Pokémon fictícios.

Todas as ações são de navegação/UI; nenhum formulário de gameplay é enviado.
"""
from pathlib import Path

from playwright.sync_api import Page, expect


EVIDENCIAS = Path("test-results/screenshots")


def _capturar(page: Page, nome: str) -> None:
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCIAS / nome), full_page=True)


def _entrar_com_jogador_teste(page: Page, live_site_url: str) -> None:
    page.goto(f"{live_site_url}/login/coringa", wait_until="domcontentloaded")
    expect(page.locator("#login")).to_be_visible()
    page.locator("#login").fill("bartz-db")
    page.locator("#senha").fill("abc123")  # Credenciais exclusivas do SQLite da fixture.
    page.get_by_role("button", name="Entrar").click()
    page.goto(f"{live_site_url}/jogador/dashboard", wait_until="domcontentloaded")
    expect(page.locator(".painel-identidade")).to_be_visible()


def test_sprite_do_personagem_abre_ficha_sem_menu_extra(
    page: Page, live_site_url: str
) -> None:
    page.set_viewport_size({"width": 1366, "height": 900})
    _entrar_com_jogador_teste(page, live_site_url)

    sprite = page.locator(".foto-treinador-link .foto-treinador-sprite")
    expect(sprite).to_be_visible()
    assert sprite.evaluate("(img) => img.complete && img.naturalWidth > 0")
    assert page.get_by_role("link", name="Minha ficha").count() == 0
    _capturar(page, "painel-desktop.png")

    page.get_by_role("link", name="Abrir ficha de Bartz").click()
    expect(page).to_have_url(f"{live_site_url}/jogador/ficha")
    expect(page.locator("#nome")).to_have_value("Bartz")


def test_atributos_nao_encolhem_ao_expandir_e_recolher(
    page: Page, live_site_url: str
) -> None:
    page.set_viewport_size({"width": 1366, "height": 900})
    _entrar_com_jogador_teste(page, live_site_url)

    atributos = page.locator(".painel-atributos-treinador")
    antes = atributos.bounding_box()
    assert antes and antes["height"] > 0
    card = page.locator("[data-dashboard-pokemon-card]").first
    expect(card).to_have_attribute("aria-expanded", "false")

    # Confirma a interação real via teclado, além da medição de layout.
    card.focus()
    card.press("Enter")
    expect(card).to_have_attribute("aria-expanded", "true")
    depois = atributos.bounding_box()
    assert depois is not None
    assert abs(depois["height"] - antes["height"]) <= 2, (
        f"Quadro de atributos mudou: antes={antes['height']:.1f}px, "
        f"depois={depois['height']:.1f}px"
    )
    _capturar(page, "pokemon-expandido-desktop.png")

    page.locator("[data-dashboard-pokemon-collapse]").first.click()
    expect(card).to_have_attribute("aria-expanded", "false")
    recolhido = atributos.bounding_box()
    assert recolhido is not None
    assert abs(recolhido["height"] - antes["height"]) <= 2


def test_bag_mobile_sem_corte_nas_categorias(
    page: Page, live_site_url: str
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    _entrar_com_jogador_teste(page, live_site_url)
    page.goto(f"{live_site_url}/jogador/inventario", wait_until="domcontentloaded")

    bag = page.locator(".inventario-nds-bag")
    expect(bag).to_be_visible()
    botoes = page.locator(".inventario-nds-aba")
    assert botoes.count() == 5

    for botao in botoes.all():
        expect(botao).to_be_visible()
        caixa = botao.bounding_box()
        assert caixa is not None
        assert caixa["x"] >= -1
        assert caixa["x"] + caixa["width"] <= 391

    largura = page.evaluate("document.documentElement.scrollWidth")
    assert largura <= 391, f"Bag extrapolou a tela de 390px: {largura}px"
    botoes.last.click()
    expect(botoes.last).to_have_attribute("aria-pressed", "true")
    _capturar(page, "bag-mobile-390.png")
