from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import Campanha, CampanhaMembro, Personagem, Usuario
from app.services.senha_service import verificar_senha


@dataclass(slots=True)
class ResultadoAutenticacao:
    usuario: Usuario
    campanha: Campanha | None
    membro: CampanhaMembro | None
    personagem: Personagem | None

    @property
    def perfil_sessao(self) -> str:
        return "mestre" if self.usuario.perfil in {"mestre", "administrador"} else "jogador"


def autenticar_usuario(
    login: str,
    senha: str,
    campanha_codigo: str,
) -> ResultadoAutenticacao | None:
    login_normalizado = login.strip().lower()
    if not login_normalizado or not senha:
        return None

    usuario = db.session.execute(
        select(Usuario)
        .where(func.lower(Usuario.login) == login_normalizado)
        .options(selectinload(Usuario.membros_campanha))
    ).scalar_one_or_none()

    if usuario is None or not usuario.ativo:
        return None
    if not verificar_senha(senha, usuario.senha_hash):
        return None

    campanha = db.session.execute(
        select(Campanha).where(
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    ).scalar_one_or_none()

    membro = None
    personagem = None
    if campanha is not None:
        membro = db.session.execute(
            select(CampanhaMembro).where(
                CampanhaMembro.campanha_id == campanha.id,
                CampanhaMembro.usuario_id == usuario.id,
            )
        ).scalar_one_or_none()

        personagem = db.session.execute(
            select(Personagem).where(
                Personagem.campanha_id == campanha.id,
                Personagem.usuario_id == usuario.id,
                Personagem.ativo.is_(True),
            )
        ).scalar_one_or_none()

    # Mestres importados são associados à campanha. Jogadores precisam de
    # vínculo e personagem para acessar as telas da campanha.
    if usuario.perfil == "jogador" and (campanha is None or membro is None):
        return None

    return ResultadoAutenticacao(
        usuario=usuario,
        campanha=campanha,
        membro=membro,
        personagem=personagem,
    )
