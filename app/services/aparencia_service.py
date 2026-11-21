"""Paletas compartilhadas e tema derivado exclusivamente do sprite local."""
from collections import Counter
from colorsys import rgb_to_hls, hls_to_rgb
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from flask import current_app, session
from PIL import Image
from sqlalchemy import select

from app.extensions import db
from app.models.db import Personagem, Usuario
from app.services.entrada_personagens_service import configuracao_login
from app.services.permissoes_service import PERFIS_JOGADOR, PERFIS_MESTRE

MODOS = ("light", "dark", "auto")
# Fundo, superfície, superfície interna, texto, texto suave, borda, destaque,
# hover, destaque suave, texto sobre destaque.
PALETAS = {
    "classico": {"nome": "Clássico", "light": ["#f4f6f8","#ffffff","#eef1f5","#1f2937","#566176","#c8d0dc","#b52a33","#941f1f","#fce8e9","#ffffff"], "dark": ["#0d1218","#18202a","#222c38","#f5f7fa","#b8c3d1","#47566a","#ff777d","#ff9397","#402127","#161217"]},
    "ankar": {"nome": "Ankar", "light": ["#f0f4f1","#ffffff","#dee8e1","#20382f","#4b6256","#a7bfb0","#176b59","#115344","#d5ebe2","#ffffff"], "dark": ["#111c1a","#1b2925","#293c35","#e3efe8","#b3c9be","#4b695b","#68c9ac","#90dfc7","#29483d","#10251c"]},
    "eclipse": {"nome": "Eclipse", "light": ["#f3f0f8","#ffffff","#e5ddef","#332744","#655474","#bfb0d0","#7045aa","#58328e","#ebe0f8","#ffffff"], "dark": ["#15121f","#211c30","#322941","#ece6f8","#c5b9d8","#594b71","#b49aef","#c8b4f7","#41325e","#21152e"]},
    "expedicao": {"nome": "Expedição", "light": ["#f4efe5","#fffdf7","#e9dfcf","#46382b","#695747","#c7b49b","#92532a","#75401f","#f2e1cf","#ffffff"], "dark": ["#1c1815","#29221c","#3b3026","#f0e4d5","#cbb7a5","#6b5541","#e2aa70","#f2c18f","#523b27","#281c12"]},
    "horizonte": {"nome": "Horizonte", "light": ["#edf3f8","#ffffff","#d9e6ef","#203649","#4c6376","#a8bfd0","#19658c","#124c6e","#d9edf7","#ffffff"], "dark": ["#0d1823","#172737","#253c50","#e1eff8","#b2cadb","#48677c","#62c4e5","#8cd8ef","#23465a","#102633"]},
}
TOKENS = ("fundo","superficie","superficie-suave","texto","texto-suave","borda",
          "primaria","primaria-escura","primaria-suave","texto-primaria")


def _uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def titular_aparencia():
    """Resolve exclusivamente o titular autenticado; nunca aceita ID do cliente."""
    uid = _uuid(session.get("usuario_id"))
    if not uid:
        return None, None
    usuario = db.session.get(Usuario, uid)
    if not usuario or not usuario.ativo:
        return None, None
    if session.get("perfil") == "mestre" and usuario.perfil in PERFIS_MESTRE:
        return usuario, usuario
    if session.get("perfil") == "jogador" and usuario.perfil in PERFIS_JOGADOR:
        pid, cid = _uuid(session.get("personagem_id")), _uuid(session.get("campanha_id"))
        if pid and cid:
            personagem = db.session.scalar(select(Personagem).where(
                Personagem.id == pid, Personagem.usuario_id == uid,
                Personagem.campanha_id == cid, Personagem.ativo.is_(True)))
            return personagem, usuario
    return None, None


def _hex(h, s, l):
    return "#" + "".join(f"{round(v * 255):02x}" for v in hls_to_rgb(h, l, s))


@lru_cache(maxsize=64)
def _matiz_sprite(path, mtime):
    # Sprite versionado/local: ignorar transparência, contorno e tons neutros.
    try:
        with Image.open(path) as image:
            if image.width * image.height > 4_000_000:
                return None
            image = image.convert("RGBA")
            image.thumbnail((128, 128), Image.Resampling.NEAREST)
            grupos = Counter()
            for r, g, b, alpha in image.getdata():
                if alpha < 200:
                    continue
                h, l, s = rgb_to_hls(r/255, g/255, b/255)
                if s < .27 or not .16 < l < .84:
                    continue
                # Pele em tons pêssego é reduzida, não eliminada.
                peso = s * (.28 if .045 < h < .13 and l > .55 else 1)
                grupos[round(h * 24) % 24] += peso
            return grupos.most_common(1)[0][0] / 24 if grupos else None
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def paleta_personagem(usuario):
    if usuario is None:
        return None
    for item in configuracao_login():
        if item["login"] != usuario.login.lower() or not item["sprite"]:
            continue
        raiz = Path(current_app.static_folder).resolve()
        path = (raiz / item["sprite"]).resolve()
        if not path.is_relative_to(raiz):
            return None
        try:
            h = _matiz_sprite(str(path), path.stat().st_mtime_ns)
        except OSError:
            return None
        if h is None:
            return None
        # Matiz do sprite, luminâncias controladas para contraste em ambos os modos.
        return {"nome": "Meu personagem",
                "light": [_hex(h,.20,.96),"#ffffff",_hex(h,.24,.90),_hex(h,.20,.17),
                          _hex(h,.20,.34),_hex(h,.22,.68),_hex(h,.64,.26),
                          _hex(h,.65,.20),_hex(h,.38,.91),"#ffffff"],
                "dark": [_hex(h,.20,.09),_hex(h,.20,.14),_hex(h,.22,.21),_hex(h,.22,.94),
                         _hex(h,.20,.76),_hex(h,.22,.40),_hex(h,.65,.75),
                         _hex(h,.65,.82),_hex(h,.30,.26),"#111111"]}
    return None


def opcoes_aparencia(titular, usuario):
    opcoes = dict(PALETAS)
    if isinstance(titular, Personagem):
        personal = paleta_personagem(usuario)
        if personal:
            opcoes["personagem"] = personal
    return opcoes


def contexto_aparencia():
    titular, usuario = titular_aparencia()
    opcoes = opcoes_aparencia(titular, usuario)
    modo = titular.aparencia_modo if titular else None
    paleta = titular.aparencia_paleta if titular else None
    return {"modo": modo if modo in MODOS else None,
            "paleta": paleta if paleta in opcoes else "classico",
            "opcoes": opcoes, "tokens": TOKENS, "autenticado": titular is not None}
