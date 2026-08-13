from pathlib import Path


def test_base_carrega_tema_e_icone_de_pokebola() -> None:
    raiz = Path(__file__).resolve().parents[1]
    base = (raiz / "templates" / "base.html").read_text(encoding="utf-8")
    assert "css/refinamento.css" in base
    assert "css/tema.css" in base
    assert "js/tema.js" in base
    assert "img/pokebola.png" in base
    assert "tema-toggle" in base


def test_layout_principal_e_fluido_e_cabecalho_hero_e_compacto() -> None:
    raiz = Path(__file__).resolve().parents[1]
    css = (raiz / "static" / "css" / "refinamento.css").read_text(encoding="utf-8")
    assert "width: 100%" in css
    assert "max-width: none" in css
    assert ".cabecalho-dashboard > div:first-child" in css
    assert "display: none" in css


def test_ficha_aceita_upload_de_foto_do_personagem() -> None:
    raiz = Path(__file__).resolve().parents[1]
    ficha = (raiz / "templates" / "jogador" / "ficha.html").read_text(encoding="utf-8")
    assert 'enctype="multipart/form-data"' in ficha
    assert 'name="foto_arquivo"' in ficha
    assert 'name="remover_foto"' in ficha
    assert "preview-perfil" in ficha


def test_dashboard_pokemon_tem_grade_3x2_e_modo_foco_interativo() -> None:
    raiz = Path(__file__).resolve().parents[1]
    template = (raiz / "templates" / "jogador" / "dashboard.html").read_text(encoding="utf-8")
    css = (raiz / "static" / "css" / "dashboard.css").read_text(encoding="utf-8")
    js = (raiz / "static" / "js" / "dashboard-pokemon.js").read_text(encoding="utf-8")

    assert "data-dashboard-pokemon-grid" in template
    assert "data-dashboard-pokemon-card" in template
    assert "pokemon-dashboard-detalhes-expandidos" in template
    assert "Editar Pokémon" in template
    assert "data-dashboard-pokemon-collapse" in template
    assert "dashboard-pokemon.js" in template
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert ".dashboard-pokemon-modo-foco" in css
    assert ".pokemon-dashboard-em-foco" in css
    assert ".pokemon-dashboard-lateral" in css
    assert "destacar(card)" in js
    assert "if (foco === card) return" in js
    assert "data-dashboard-pokemon-collapse" in js
    assert "evento.key === 'Escape'" in js


def test_modo_escuro_corrige_contraste_dos_slots_e_cartoes() -> None:
    raiz = Path(__file__).resolve().parents[1]
    css = (raiz / "static" / "css" / "tema.css").read_text(encoding="utf-8")

    assert '--fundo: #0d1218' in css
    assert '--superficie: #18202a' in css
    assert '.slot-box-vazio' in css
    assert '.pokemon-dashboard-vazio' in css
    assert '.pokemon-imagem-wrap' in css
    assert '.box-pokemon-imagem-wrap' in css


def test_equipes_e_box_usam_ate_seis_colunas_no_desktop() -> None:
    raiz = Path(__file__).resolve().parents[1]
    pokemon_css = (raiz / "static" / "css" / "pokemon.css").read_text(encoding="utf-8")
    boxes_css = (raiz / "static" / "css" / "boxes.css").read_text(encoding="utf-8")

    assert ".grade-equipe" in pokemon_css
    assert "grid-template-columns: repeat(6, minmax(0, 1fr))" in pokemon_css
    assert ".grade-box-pokemons" in boxes_css
    assert "grid-template-columns: repeat(6, minmax(0, 1fr))" in boxes_css


def test_modo_escuro_nao_cria_fundo_claro_nos_retratos_pokemon() -> None:
    raiz = Path(__file__).resolve().parents[1]
    css = (raiz / "static" / "css" / "tema.css").read_text(encoding="utf-8")

    assert "Retratos Pokémon seguem a mesma hierarquia escura" in css
    assert "radial-gradient(circle at 50% 48%" in css
    assert "var(--superficie-suave)" in css
