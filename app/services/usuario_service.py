from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Atributo,
    Campanha,
    CampanhaMembro,
    ConjuntoRegras,
    Personagem,
    PersonagemAtributo,
    Pokemon,
    Regra,
    RegraValor,
    Usuario,
)
from app.services.personagem_service import carregar_regras_personagem
from app.services.senha_service import gerar_hash_senha


@dataclass(slots=True)
class JogadorCriado:
    usuario: Usuario
    personagem: Personagem


def obter_campanha(codigo: str) -> Campanha | None:
    return db.session.execute(
        select(Campanha).where(
            Campanha.codigo == codigo,
            Campanha.ativo.is_(True),
        )
    ).scalar_one_or_none()


def _valor_regra(campanha_id, codigo: str, padrao: Any) -> Any:
    conjunto = db.session.execute(
        select(ConjuntoRegras).where(
            ConjuntoRegras.campanha_id == campanha_id,
            ConjuntoRegras.em_uso.is_(True),
            ConjuntoRegras.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if conjunto is None:
        return padrao
    valor = db.session.execute(
        select(RegraValor.valor)
        .join(Regra, Regra.id == RegraValor.regra_id)
        .where(
            RegraValor.conjunto_regras_id == conjunto.id,
            Regra.codigo == codigo,
            Regra.ativo.is_(True),
        )
    ).scalar_one_or_none()
    return padrao if valor is None else valor


def _decimal_para_numero(valor: Decimal | int | float | None) -> int | float:
    if valor is None:
        return 0
    numero = Decimal(valor)
    return int(numero) if numero == numero.to_integral_value() else float(numero)


def listar_jogadores_campanha(
    *,
    campanha_codigo: str,
) -> tuple[Campanha | None, list[dict[str, Any]]]:
    campanha = obter_campanha(campanha_codigo)
    if campanha is None:
        return None, []

    personagens = list(
        db.session.execute(
            select(Personagem)
            .join(Usuario, Usuario.id == Personagem.usuario_id)
            .where(
                Personagem.campanha_id == campanha.id,
                Personagem.ativo.is_(True),
            )
            .options(
                selectinload(Personagem.usuario),
                selectinload(Personagem.atributos).selectinload(
                    PersonagemAtributo.atributo
                ),
            )
            .order_by(func.lower(Personagem.nome))
        ).scalars()
    )

    pv_por_saude = int(_valor_regra(campanha.id, "pv-por-ponto-saude", 10))
    resultado: list[dict[str, Any]] = []
    for personagem in personagens:
        atributos = {
            item.atributo.codigo: _decimal_para_numero(item.valor)
            for item in personagem.atributos
        }
        saude = int(atributos.get("saude", 1))
        equipe_total = db.session.scalar(
            select(func.count(Pokemon.id)).where(
                Pokemon.personagem_id == personagem.id,
                Pokemon.ativo.is_(True),
                Pokemon.localizacao == "equipe",
            )
        ) or 0
        resultado.append(
            {
                "id": str(personagem.id),
                "personagem_id": str(personagem.id),
                "usuario": {
                    "id": str(personagem.usuario.id),
                    "nome": personagem.usuario.nome,
                    "login": personagem.usuario.login,
                    "ativo": personagem.usuario.ativo,
                    "perfil": personagem.usuario.perfil,
                },
                "treinador": {
                    "nome": personagem.nome,
                    "classe": personagem.classe,
                    "origem": personagem.origem,
                    "nivel": personagem.nivel,
                    "pv_atual": personagem.pv_atual,
                    "pv_maximo": max(0, saude * pv_por_saude),
                    "pokedolares": personagem.pokedolares,
                    "atributos": atributos,
                },
                "equipe": [None] * int(equipe_total),
                "fonte": "PostgreSQL",
            }
        )
    return campanha, resultado


def criar_jogador_postgresql(
    *,
    campanha_codigo: str,
    nome: str,
    login: str,
    senha: str,
    perfil: str = "jogador",
) -> JogadorCriado:
    from app.services.permissoes_service import PERFIS_PERMITIDOS_GESTAO
    if perfil not in PERFIS_PERMITIDOS_GESTAO:
        raise ValueError("O perfil inicial deve ser Jogador ou Tester.")
    campanha = obter_campanha(campanha_codigo)
    if campanha is None:
        raise ValueError("A campanha configurada não foi encontrada no PostgreSQL.")

    login_normalizado = login.strip().lower()
    existente = db.session.execute(
        select(Usuario.id).where(func.lower(Usuario.login) == login_normalizado)
    ).scalar_one_or_none()
    if existente is not None:
        raise ValueError("Já existe um usuário com esse login.")

    regras_personagem = carregar_regras_personagem(campanha.id)
    atributos_config = {
        item["id"]: item for item in regras_personagem.get("atributos", [])
    }
    saude_inicial = int(
        atributos_config.get("saude", {}).get("valor_inicial", 1)
    )

    proxima_ordem_painel = int(
        db.session.execute(
            select(func.coalesce(func.max(Personagem.ordem_painel), 0) + 1).where(
                Personagem.campanha_id == campanha.id,
                Personagem.ativo.is_(True),
            )
        ).scalar_one()
    )

    usuario = Usuario(
        login=login_normalizado,
        nome=nome,
        senha_hash=gerar_hash_senha(senha),
        perfil=perfil,
        ativo=True,
    )
    personagem = Personagem(
        usuario=usuario,
        campanha=campanha,
        nome=nome,
        nivel=int(regras_personagem.get("nivel_inicial", 1)),
        pokedolares=0,
        pv_atual=saude_inicial
        * int(regras_personagem.get("pv_por_ponto_saude", 10)),
        ordem_painel=proxima_ordem_painel,
        ativo=True,
    )
    membro = CampanhaMembro(
        campanha=campanha,
        usuario=usuario,
        papel="jogador",
    )
    db.session.add_all([usuario, personagem, membro])
    db.session.flush()

    atributos = list(
        db.session.execute(
            select(Atributo)
            .where(
                Atributo.ativo.is_(True),
                Atributo.escopo.in_(["personagem", "ambos"]),
            )
            .order_by(Atributo.ordem, Atributo.nome)
        ).scalars()
    )
    for atributo in atributos:
        db.session.add(
            PersonagemAtributo(
                personagem=personagem,
                atributo=atributo,
                valor=Decimal(
                    str(
                        atributos_config.get(atributo.codigo, {}).get(
                            "valor_inicial", 1
                        )
                    )
                ),
            )
        )

    db.session.commit()
    return JogadorCriado(usuario=usuario, personagem=personagem)


def alterar_atividade_usuario(usuario_id: str, ativo: bool) -> Usuario | None:
    try:
        identificador = uuid.UUID(usuario_id)
    except (TypeError, ValueError):
        return None

    usuario = db.session.get(Usuario, identificador)
    if usuario is None or usuario.perfil not in {"jogador", "tester"}:
        return None
    usuario.ativo = ativo
    db.session.commit()
    return usuario


def alterar_perfil_usuario(
    usuario_id: str, perfil: str, *, campanha_codigo: str, responsavel_id: str
) -> Usuario | None:
    """Mestre só pode alternar usuários da própria campanha entre Jogador/Tester."""
    from app.models.db import HistoricoAlteracao
    from app.services.permissoes_service import PERFIS_PERMITIDOS_GESTAO, PERFIS_MESTRE
    if perfil not in PERFIS_PERMITIDOS_GESTAO:
        raise ValueError("Apenas os perfis Jogador e Tester podem ser atribuídos aqui.")
    try:
        identificador = uuid.UUID(usuario_id)
        responsavel = uuid.UUID(responsavel_id)
    except (ValueError, TypeError):
        raise ValueError("Usuário inválido.")
    campanha = obter_campanha(campanha_codigo)
    if campanha is None:
        raise ValueError("Campanha não encontrada.")
    gestor = db.session.get(Usuario, responsavel)
    if gestor is None or not gestor.ativo or gestor.perfil not in PERFIS_MESTRE:
        raise ValueError("Somente o mestre pode alterar níveis de acesso.")
    vinculo_gestor = db.session.scalar(select(CampanhaMembro.id).where(
        CampanhaMembro.usuario_id == gestor.id,
        CampanhaMembro.campanha_id == campanha.id,
        CampanhaMembro.papel == "mestre",
    ))
    if not vinculo_gestor and gestor.perfil != "administrador":
        raise ValueError("O mestre não está vinculado a esta campanha.")
    usuario = db.session.get(Usuario, identificador)
    if usuario is None or usuario.perfil not in PERFIS_PERMITIDOS_GESTAO:
        return None
    membro = db.session.scalar(select(CampanhaMembro.id).where(
        CampanhaMembro.usuario_id == usuario.id,
        CampanhaMembro.campanha_id == campanha.id,
        CampanhaMembro.papel == "jogador",
    ))
    if membro is None:
        return None
    anterior = usuario.perfil
    if anterior != perfil:
        usuario.perfil = perfil
        db.session.add(HistoricoAlteracao(
            usuario_id=responsavel,
            entidade="usuario",
            registro_id=usuario.id,
            acao="alterar_perfil",
            dados_anteriores={"perfil": anterior},
            dados_novos={"perfil": perfil},
        ))
        db.session.commit()
    return usuario
