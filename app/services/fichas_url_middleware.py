"""Reescrita de URL /p/<login>/... mantendo o prefixo em SCRIPT_NAME.

Middleware WSGI puro, sem sessão, acesso ao banco ou dependências Flask.
Isso faz url_for() preservar automaticamente o contexto da ficha nos links,
formulários e URLs de recursos estáticos do mesmo navegador.
"""
from __future__ import annotations

import re
from typing import Callable

_LOGIN = r"[a-z0-9][a-z0-9_.-]{0,79}"
_PREFIXO = re.compile(rf"^/p/(?P<login>{_LOGIN})(?P<resto>/.*|$)")


class FichasURLMiddleware:
    def __init__(self, app: Callable):
        self.app = app

    def __call__(self, environ: dict, start_response: Callable):
        caminho = str(environ.get("PATH_INFO") or "")
        resultado = _PREFIXO.match(caminho)
        if resultado:
            login = resultado.group("login")
            script_original = str(environ.get("SCRIPT_NAME") or "").rstrip("/")
            prefixo = f"/p/{login}"
            environ["ANKAR_FICHA_LOGIN"] = login
            environ["ANKAR_SCRIPT_ROOT_ORIGINAL"] = script_original
            environ["SCRIPT_NAME"] = script_original + prefixo
            environ["PATH_INFO"] = resultado.group("resto") or "/"
        return self.app(environ, start_response)
