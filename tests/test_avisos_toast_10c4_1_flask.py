"""Teste com o app Flask real do PokemonRPG; usa fixture app_db (DB de testes)."""

def test_flash_e_global_tem_duracao_e_nao_ocupa_conteudo(client_db):
    # Login tradicional/coringa renderiza base.html, sem autenticar para este teste.
    with client_db.session_transaction() as sess:
        sess["_flashes"] = [
            ("sucesso", "Ficha salva com sucesso no PostgreSQL."),
            ("erro", "Operacao rejeitada no teste."),
        ]
    pagina = client_db.get("/login/coringa")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert html.count('data-tempo-ms="1500"') == 2
    assert 'class="aviso-toast aviso-toast--sucesso"' in html
    assert 'class="aviso-toast aviso-toast--erro"' in html
    assert "Ficha salva com sucesso no PostgreSQL." in html
    assert 'class="alerta alerta-' not in html
    assert 'avisos-toast-10c4-1.js' in html
    assert 'avisos-toast-10c4-1.css' in html
