
import os

import pytest
from playwright.sync_api import Page, expect


# Sem URL externa, levanta o Flask de testes usando somente SQLite.
# Quem quiser inspecionar seu servidor local pode fornecer a variável abaixo.


@pytest.mark.parametrize(
    "largura,altura",
    [(390, 844), (1366, 768)],
)
def test_site_responsivo(
    page: Page,
    largura: int,
    altura: int,
    live_site_url: str,
):
    page.set_viewport_size({
        "width": largura,
        "height": altura,
    })

    url = os.getenv("POKEMON_RPG_TEST_URL", live_site_url)
    page.goto(url, wait_until="domcontentloaded")

    expect(page.locator("body")).to_be_visible()

    largura_documento = page.evaluate(
        "document.documentElement.scrollWidth"
    )

    print(
        f"Tela: {largura}px | "
        f"Documento: {largura_documento}px"
    )

    assert largura_documento <= largura + 1
