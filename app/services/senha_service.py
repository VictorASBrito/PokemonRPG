from __future__ import annotations

import hashlib
import hmac
import secrets


def gerar_hash_senha(senha: str, iteracoes: int = 600_000) -> str:
    """Gera um hash PBKDF2 compatível com os usuários já importados."""
    salt = secrets.token_hex(16)
    hash_senha = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        iteracoes,
    ).hex()
    return f"pbkdf2_sha256${iteracoes}${salt}${hash_senha}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Valida a senha sem expor diferenças de tempo entre os hashes."""
    try:
        algoritmo, iteracoes, salt, hash_esperado = senha_hash.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False

        hash_recebido = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt.encode("utf-8"),
            int(iteracoes),
        ).hex()
        return hmac.compare_digest(hash_recebido, hash_esperado)
    except (AttributeError, TypeError, ValueError):
        return False
