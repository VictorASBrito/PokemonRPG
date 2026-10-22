from __future__ import annotations

import click
from flask import Blueprint, current_app
from sqlalchemy import func, select, text

from app.extensions import db
from app.models.db import Campanha, CampanhaMembro, Personagem, Usuario

usuarios_cli = Blueprint("usuarios_cli", __name__)


@usuarios_cli.cli.group("usuarios")
def usuarios_group() -> None:
    """Diagnósticos da autenticação e dos vínculos de usuários."""


@usuarios_group.command("verificar")
def verificar() -> None:
    campanha_codigo = str(current_app.config["CAMPANHA_PADRAO"])
    campanha = db.session.execute(
        select(Campanha).where(Campanha.codigo == campanha_codigo)
    ).scalar_one_or_none()

    if campanha is None:
        raise click.ClickException(
            f'A campanha "{campanha_codigo}" não foi encontrada no PostgreSQL.'
        )

    total_usuarios = db.session.scalar(select(func.count(Usuario.id))) or 0
    total_ativos = db.session.scalar(
        select(func.count(Usuario.id)).where(Usuario.ativo.is_(True))
    ) or 0
    total_membros = db.session.scalar(
        select(func.count(CampanhaMembro.id)).where(
            CampanhaMembro.campanha_id == campanha.id
        )
    ) or 0
    total_personagens = db.session.scalar(
        select(func.count(Personagem.id)).where(
            Personagem.campanha_id == campanha.id,
            Personagem.ativo.is_(True),
        )
    ) or 0

    jogadores_sem_personagem = list(
        db.session.execute(
            select(Usuario.login)
            .join(
                CampanhaMembro,
                CampanhaMembro.usuario_id == Usuario.id,
            )
            .outerjoin(
                Personagem,
                (Personagem.usuario_id == Usuario.id)
                & (Personagem.campanha_id == campanha.id)
                & (Personagem.ativo.is_(True)),
            )
            .where(
                CampanhaMembro.campanha_id == campanha.id,
                CampanhaMembro.papel == "jogador",
                Personagem.id.is_(None),
            )
        ).scalars()
    )

    click.echo(f"Campanha: {campanha.nome} ({campanha.codigo})")
    click.echo(f"Usuários: {total_usuarios} | ativos: {total_ativos}")
    click.echo(f"Membros da campanha: {total_membros}")
    click.echo(f"Personagens ativos: {total_personagens}")
    if jogadores_sem_personagem:
        click.echo(
            "Jogadores sem personagem: " + ", ".join(jogadores_sem_personagem)
        )
        raise click.ClickException("Foram encontrados vínculos incompletos.")
    # Além do modelo ORM, confirme a restrição que está realmente ativa no
    # PostgreSQL. Uma revisão Alembic registrada não garante que esta CHECK
    # não tenha sido restaurada manualmente com os perfis antigos.
    if db.engine.dialect.name == "postgresql":
        restricoes = db.session.execute(text("""
            SELECT conname, pg_get_constraintdef(oid) AS definicao
            FROM pg_constraint
            WHERE conrelid = 'usuarios'::regclass AND contype = 'c'
        """)).all()
        restricoes_perfil = [
            (nome, definicao) for nome, definicao in restricoes
            if "perfil" in str(definicao).lower()
        ]
        if not restricoes_perfil or any(
            "'tester'" not in str(definicao).lower()
            for _, definicao in restricoes_perfil
        ):
            raise click.ClickException(
                "A restrição de perfil no PostgreSQL ainda bloqueia Tester "
                "(ou está ausente). Execute: flask --app app.py db upgrade"
            )
        click.echo("Restrição de usuários: Tester permitido no PostgreSQL.")

    click.echo("Autenticação e vínculos estão consistentes.")
