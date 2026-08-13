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
