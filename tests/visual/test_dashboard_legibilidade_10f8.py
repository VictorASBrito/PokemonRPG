"""Regressão de legibilidade do dashboard em Chromium, com equipe completa."""
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from sqlalchemy import select

from app.extensions import db
from app.models.db import Golpe, Pokemon, PokemonGolpe

EVIDENCIAS = Path("test-results/dashboard-10f8")


@pytest.fixture()
def equipe_completa(app_visual):
    with app_visual.app_context():
        primeiro = db.session.scalar(select(Pokemon))
        assert primeiro is not None
        golpes = db.session.scalars(select(Golpe).order_by(Golpe.nome)).all()
        assert len(golpes) >= 2
        for pos, golpe in enumerate(golpes[:2], 1):
            db.session.add(PokemonGolpe(pokemon=primeiro, golpe=golpe, posicao=pos))
        for pos in range(2, 7):
            db.session.add(Pokemon(
                personagem_id=primeiro.personagem_id,
                forma_pokemon_id=primeiro.forma_pokemon_id,
                apelido=f"Parceiro {pos} com nome comprido",
                localizacao="equipe",
                posicao=pos,
                genero="Macho",
                pv_atual=30,
                ativo=True,
            ))
        db.session.commit()


@pytest.mark.parametrize("largura,altura,tema", [
    (1720, 864, "dark"),
    (1366, 768, "light"),
    (390, 844, "dark"),
])
def test_painel_legivel_e_golpes_compactos(
    page: Page, live_site_url: str, equipe_completa,
    largura: int, altura: int, tema: str,
):
    page.set_viewport_size({"width": largura, "height": altura})
    page.add_init_script(f"localStorage.setItem('pokemon-rpg-tema', '{tema}')")
    page.goto(f"{live_site_url}/login/coringa")
    page.locator("#login").fill("bartz-db")
    page.locator("#senha").fill("abc123")
    page.get_by_role("button", name="Entrar").click()
    page.goto(f"{live_site_url}/jogador/dashboard")
    expect(page.locator("html")).to_have_attribute("data-theme", tema)
    cards = page.locator("[data-dashboard-pokemon-card]")
    expect(cards).to_have_count(6)
    card = cards.first
    expect(card.locator(".atributos-base-pokemon strong")).to_have_count(6)
    assert card.locator(".atributos-base-pokemon strong").first.evaluate(
        "(el) => parseFloat(getComputedStyle(el).fontSize)"
    ) >= 17
    expect(card.locator(".golpes-pokemon-dashboard > div")).to_have_count(4)
    expect(card.locator(".golpe-dashboard-preenchido")).to_have_count(2)
    expect(card.locator(".golpe-dashboard-vazio")).to_have_count(2)
    expect(card.locator(".golpe-dashboard-dano").first).to_be_visible()
    expect(card.locator(".golpe-dashboard-tipo").first).to_be_visible()
    assert card.evaluate("""el => {
      const card = el.getBoundingClientRect();
      return [...el.querySelectorAll('.golpes-pokemon-dashboard > div')].every(
        row => row.getBoundingClientRect().bottom <= card.bottom + 1);
    }"""), "Golpes compactos cortados na grade normal"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCIAS / f"normal-{largura}-{tema}.png"), full_page=True)

    card.focus()
    card.press("Enter")
    expect(card).to_have_attribute("aria-expanded", "true")
    slots = card.locator(".pokemon-dashboard-golpe-detalhado")
    expect(slots).to_have_count(4)
    for slot in slots.all():
        box = slot.bounding_box()
        assert box is not None and 50 <= box["height"] <= 115, box
    expect(card.locator(".pokemon-dashboard-golpe-resumo small").first).to_be_visible()
    assert card.locator(".pokemon-dashboard-atributos-totais strong").first.evaluate(
        "(el) => parseFloat(getComputedStyle(el).fontSize)"
    ) >= 19
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.screenshot(path=str(EVIDENCIAS / f"expandido-{largura}-{tema}.png"), full_page=True)
    card.locator("[data-dashboard-pokemon-collapse]").click()
    expect(card).to_have_attribute("aria-expanded", "false")
