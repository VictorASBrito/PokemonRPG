from __future__ import annotations


def _login_mestre(client_db) -> None:
    resposta = client_db.post(
        "/login",
        data={"login": "mestre-db", "senha": "senha-db"},
    )
    assert resposta.status_code == 302


def test_listagens_do_catalogo_usam_pesquisa_dinamica(client_db) -> None:
    _login_mestre(client_db)
    for url in (
        "/mestre/catalogo/pokemons",
        "/mestre/catalogo/golpes",
        "/mestre/catalogo/itens",
    ):
        resposta = client_db.get(url)
        texto = resposta.get_data(as_text=True)
        assert resposta.status_code == 200
        assert "data-pesquisa-dinamica" in texto
        assert "data-pesquisa-resultados" in texto
        assert "pesquisa-dinamica.js" in texto


def test_autocomplete_de_formas_e_golpes_consulta_o_banco(client_db) -> None:
    _login_mestre(client_db)

    resposta = client_db.get("/api/catalogo/formas?q=char")
    assert resposta.status_code == 200
    valores = [item["valor"] for item in resposta.get_json()["itens"]]
    assert "Charmander" in valores
    assert "Bulbasaur" not in valores

    resposta = client_db.get("/api/catalogo/golpes?q=chamas")
    assert resposta.status_code == 200
    valores = [item["valor"] for item in resposta.get_json()["itens"]]
    assert "Ataque de Chamas" in valores


def test_tela_de_novo_pokemon_nao_carrega_catalogo_inteiro_no_html(app_db, client_db) -> None:
    _login_mestre(client_db)
    jogador_id = app_db.config["TEST_IDS"]["personagem"]
    resposta = client_db.get(
        f"/mestre/jogadores/{jogador_id}/equipe/novo?destino=box:box-unica"
    )
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "data-autocomplete-url" in texto
    assert '<datalist id="catalogo-especies"></datalist>' in texto
    assert "autocomplete-catalogo.js" in texto
