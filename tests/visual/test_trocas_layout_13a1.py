"""Regressão: checkbox não pode ocupar a largura dos cartões de troca."""
from uuid import UUID

import pytest
from playwright.sync_api import Page, expect

from app.extensions import db
from app.models.db import CampanhaMembro, Personagem, Pokemon, TrocaPokemon, Usuario
from app.services.senha_service import gerar_hash_senha


@pytest.fixture()
def negociacao_visual(app_visual):
    with app_visual.app_context():
        cfg = app_visual.config["TEST_IDS"]
        autor = db.session.get(Personagem, UUID(cfg["personagem"]))
        usuario = Usuario(login="troca-visual", nome="Outro jogador", perfil="jogador",
                          senha_hash=gerar_hash_senha("senha-troca"), ativo=True)
        outro = Personagem(usuario=usuario, campanha_id=autor.campanha_id, nome="Treinador B", nivel=48)
        db.session.add_all([usuario, outro, CampanhaMembro(usuario=usuario,
                            campanha_id=autor.campanha_id, papel="jogador")])
        db.session.flush()
        for pos in range(1, 5):
            db.session.add(Pokemon(personagem_id=autor.id,
                            forma_pokemon_id=UUID(cfg["formas"]["bulbasaur"]),
                            apelido=f"Parceiro com nome comprido {pos}",
                            localizacao="box", posicao=pos, pv_atual=10,
                            genero="Macho", ativo=True))
        troca = TrocaPokemon(campanha_id=autor.campanha_id, proponente_id=autor.id,
                             destinatario_id=outro.id, estado="negociacao",
                             oferta_a=[], oferta_b=[])
        db.session.add(troca)
        db.session.flush()
        rota = f"/jogador/boxes/trocas/{troca.id}"
        db.session.commit()
    return rota


@pytest.mark.parametrize("largura,altura,tema", [
    (1720, 864, "dark"), (1366, 768, "light"),
    (390, 844, "dark"), (320, 700, "light"),
])
def test_cartoes_de_troca_legiveis_e_selecao_limitada(
    page: Page, live_site_url, negociacao_visual, largura, altura, tema
):
    page.set_viewport_size({"width": largura, "height": altura})
    page.add_init_script(f"localStorage.setItem('pokemon-rpg-tema', '{tema}')")
    page.goto(f"{live_site_url}/login/coringa")
    page.locator("#login").fill("bartz-db")
    page.locator("#senha").fill("abc123")
    page.get_by_role("button", name="Entrar").click()
    page.goto(f"{live_site_url}{negociacao_visual}")
    expect(page.locator("html")).to_have_attribute("data-theme", tema)
    escolhas = page.locator(".troca-escolha")
    expect(escolhas).to_have_count(4)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    for escolha in escolhas.all():
        checkbox = escolha.locator('input[type="checkbox"]')
        cartao = escolha.locator(".troca-pokemon")
        expect(checkbox).to_be_visible()
        expect(cartao).to_be_visible()
        assert escolha.evaluate("""el => {
          const row = el.getBoundingClientRect();
          const c = el.querySelector('input').getBoundingClientRect();
          const card = el.querySelector('.troca-pokemon').getBoundingClientRect();
          const name = el.querySelector('.troca-pokemon strong');
          const range = document.createRange();
          range.selectNodeContents(name);
          const text = range.getBoundingClientRect();
          const image = el.querySelector('img').getBoundingClientRect();
          return c.width >= 16 && c.width <= 24 && c.height >= 16 && c.height <= 24 &&
            card.width >= 140 && card.height < 240 && c.right <= card.left &&
            card.right <= row.right + 1 && image.width >= 40 &&
            text.left >= card.left && text.right <= card.right + 1 &&
            text.height < 100;
        }"""), "Checkbox ou conteúdo do cartão fora das dimensões esperadas"
    checks = page.locator('.troca-escolha input[type="checkbox"]')
    for i in range(3):
        checks.nth(i).check()
    expect(checks.nth(3)).to_be_disabled()
    expect(page.locator("[data-troca-contagem]")).to_contain_text("3/3 selecionados")
    checks.nth(0).uncheck()
    expect(checks.nth(3)).to_be_enabled()
    page.get_by_role("button", name="Salvar oferta").click()
    expect(page.locator(".troca-escolha input:checked")).to_have_count(2)
    expect(page.locator(".troca-colunas .troca-pokemon")).to_have_count(2)
    expect(page.get_by_role("button", name="Confirmar troca")).to_be_enabled()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
