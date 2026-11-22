"""Ficha de edição 13C: layout responsivo e contrato de campos preservado."""
from sqlalchemy import select
import pytest
from playwright.sync_api import Page, expect

from app.extensions import db
from app.models.db import Golpe, Pokemon, PokemonGolpe


@pytest.fixture()
def ficha_com_golpe(app_visual):
    with app_visual.app_context():
        pokemon = db.session.scalar(select(Pokemon))
        golpe = db.session.scalar(select(Golpe).where(Golpe.codigo == "arranhao"))
        pokemon.apelido = "Parceiro de teste com nome comprido"
        db.session.add(PokemonGolpe(pokemon_id=pokemon.id, golpe_id=golpe.id, posicao=1))
        pid = pokemon.id
        db.session.commit()
    return pid


@pytest.mark.parametrize("largura,altura,tema,mestre", [
    (1720, 864, "dark", False),
    (1366, 768, "light", True),
    (390, 844, "dark", False),
    (320, 700, "light", True),
])
def test_ficha_responsiva_e_campos_preservados(
    page: Page, app_visual, live_site_url, ficha_com_golpe, largura, altura, tema, mestre
):
    page.set_viewport_size({"width": largura, "height": altura})
    page.add_init_script(f"localStorage.setItem('pokemon-rpg-tema', '{tema}')")
    page.goto(f"{live_site_url}/login/coringa")
    page.locator("#login").fill("mestre-db" if mestre else "bartz-db")
    page.locator("#senha").fill("senha-db" if mestre else "abc123")
    page.get_by_role("button", name="Entrar").click()
    prefixo = f"/mestre/jogadores/{app_visual.config['TEST_IDS']['personagem']}" if mestre else "/jogador"
    page.goto(f"{live_site_url}{prefixo}/pokemon/{ficha_com_golpe}?retorno=boxes")
    expect(page.locator("html")).to_have_attribute("data-theme", tema)
    expect(page.locator(".ficha-pokemon-13c")).to_be_visible()
    expect(page.locator("#identidade-pokemon")).to_be_visible()
    expect(page.locator(".atributo-pokemon-card")).to_have_count(6)
    expect(page.locator('[name^="bonus_"]')).to_have_count(6)
    slots = page.locator("[data-golpe-slot]")
    expect(slots).to_have_count(4)
    expect(slots.first.locator("[data-golpe-input]")).to_have_value("Arranhão")
    expect(slots.first.locator("[data-golpe-tipo] .etiqueta-tipo")).to_have_text("Grama")
    expect(slots.first.locator("[data-golpe-dano]")).to_have_text("2d6")
    for slot in slots.all():
        expect(slot.locator("[data-golpe-efeito-card]")).to_have_count(1)
    assert page.locator(".ficha-pokemon-13c").evaluate("""root => {
        const alvo = root.getBoundingClientRect();
        const blocos = root.querySelectorAll('section, .ficha-golpe-slot, .campo-calculado, .atributo-pokemon-card');
        return [...blocos].every(el => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.left >= alvo.left - 1 && r.right <= alvo.right + 1;
        });
    }""")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    assert page.locator(".barra-salvar-pokemon").evaluate("(el) => getComputedStyle(el).position") == "static"
    expect(page.locator(".barra-salvar-pokemon [data-abrir-exclusao]")).to_have_count(0)
    expect(page.locator(".ficha-pokemon-perigo [data-abrir-exclusao]")).to_be_visible()
    expect(page.locator("#especie_nome")).to_have_count(1 if mestre else 0)
    page.locator("#pv_atual").fill("20")
    assert page.locator("#ficha-pv-barra").evaluate("(el) => el.value") == 20
    page.locator("#apelido").fill("Parceiro atualizado")
    page.get_by_role("button", name="Salvar alterações").click()
    expect(page.locator("#apelido")).to_have_value("Parceiro atualizado")
    with app_visual.app_context():
        pokemon = db.session.get(Pokemon, ficha_com_golpe)
        assert pokemon.apelido == "Parceiro atualizado"
        assert pokemon.pv_atual == 20
        assert len(pokemon.golpes) == 1
