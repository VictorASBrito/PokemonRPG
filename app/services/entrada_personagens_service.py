"""Nove entradas visuais *explicitamente permitidas* para jogadores de Ankar.

Não converte login em autorização: todos os IDs e papéis são verificados no
PostgreSQL a cada POST. Perfil mestre, administrador e tester nunca são aceitos.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from flask import current_app, url_for
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import Campanha, CampanhaMembro, Personagem, Usuario

TOTAL_SLOTS = 9
SPRITE_PERMITIDO = re.compile(r"^img/login-personagens/[a-zA-Z0-9_-]+\.(?:png|gif|webp|jpg|jpeg)$")
ANGULOS = (-148, -111, -74, -37, 0, 37, 74, 111, 148)


def caminho_configuracao() -> Path:
    informado = current_app.config.get("LOGIN_PERSONAGENS_ARQUIVO")
    return Path(informado) if informado else Path(current_app.root_path).parent / "data" / "entrada_personagens.json"


def configuracao_login() -> list[dict]:
    """Fail closed: apenas arquivo habilitado com nove logins distintos."""
    try:
        documento = json.loads(caminho_configuracao().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        return []
    if not isinstance(documento, dict) or documento.get("habilitado") is not True:
        return []
    itens = documento.get("slots")
    if not isinstance(itens, list) or len(itens) != TOTAL_SLOTS:
        return []
    resultado = []
    for item in itens:
        if not isinstance(item, dict):
            return []
        login = str(item.get("login") or "").strip().lower()
        if not login or len(login) > 80 or any(x["login"] == login for x in resultado):
            return []
        sprite = str(item.get("sprite") or "").strip()
        if sprite and not SPRITE_PERMITIDO.fullmatch(sprite):
            return []
        resultado.append({"login": login, "sprite": sprite})
    return resultado


def _consulta_jogadores(logins: list[str], campanha_codigo: str):
    return db.session.execute(
        select(Usuario, Personagem)
        .join(Personagem, Personagem.usuario_id == Usuario.id)
        .join(Campanha, Personagem.campanha_id == Campanha.id)
        .join(CampanhaMembro,
              (CampanhaMembro.usuario_id == Usuario.id) &
              (CampanhaMembro.campanha_id == Campanha.id))
        .where(
            func.lower(Usuario.login).in_(logins),
            Usuario.perfil == "jogador",  # tester/mestre/admin bloqueados
            Usuario.ativo.is_(True),
            Personagem.ativo.is_(True),
            Campanha.ativo.is_(True),
            Campanha.codigo == campanha_codigo,
            CampanhaMembro.papel == "jogador",
        )
    ).all()


def _coordenadas(indice: int) -> tuple[float, float]:
    ang = math.radians(ANGULOS[indice])
    return round(50 + 40 * math.sin(ang), 2), round(48 - 40 * math.cos(ang), 2)


def slots_vazios() -> list[dict]:
    resultado = []
    for i in range(TOTAL_SLOTS):
        x, y = _coordenadas(i)
        sprite = f"img/login-personagens/slot-{i + 1:02}.png"
        imagem = url_for("static", filename=sprite) if (Path(current_app.static_folder) / sprite).is_file() else ""
        resultado.append({"numero": i + 1, "x": x, "y": y, "nome": f"Slot {i + 1}",
                          "imagem": imagem, "disponivel": False})
    return resultado


def listar_slots_visuais(*, campanha_codigo: str) -> list[dict]:
    configurados = configuracao_login()
    saida = slots_vazios()
    if not configurados:
        return saida
    encontrados = {
        u.login.lower(): (u, p)
        for u, p in _consulta_jogadores([s["login"] for s in configurados], campanha_codigo)
    }
    for indice, item in enumerate(configurados):
        usuario_personagem = encontrados.get(item["login"])
        if usuario_personagem is None:
            continue
        _, personagem = usuario_personagem
        imagem = personagem.foto_url or ""
        sprite = item["sprite"]
        if sprite:
            arquivo = Path(current_app.static_folder) / sprite
            if arquivo.is_file():
                imagem = url_for("static", filename=sprite)
        saida[indice].update(nome=personagem.nome, imagem=imagem, disponivel=True)
    return saida


def personagem_para_entrada(numero: int, *, campanha_codigo: str):
    """Revalida slot + vínculo da campanha no instante da autenticação."""
    configurados = configuracao_login()
    if not 1 <= numero <= TOTAL_SLOTS or len(configurados) != TOTAL_SLOTS:
        return None
    registro = configurados[numero - 1]
    encontrados = _consulta_jogadores([registro["login"]], campanha_codigo)
    for usuario, personagem in encontrados:
        if usuario.login.lower() == registro["login"]:
            campanha = db.session.get(Campanha, personagem.campanha_id)
            return usuario, personagem, campanha
    return None


def candidatos_a_slots(*, campanha_codigo: str):
    """Listagem de configuração; não habilita ninguém automaticamente."""
    return db.session.execute(
        select(Usuario.login, Personagem.nome)
        .join(Personagem, Personagem.usuario_id == Usuario.id)
        .join(Campanha, Campanha.id == Personagem.campanha_id)
        .join(CampanhaMembro, (CampanhaMembro.campanha_id == Campanha.id) &
              (CampanhaMembro.usuario_id == Usuario.id))
        .where(Usuario.perfil == "jogador", Usuario.ativo.is_(True),
               Personagem.ativo.is_(True), Campanha.ativo.is_(True),
               Campanha.codigo == campanha_codigo, CampanhaMembro.papel == "jogador")
        .order_by(Personagem.ordem_painel.asc().nullslast(), func.lower(Personagem.nome))
    ).all()
