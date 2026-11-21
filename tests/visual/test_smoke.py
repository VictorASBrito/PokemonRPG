
import os

import pytest
from playwright.sync_api import Page, expect


URL = os.getenv(
    "POKEMON_RPG_TEST_URL",
    "http://127.0.0.1:5000",
)


@pytest.mark.parametrize(
    "largura,altura",
    [(390, 844), (1366, 768)],
)
def test_site_responsivo(
    page: Page,
    largura: int,
    altura: int,
):
    page.set_viewport_size({
        "width": largura,
        "height": altura,
    })

    page.goto(URL, wait_until="domcontentloaded")

    expect(page.locator("body")).to_be_visible()

    largura_documento = page.evaluate(
        "document.documentElement.scrollWidth"
    )

    print(
        f"Tela: {largura}px | "
        f"Documento: {largura_documento}px"
    )

    assert largura_documento <= largura + 1
