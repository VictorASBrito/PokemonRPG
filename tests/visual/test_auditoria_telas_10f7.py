"""10F.7 — Auditoria ampla, em Chromium real, de rotas GET e navegação.

O Flask e o SQLite pertencem ao teste. Não há writes de gameplay.
O relatório é verificável no log do GitHub Actions e capturas de tela.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


EVIDENCIAS = Path("test-results/auditoria-telas")
RESOLUCOES = [(390, 844), (1366, 768)]

PAGINAS_JOGADOR = [
    ("dashboard", "/jogador/dashboard"),
    ("equipe", "/jogador/equipe"),
    ("boxes", "/jogador/boxes"),
    ("inventario", "/jogador/inventario"),
    ("capturaveis", "/jogador/capturaveis"),
    ("ficha", "/jogador/ficha"),
    ("campo", "/campo"),
]

PAGINAS_MESTRE = [
    ("dashboard", "/mestre/dashboard"),
    ("jogadores", "/mestre/jogadores"),
    ("novo-jogador", "/mestre/jogadores/novo"),
    ("capturaveis", "/mestre/capturaveis"),
    ("catalogo-inicio", "/mestre/catalogo"),
    ("catalogo-pokemons", "/mestre/catalogo/pokemons"),
    ("catalogo-novo-pokemon", "/mestre/catalogo/pokemons/novo"),
    ("catalogo-golpes", "/mestre/catalogo/golpes"),
    ("catalogo-novo-golpe", "/mestre/catalogo/golpes/novo"),
    ("catalogo-itens", "/mestre/catalogo/itens"),
    ("catalogo-novo-item", "/mestre/catalogo/itens/novo"),
    ("catalogo-npcs", "/mestre/catalogo/npcs"),
    ("catalogo-novo-npc", "/mestre/catalogo/npcs/novo"),
    ("gerador-npcs", "/mestre/npcs"),
    ("regiao", "/regiao/ankar"),
    ("campo", "/campo"),
]

MATRIZ = [
    pytest.param(perfil, nome, rota, largura, altura, id=f"{perfil}-{nome}-{largura}")
    for perfil, paginas in (
        ("jogador", PAGINAS_JOGADOR),
        ("mestre", PAGINAS_MESTRE),
    )
    for nome, rota in paginas
    for largura, altura in RESOLUCOES
]


def entrar(page: Page, base: str, perfil: str) -> None:
    page.goto(f"{base}/login/coringa", wait_until="domcontentloaded")
    expect(page.locator("#login")).to_be_visible()
    page.locator("#login").fill("bartz-db" if perfil == "jogador" else "mestre-db")
    page.locator("#senha").fill("abc123" if perfil == "jogador" else "senha-db")
    page.get_by_role("button", name="Entrar").click()
    expect(page).not_to_have_url(re.compile(r"/login(?:/coringa)?$"))


@pytest.mark.parametrize("perfil,nome,rota,largura,altura", MATRIZ)
def test_tela_sem_corte_ou_erro_javascript(
    page: Page,
    live_site_url: str,
    perfil: str,
    nome: str,
    rota: str,
    largura: int,
    altura: int,
) -> None:
    page.set_viewport_size({"width": largura, "height": altura})
    erros_js: list[str] = []
    page.on("pageerror", lambda erro: erros_js.append(str(erro)))

    entrar(page, live_site_url, perfil)
    resposta = page.goto(
        f"{live_site_url}{rota}",
        wait_until="domcontentloaded",
        timeout=30000,
    )
    page.wait_for_timeout(100)  # Permite inicialização dos scripts defer.
    assert resposta is not None

    # Gerar evidência antes de falhar para permitir inspeção na CI.
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=str(EVIDENCIAS / f"{perfil}-{nome}-{largura}.png"),
        full_page=False,
        animations="disabled",
    )
    medidas = page.evaluate("""() => ({
      viewport: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
      titulo: document.title
    })""")
    print(
        f"AUDITORIA {perfil}/{nome} {largura}x{altura}: "
        f"HTTP {resposta.status}; viewport={medidas['viewport']}; "
        f"scroll={medidas['scroll']}; body={medidas['body']}; "
        f"url={page.url}; erros_js={erros_js[:2]}"
    )
    assert resposta.status == 200, (
        f"{perfil}/{nome}: HTTP {resposta.status} em {page.url}"
    )
    assert page.url.rstrip("/") == f"{live_site_url}{rota}".rstrip("/"), (
        f"{perfil}/{nome}: redirecionou para {page.url}"
    )
    assert medidas["scroll"] <= medidas["viewport"] + 1, (
        f"{perfil}/{nome}: overflow horizontal {medidas}"
    )
    assert not erros_js, f"{perfil}/{nome}: exceções JS: {erros_js}"


@pytest.mark.parametrize("perfil", ["jogador", "mestre"])
def test_menu_mobile_abre_e_navega(
    page: Page, live_site_url: str, perfil: str,
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    entrar(page, live_site_url, perfil)
    url = "/jogador/dashboard" if perfil == "jogador" else "/mestre/dashboard"
    page.goto(f"{live_site_url}{url}")
    toggle = page.locator("[data-ui-nav-toggle]")
    expect(toggle).to_be_visible()
    expect(toggle).to_have_attribute("aria-expanded", "false")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    navegacao = page.locator("[data-ui-navegacao]")
    expect(navegacao).to_be_visible()
    alvo = "Equipe" if perfil == "jogador" else "Catálogo"
    navegacao.get_by_role("link", name=alvo).click()
    assert ("/jogador/equipe" if perfil == "jogador" else "/mestre/catalogo") in page.url
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


def test_mobile_pequeno_navegacao_e_bag(
    page: Page, live_site_url: str,
) -> None:
    page.set_viewport_size({"width": 320, "height": 700})
    entrar(page, live_site_url, "jogador")
    page.goto(f"{live_site_url}/jogador/inventario")
    abas = page.locator(".inventario-nds-aba")
    assert abas.count() == 5
    for aba in abas.all():
        rect = aba.bounding_box()
        assert rect and rect["x"] >= -1 and rect["x"] + rect["width"] <= 321
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


def test_regiao_ankar_e_exclusiva_do_mestre(
    page: Page, live_site_url: str,
) -> None:
    """A tela nao integra o menu jogador: seu redirecionamento e intencional."""
    entrar(page, live_site_url, "jogador")
    resposta = page.goto(f"{live_site_url}/regiao/ankar")
    assert resposta is not None
    assert page.url == f"{live_site_url}/login"
