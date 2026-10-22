"""Verificações da configuração usada para testes temporários externos."""

from pathlib import Path

from flask import Flask

from app.config import Config


def test_cookies_seguros_e_hosts_do_tunel(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("POKEMON_RPG_TESTE_REMOTO", "1")
    monkeypatch.setenv("POKEMON_RPG_HOSTS_ADICIONAIS", "teste.exemplo.com")
    aplicativo = Flask("teste")
    Config(tmp_path).aplicar(aplicativo)

    assert aplicativo.config["SESSION_COOKIE_SECURE"] is True
    assert aplicativo.config["SESSION_COOKIE_HTTPONLY"] is True
    assert aplicativo.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert aplicativo.config["PREFERRED_URL_SCHEME"] == "https"
    assert ".trycloudflare.com" in aplicativo.config["TRUSTED_HOSTS"]
    assert "teste.exemplo.com" in aplicativo.config["TRUSTED_HOSTS"]
    @aplicativo.get("/")
    def inicio():
        return "ok"

    cliente = aplicativo.test_client()
    assert cliente.get("/", base_url="https://rpg.trycloudflare.com").status_code == 200
    assert cliente.get("/", base_url="https://site-estranho.example").status_code == 400


def test_modo_local_sem_restricao_de_tunel(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("POKEMON_RPG_TESTE_REMOTO", raising=False)
    monkeypatch.delenv("POKEMON_RPG_HOSTS_ADICIONAIS", raising=False)
    aplicativo = Flask("teste")
    Config(tmp_path).aplicar(aplicativo)
    assert aplicativo.config["SESSION_COOKIE_SECURE"] is False
    assert aplicativo.config["TRUSTED_HOSTS"] is None


def test_servidor_teste_nao_liga_debugger() -> None:
    codigo = (Path(__file__).resolve().parents[1] / "servidor_teste.py").read_text(
        encoding="utf-8"
    )
    assert 'serve(aplicativo, host="127.0.0.1"' in codigo
    assert 'os.environ.pop("FLASK_DEBUG", None)' in codigo


def test_tunel_publico_sem_lista_de_emails() -> None:
    codigo = (
        Path(__file__).resolve().parents[1] / "scripts" / "2_tunel_cloudflare.ps1"
    ).read_text(encoding="utf-8")
    assert "--allowed-mail" not in codigo
    assert "-Emails" not in codigo
    assert "tunnel --url http://127.0.0.1:5000" in codigo
