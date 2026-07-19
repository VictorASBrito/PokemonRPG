from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
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
from app.services.compatibilidade_legado import buscar_id_jogador_legado
from app.services.importacao.utils import uuid_legado
from app.services.jogador_service import (
    adicionar_jogador_na_campanha,
    criar_jogador,
)
from app.services.json_service import ler_json, salvar_json
from app.services.senha_service import gerar_hash_senha
from app.services.personagem_service import carregar_regras_personagem


@dataclass(slots=True)
class JogadorCriado:
    usuario: Usuario
    personagem: Personagem
    jogador_id_legado: str


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
    data_dir: str | Path,
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
                Usuario.ativo.is_(True),
            )
            .options(
                selectinload(Personagem.usuario),
                selectinload(Personagem.atributos).selectinload(PersonagemAtributo.atributo),
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
        jogador_id_legado = buscar_id_jogador_legado(
            data_dir,
            campanha_codigo,
            personagem.usuario_id,
        )

        resultado.append(
            {
                "id": jogador_id_legado or str(personagem.id),
                "personagem_id": str(personagem.id),
                "usuario": {
                    "id": str(personagem.usuario.id),
                    "nome": personagem.usuario.nome,
                    "login": personagem.usuario.login,
                    "ativo": personagem.usuario.ativo,
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
                "compatibilidade_json": jogador_id_legado is not None,
            }
        )
    return campanha, resultado


def _gravar_usuario_legado(
    *,
    data_dir: Path,
    usuario_id_legado: str,
    jogador_id_legado: str,
    nome: str,
    login: str,
    senha_hash: str,
) -> None:
    arquivo = data_dir / "usuarios.json"
    dados = ler_json(arquivo, {"usuarios": []})
    usuarios = dados.setdefault("usuarios", [])
    usuarios.append(
        {
            "id": usuario_id_legado,
            "login": login,
            "nome": nome,
            "perfil": "jogador",
            "jogador_id": jogador_id_legado,
            "senha_hash": senha_hash,
            "ativo": True,
        }
    )
    salvar_json(arquivo, dados)


def criar_jogador_postgresql(
    *,
    data_dir: str | Path,
    campanha_codigo: str,
    nome: str,
    login: str,
    senha: str,
) -> JogadorCriado:
    data_path = Path(data_dir)
    campanha = obter_campanha(campanha_codigo)
    if campanha is None:
        raise ValueError("A campanha configurada não foi encontrada no PostgreSQL.")

    login_normalizado = login.strip().lower()
    existente = db.session.execute(
        select(Usuario.id).where(func.lower(Usuario.login) == login_normalizado)
    ).scalar_one_or_none()
    if existente is not None:
        raise ValueError("Já existe um usuário com esse login.")

    usuario_id_legado = f"usr_{uuid.uuid4().hex[:12]}"
    jogador_id_legado = f"jog_{uuid.uuid4().hex[:12]}"
    senha_hash = gerar_hash_senha(senha)

    regras_personagem = carregar_regras_personagem(campanha.id)
    atributos_config = {
        item["id"]: item for item in regras_personagem.get("atributos", [])
    }
    saude_inicial = int(
        atributos_config.get("saude", {}).get("valor_inicial", 1)
    )

    usuario = Usuario(
        id=uuid_legado("usuario", usuario_id_legado),
        login=login_normalizado,
        nome=nome,
        senha_hash=senha_hash,
        perfil="jogador",
        ativo=True,
    )
    personagem = Personagem(
        id=uuid_legado("personagem", jogador_id_legado),
        usuario=usuario,
        campanha=campanha,
        nome=nome,
        nivel=int(regras_personagem.get("nivel_inicial", 1)),
        pokedolares=0,
        pv_atual=saude_inicial
        * int(regras_personagem.get("pv_por_ponto_saude", 10)),
        ativo=True,
    )
    membro = CampanhaMembro(
        id=uuid_legado("campanha-membro", f"{campanha.id}:{usuario.id}"),
        campanha=campanha,
        usuario=usuario,
        papel="jogador",
    )
    db.session.add_all([usuario, personagem, membro])
    db.session.flush()

    atributos = list(
        db.session.execute(
            select(Atributo).where(
                Atributo.ativo.is_(True),
                Atributo.escopo.in_(["personagem", "ambos"]),
            ).order_by(Atributo.ordem, Atributo.nome)
        ).scalars()
    )
    for atributo in atributos:
        db.session.add(
            PersonagemAtributo(
                id=uuid_legado(
                    "personagem-atributo",
                    f"{personagem.id}:{atributo.id}",
                ),
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

    # A compatibilidade é criada dentro da mesma operação lógica. Esses JSONs
    # serão removidos quando ficha, Pokémon e Box forem convertidos ao banco.
    _gravar_usuario_legado(
        data_dir=data_path,
        usuario_id_legado=usuario_id_legado,
        jogador_id_legado=jogador_id_legado,
        nome=nome,
        login=login_normalizado,
        senha_hash=senha_hash,
    )
    criar_jogador(
        data_dir=data_path,
        campanha_id=campanha_codigo,
        jogador_id=jogador_id_legado,
        usuario_id=usuario_id_legado,
        nome=nome,
    )
    adicionar_jogador_na_campanha(data_path, campanha_codigo, jogador_id_legado)

    db.session.commit()
    return JogadorCriado(
        usuario=usuario,
        personagem=personagem,
        jogador_id_legado=jogador_id_legado,
    )


def alterar_atividade_usuario(usuario_id: str, ativo: bool) -> Usuario | None:
    try:
        identificador = uuid.UUID(usuario_id)
    except (TypeError, ValueError):
        return None

    usuario = db.session.get(Usuario, identificador)
    if usuario is None or usuario.perfil != "jogador":
        return None
    usuario.ativo = ativo
    db.session.commit()
    return usuario
