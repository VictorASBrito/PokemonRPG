from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from werkzeug.datastructures import FileStorage

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    Atributo,
    Campanha,
    CategoriaItem,
    ConjuntoRegras,
    HistoricoAlteracao,
    Insignia,
    Item,
    Personagem,
    PersonagemAtributo,
    PersonagemInsignia,
    PersonagemItem,
    Regra,
    RegraValor,
)
from app.services.importacao.utils import slug, uuid_legado
from app.services.json_service import ler_json
from app.services.upload_service import (
    ErroUploadImagem,
    excluir_imagem_local,
    preparar_imagem_formulario,
)


@dataclass(slots=True)
class ContextoFicha:
    personagem: Personagem
    regras: dict[str, Any]
    jogador: dict[str, Any]


def _numero(valor: Decimal | int | float | None) -> int | float:
    if valor is None:
        return 0
    numero = Decimal(valor)
    return int(numero) if numero == numero.to_integral_value() else float(numero)


def _inteiro(valor: Any, *, padrao: int = 0) -> int:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return padrao


def _resolver_id_personagem(referencia: str | uuid.UUID) -> uuid.UUID:
    if isinstance(referencia, uuid.UUID):
        return referencia
    try:
        return uuid.UUID(str(referencia))
    except (TypeError, ValueError):
        return uuid_legado("personagem", str(referencia))


def _valor_regra(valores: dict[str, Any], codigo: str, padrao: Any) -> Any:
    valor = valores.get(codigo, padrao)
    return padrao if valor is None else valor


def _lista_configuravel(valor: Any) -> list[dict[str, Any]]:
    if isinstance(valor, dict):
        resultado: list[dict[str, Any]] = []
        for codigo, dados in valor.items():
            if isinstance(dados, dict):
                resultado.append({"id": codigo, "nome": dados.get("nome", codigo), **dados})
            else:
                resultado.append({"id": codigo, "nome": str(dados)})
        return resultado
    if not isinstance(valor, list):
        return []

    resultado = []
    for entrada in valor:
        if isinstance(entrada, dict):
            nome = str(entrada.get("nome") or entrada.get("id") or "").strip()
            if nome:
                resultado.append({**entrada, "nome": nome})
        else:
            nome = str(entrada).strip()
            if nome:
                resultado.append({"id": slug(nome), "nome": nome})
    return resultado


def carregar_regras_personagem(campanha_id: uuid.UUID) -> dict[str, Any]:
    conjunto = db.session.execute(
        select(ConjuntoRegras)
        .where(
            ConjuntoRegras.campanha_id == campanha_id,
            ConjuntoRegras.em_uso.is_(True),
            ConjuntoRegras.ativo.is_(True),
        )
        .options(selectinload(ConjuntoRegras.valores).selectinload(RegraValor.regra))
    ).scalar_one_or_none()

    valores: dict[str, Any] = {}
    versao = "sem-versao"
    if conjunto is not None:
        versao = conjunto.versao
        valores = {
            item.regra.codigo: item.valor
            for item in conjunto.valores
            if item.regra.ativo
        }

    atributos_db = list(
        db.session.execute(
            select(Atributo)
            .where(
                Atributo.ativo.is_(True),
                Atributo.escopo.in_(["personagem", "ambos"]),
            )
            .order_by(Atributo.ordem, func.lower(Atributo.nome))
        ).scalars()
    )
    config_por_codigo = {
        str(item.get("id") or item.get("codigo") or ""): item
        for item in _lista_configuravel(
            _valor_regra(valores, "atributos-personagem-config", [])
        )
    }
    atributos: list[dict[str, Any]] = []
    for atributo in atributos_db:
        config = config_por_codigo.get(atributo.codigo, {})
        atributos.append(
            {
                "id": atributo.codigo,
                "nome": atributo.nome,
                "descricao": atributo.descricao,
                "minimo": _inteiro(config.get("minimo"), padrao=1),
                "maximo": _inteiro(config.get("maximo"), padrao=6),
                "valor_inicial": _inteiro(config.get("valor_inicial"), padrao=1),
            }
        )

    return {
        "versao": versao,
        "pv_por_ponto_saude": _inteiro(
            _valor_regra(valores, "pv-por-ponto-saude", 10), padrao=10
        ),
        "nivel_minimo": _inteiro(
            _valor_regra(valores, "nivel-minimo", 1), padrao=1
        ),
        "nivel_maximo": _inteiro(
            _valor_regra(valores, "nivel-maximo", 100), padrao=100
        ),
        "nivel_inicial": _inteiro(
            _valor_regra(valores, "nivel-inicial", 1), padrao=1
        ),
        "limite_numeros_shiny": _inteiro(
            _valor_regra(valores, "limite-numeros-shiny", 10), padrao=10
        ),
        "limite_equipe": _inteiro(
            _valor_regra(valores, "tamanho-equipe", 6), padrao=6
        ),
        "atributos": atributos,
        "origens": _lista_configuravel(
            _valor_regra(valores, "origens-personagem", [])
        ),
        "classes": _lista_configuravel(
            _valor_regra(valores, "classes-personagem", [])
        ),
        "estilos_combate": _lista_configuravel(
            _valor_regra(valores, "estilos-combate-personagem", [])
        ),
    }


def carregar_personagem(
    referencia: str | uuid.UUID,
    *,
    campanha_codigo: str | None = None,
) -> Personagem | None:
    personagem_id = _resolver_id_personagem(referencia)
    consulta = (
        select(Personagem)
        .where(Personagem.id == personagem_id, Personagem.ativo.is_(True))
        .options(
            selectinload(Personagem.usuario),
            selectinload(Personagem.campanha),
            selectinload(Personagem.atributos).selectinload(PersonagemAtributo.atributo),
            selectinload(Personagem.inventario).selectinload(PersonagemItem.item),
            selectinload(Personagem.insignias).selectinload(PersonagemInsignia.insignia),
        )
    )
    if campanha_codigo:
        consulta = consulta.join(Campanha, Campanha.id == Personagem.campanha_id).where(
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    return db.session.execute(consulta).scalar_one_or_none()


def personagem_para_jogador(
    personagem: Personagem,
    regras: dict[str, Any],
) -> dict[str, Any]:
    atributos = {
        item.atributo.codigo: _numero(item.valor)
        for item in personagem.atributos
        if item.atributo.ativo
    }
    saude = int(atributos.get("saude", 1))
    pv_maximo = max(0, saude * int(regras.get("pv_por_ponto_saude", 10)))

    inventario = sorted(
        (
            {
                "id": str(item.item.id),
                "nome": item.item.nome,
                "quantidade": item.quantidade,
                "categoria": item.item.categoria.nome if item.item.categoria else "",
                "consumivel": item.item.consumivel,
                "equipavel": item.item.equipavel,
                "ativo": item.item.ativo,
            }
            for item in personagem.inventario
            if item.quantidade > 0
        ),
        key=lambda item: item["nome"].casefold(),
    )
    insigneas = sorted(
        (
            {"nome": item.insignia.nome}
            for item in personagem.insignias
            if item.insignia.ativo
        ),
        key=lambda item: item["nome"].casefold(),
    )

    return {
        "id": str(personagem.id),
        "usuario_id": str(personagem.usuario_id),
        "campanha_id": str(personagem.campanha_id),
        "treinador": {
            "nome": personagem.nome,
            "foto_url": personagem.foto_url or "",
            "nivel": personagem.nivel,
            "idade": personagem.idade,
            "genero": personagem.genero or "",
            "origem": personagem.origem or "",
            "classe": personagem.classe or "",
            "estilo_combate": personagem.estilo_combate or "",
            "numeros_shiny": personagem.numeros_shiny or [],
            "pokedolares": personagem.pokedolares,
            "pv_atual": personagem.pv_atual,
            "pv_maximo": pv_maximo,
            "atributos": atributos,
            "beneficios_habilidades": personagem.beneficios_habilidades or "",
            "anotacoes": personagem.anotacoes or "",
        },
        "inventario": inventario,
        "insigneas": insigneas,
    }


def carregar_contexto_ficha(
    referencia: str | uuid.UUID,
    *,
    campanha_codigo: str | None = None,
) -> ContextoFicha | None:
    personagem = carregar_personagem(referencia, campanha_codigo=campanha_codigo)
    if personagem is None:
        return None
    regras = carregar_regras_personagem(personagem.campanha_id)
    return ContextoFicha(
        personagem=personagem,
        regras=regras,
        jogador=personagem_para_jogador(personagem, regras),
    )


def _parse_numeros_shiny(valor: str) -> tuple[list[int], list[str]]:
    erros: list[str] = []
    encontrados: list[int] = []
    texto = valor.replace(";", ",").replace("\n", ",")
    for parte in texto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            numero = int(parte)
        except ValueError:
            erros.append(f'"{parte}" não é um número shiny válido.')
            continue
        if not 1 <= numero <= 100:
            erros.append(f"O número shiny {numero} deve estar entre 1 e 100.")
            continue
        if numero not in encontrados:
            encontrados.append(numero)
    encontrados.sort()
    return encontrados, erros


def _nomes_opcoes(regras: dict[str, Any], chave: str) -> set[str]:
    return {
        str(item.get("nome", "")).strip()
        for item in regras.get(chave, [])
        if str(item.get("nome", "")).strip()
    }


def _normalizar_inventario(
    nomes: Iterable[str], quantidades: Iterable[str]
) -> list[dict[str, Any]]:
    consolidados: dict[str, dict[str, Any]] = {}
    for nome, quantidade in zip(nomes, quantidades):
        nome_limpo = str(nome).strip()
        if not nome_limpo:
            continue
        chave = slug(nome_limpo) or nome_limpo.casefold()
        qtd = max(0, _inteiro(quantidade, padrao=0))
        if chave in consolidados:
            consolidados[chave]["quantidade"] += qtd
        else:
            consolidados[chave] = {"nome": nome_limpo, "quantidade": qtd}
    return list(consolidados.values())


def _normalizar_insigneas(nomes: Iterable[str]) -> list[dict[str, str]]:
    resultado: dict[str, dict[str, str]] = {}
    for nome in nomes:
        nome_limpo = str(nome).strip()
        if nome_limpo:
            resultado[slug(nome_limpo) or nome_limpo.casefold()] = {"nome": nome_limpo}
    return list(resultado.values())


def _dto_formulario(
    personagem: Personagem,
    formulario: Any,
    regras: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    erros: list[str] = []
    atual = personagem_para_jogador(personagem, regras)
    treinador_atual = atual["treinador"]

    nome = str(formulario.get("nome", "")).strip()
    if not nome:
        erros.append("Informe o nome do treinador.")

    idade_texto = str(formulario.get("idade", "")).strip()
    idade: int | None = None
    if idade_texto:
        idade = _inteiro(idade_texto, padrao=-1)
        if idade < 0 or idade > 150:
            erros.append("A idade deve estar entre 0 e 150.")

    nivel_minimo = int(regras.get("nivel_minimo", 1))
    nivel_maximo = int(regras.get("nivel_maximo", 100))
    nivel = _inteiro(formulario.get("nivel"), padrao=personagem.nivel)
    if nivel < nivel_minimo or nivel > nivel_maximo:
        erros.append(
            f"O nível do jogador deve estar entre {nivel_minimo} e {nivel_maximo}."
        )

    origem = str(formulario.get("origem", "")).strip()
    classe = str(formulario.get("classe", "")).strip()
    estilo = str(formulario.get("estilo_combate", "")).strip()
    for valor, chave, rotulo in (
        (origem, "origens", "origem"),
        (classe, "classes", "classe"),
        (estilo, "estilos_combate", "estilo de combate"),
    ):
        opcoes = _nomes_opcoes(regras, chave)
        if valor and opcoes and valor not in opcoes:
            erros.append(f"Selecione um {rotulo} disponível na configuração atual.")

    atributos: dict[str, int] = {}
    for atributo in regras.get("atributos", []):
        codigo = str(atributo.get("id", "")).strip()
        if not codigo:
            continue
        minimo = int(atributo.get("minimo", 1))
        maximo = int(atributo.get("maximo", 6))
        padrao = int(treinador_atual.get("atributos", {}).get(codigo, minimo))
        valor = _inteiro(formulario.get(f"atributo_{codigo}"), padrao=padrao)
        if valor < minimo or valor > maximo:
            erros.append(
                f'{atributo.get("nome", codigo)} deve estar entre {minimo} e {maximo}.'
            )
        atributos[codigo] = valor

    numeros_shiny, erros_shiny = _parse_numeros_shiny(
        str(formulario.get("numeros_shiny", ""))
    )
    erros.extend(erros_shiny)
    limite_shiny = int(regras.get("limite_numeros_shiny", 10))
    if len(numeros_shiny) > limite_shiny:
        erros.append(f"Informe no máximo {limite_shiny} números shiny.")

    pokedolares = _inteiro(formulario.get("pokedolares"), padrao=0)
    if pokedolares < 0:
        erros.append("A quantidade de pokédolares não pode ser negativa.")

    saude = int(atributos.get("saude", 1))
    pv_maximo = max(0, saude * int(regras.get("pv_por_ponto_saude", 10)))
    pv_atual = _inteiro(formulario.get("pv_atual"), padrao=pv_maximo)
    if pv_atual > pv_maximo:
        erros.append("Os PV atuais não podem ultrapassar os PV máximos.")
    if pv_atual < -pv_maximo:
        erros.append("Os PV atuais não podem ficar abaixo do limite negativo máximo.")

    atual["treinador"] = {
        **treinador_atual,
        "nome": nome,
        "foto_url": str(formulario.get("foto_url", "")).strip(),
        "nivel": nivel,
        "idade": idade,
        "genero": str(formulario.get("genero", "")).strip(),
        "origem": origem,
        "classe": classe,
        "estilo_combate": estilo,
        "numeros_shiny": numeros_shiny,
        "pokedolares": pokedolares,
        "pv_atual": pv_atual,
        "pv_maximo": pv_maximo,
        "atributos": atributos,
        "beneficios_habilidades": str(
            formulario.get("beneficios_habilidades", "")
        ).strip(),
        "anotacoes": str(formulario.get("anotacoes", "")).strip(),
    }
    # O inventário possui uma tela própria. A ficha não altera quantidades para
    # evitar que um POST sem os campos antigos apague os itens do personagem.
    atual["inventario"] = atual.get("inventario", [])
    atual["insigneas"] = _normalizar_insigneas(
        formulario.getlist("insignea_nome")
    )
    return atual, erros


def _categoria_inventario() -> CategoriaItem:
    categoria = db.session.execute(
        select(CategoriaItem).where(CategoriaItem.codigo == "inventario-personagem")
    ).scalar_one_or_none()
    if categoria is None:
        categoria = CategoriaItem(
            codigo="inventario-personagem",
            nome="Inventário dos personagens",
            descricao="Itens criados ou selecionados diretamente nas fichas.",
        )
        db.session.add(categoria)
        db.session.flush()
    return categoria


def _sincronizar_inventario(
    personagem: Personagem,
    inventario: list[dict[str, Any]],
) -> None:
    categoria = _categoria_inventario()
    associacoes = {item.item.codigo: item for item in personagem.inventario}
    manter: set[str] = set()

    for entrada in inventario:
        nome = entrada["nome"]
        codigo = slug(nome) or f"item-{uuid.uuid4().hex[:12]}"
        manter.add(codigo)
        item = db.session.execute(
            select(Item).where(Item.codigo == codigo)
        ).scalar_one_or_none()
        if item is None:
            item = Item(
                codigo=codigo,
                nome=nome,
                categoria=categoria,
                personalizado=True,
                ativo=True,
            )
            db.session.add(item)
            db.session.flush()
        else:
            item.nome = nome
            item.ativo = True

        associacao = associacoes.get(codigo)
        if associacao is None:
            personagem.inventario.append(
                PersonagemItem(item=item, quantidade=int(entrada["quantidade"]))
            )
        else:
            associacao.quantidade = int(entrada["quantidade"])

    personagem.inventario[:] = [
        associacao
        for associacao in personagem.inventario
        if associacao.item.codigo in manter
    ]


def _sincronizar_insigneas(
    personagem: Personagem,
    insigneas: list[dict[str, str]],
) -> None:
    associacoes = {item.insignia.codigo: item for item in personagem.insignias}
    manter: set[str] = set()
    for entrada in insigneas:
        nome = entrada["nome"]
        codigo = slug(nome) or f"insignia-{uuid.uuid4().hex[:12]}"
        manter.add(codigo)
        insignia = db.session.execute(
            select(Insignia).where(Insignia.codigo == codigo)
        ).scalar_one_or_none()
        if insignia is None:
            insignia = Insignia(codigo=codigo, nome=nome, ativo=True)
            db.session.add(insignia)
            db.session.flush()
        else:
            insignia.nome = nome
            insignia.ativo = True
        if codigo not in associacoes:
            personagem.insignias.append(PersonagemInsignia(insignia=insignia))

    personagem.insignias[:] = [
        associacao
        for associacao in personagem.insignias
        if associacao.insignia.codigo in manter
    ]


def atualizar_ficha_personagem(
    *,
    personagem: Personagem,
    formulario: Any,
    regras: dict[str, Any],
    arquivo_foto: FileStorage | None = None,
    remover_foto: bool = False,
    usuario_responsavel_id: str | uuid.UUID | None = None,
) -> tuple[dict[str, Any], list[str]]:
    candidato, erros = _dto_formulario(personagem, formulario, regras)
    if erros:
        return candidato, erros

    try:
        imagem = preparar_imagem_formulario(
            arquivo=arquivo_foto,
            url_informada=candidato["treinador"].get("foto_url"),
            remover=remover_foto,
            subpasta="perfis",
            url_atual=personagem.foto_url,
        )
    except ErroUploadImagem as erro:
        return candidato, [str(erro)]

    candidato["treinador"]["foto_url"] = imagem.url or ""
    anterior = personagem_para_jogador(personagem, regras)
    treinador = candidato["treinador"]
    personagem.nome = treinador["nome"]
    personagem.foto_url = treinador["foto_url"] or None
    personagem.nivel = treinador["nivel"]
    personagem.idade = treinador["idade"]
    personagem.genero = treinador["genero"] or None
    personagem.origem = treinador["origem"] or None
    personagem.classe = treinador["classe"] or None
    personagem.estilo_combate = treinador["estilo_combate"] or None
    personagem.numeros_shiny = treinador["numeros_shiny"]
    personagem.pokedolares = treinador["pokedolares"]
    personagem.pv_atual = treinador["pv_atual"]
    personagem.beneficios_habilidades = treinador["beneficios_habilidades"] or None
    personagem.anotacoes = treinador["anotacoes"] or None

    atributos_por_codigo = {item.atributo.codigo: item for item in personagem.atributos}
    catalogo_atributos = {
        item.codigo: item
        for item in db.session.execute(
            select(Atributo).where(
                Atributo.ativo.is_(True),
                Atributo.escopo.in_(["personagem", "ambos"]),
            )
        ).scalars()
    }
    for codigo, valor in treinador["atributos"].items():
        atributo = catalogo_atributos.get(codigo)
        if atributo is None:
            continue
        registro = atributos_por_codigo.get(codigo)
        if registro is None:
            personagem.atributos.append(
                PersonagemAtributo(atributo=atributo, valor=Decimal(str(valor)))
            )
        else:
            registro.valor = Decimal(str(valor))

    _sincronizar_insigneas(personagem, candidato["insigneas"])
    db.session.flush()

    novo = personagem_para_jogador(personagem, regras)
    responsavel: uuid.UUID | None = None
    if usuario_responsavel_id:
        try:
            responsavel = (
                usuario_responsavel_id
                if isinstance(usuario_responsavel_id, uuid.UUID)
                else uuid.UUID(str(usuario_responsavel_id))
            )
        except (TypeError, ValueError):
            responsavel = None
    db.session.add(
        HistoricoAlteracao(
            usuario_id=responsavel,
            entidade="personagem",
            registro_id=personagem.id,
            acao="edicao_ficha",
            dados_anteriores=anterior,
            dados_novos=novo,
        )
    )
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        if imagem.upload_novo:
            excluir_imagem_local(imagem.upload_novo, somente_se_orfa=False)
        raise

    if imagem.url_anterior_substituida:
        excluir_imagem_local(imagem.url_anterior_substituida, somente_se_orfa=True)
    return novo, []



def definir_nivel_personagem_pelo_mestre(
    *,
    personagem_id: str,
    campanha_codigo: str,
    nivel: int,
    responsavel_id: str,
) -> tuple[str, int] | None:
    """Altera só o nível; evita invalidar a ficha por campos legados não editados.

    A autorização do mestre pertence à rota. O personagem é sempre limitado
    à campanha corrente e o nível respeita as regras ativas do PostgreSQL.
    """
    try:
        identificador = uuid.UUID(str(personagem_id))
        responsavel = uuid.UUID(str(responsavel_id))
    except (ValueError, TypeError) as erro:
        raise ValueError("Identificador de personagem ou mestre inválido.") from erro

    from app.models.db import Usuario

    gestor = db.session.get(Usuario, responsavel)
    if gestor is None or not gestor.ativo or gestor.perfil not in {"administrador", "mestre"}:
        raise ValueError("Somente um mestre ativo pode alterar o nível de outro personagem.")

    personagem = db.session.execute(
        select(Personagem)
        .join(Campanha, Campanha.id == Personagem.campanha_id)
        .where(
            Personagem.id == identificador,
            Personagem.ativo.is_(True),
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
        .with_for_update()
    ).scalar_one_or_none()
    if personagem is None:
        return None

    regras = carregar_regras_personagem(personagem.campanha_id)
    minimo = int(regras.get("nivel_minimo", 1))
    maximo = int(regras.get("nivel_maximo", 100))
    if not minimo <= nivel <= maximo:
        raise ValueError(f"O nível deve estar entre {minimo} e {maximo}.")

    anterior = int(personagem.nivel)
    if anterior != nivel:
        personagem.nivel = nivel
        db.session.add(
            HistoricoAlteracao(
                usuario_id=responsavel,
                entidade="personagem",
                registro_id=personagem.id,
                acao="ajustar_nivel",
                dados_anteriores={"nivel": anterior},
                dados_novos={"nivel": nivel},
            )
        )
        db.session.commit()
    return personagem.nome, nivel


def preparar_configuracoes_ficha(
    *,
    data_dir: str | Path,
    campanha_codigo: str,
    sobrescrever: bool = False,
) -> dict[str, int]:
    arquivo = Path(data_dir) / "catalogo" / "regras_treinador.json"
    fonte = ler_json(arquivo, {})
    campanha = db.session.execute(
        select(Campanha).where(
            Campanha.codigo == campanha_codigo,
            Campanha.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if campanha is None:
        raise ValueError(f'A campanha "{campanha_codigo}" não foi encontrada.')
    conjunto = db.session.execute(
        select(ConjuntoRegras).where(
            ConjuntoRegras.campanha_id == campanha.id,
            ConjuntoRegras.em_uso.is_(True),
            ConjuntoRegras.ativo.is_(True),
        )
    ).scalar_one_or_none()
    if conjunto is None:
        raise ValueError("A campanha não possui um conjunto de regras ativo.")

    definicoes = {
        "nivel-inicial": (
            "Nível inicial",
            "personagem",
            "inteiro",
            fonte.get("nivel_inicial", 1),
        ),
        "atributos-personagem-config": (
            "Configuração dos atributos do personagem",
            "personagem",
            "json",
            fonte.get("atributos", []),
        ),
        "origens-personagem": (
            "Origens de personagem",
            "personagem",
            "json",
            fonte.get("origens", []),
        ),
        "classes-personagem": (
            "Classes de personagem",
            "personagem",
            "json",
            fonte.get("classes", []),
        ),
        "estilos-combate-personagem": (
            "Estilos de combate do personagem",
            "personagem",
            "json",
            fonte.get("estilos_combate", []),
        ),
    }

    criadas = 0
    atualizadas = 0
    ignoradas = 0
    for codigo, (nome, categoria, tipo, valor) in definicoes.items():
        regra = db.session.execute(
            select(Regra).where(Regra.codigo == codigo)
        ).scalar_one_or_none()
        if regra is None:
            regra = Regra(
                id=uuid_legado("regra", codigo),
                codigo=codigo,
                nome=nome,
                categoria=categoria,
                tipo_valor=tipo,
                valor_padrao=valor,
                ativo=True,
            )
            db.session.add(regra)
            db.session.flush()
        else:
            regra.nome = nome
            regra.categoria = categoria
            regra.tipo_valor = tipo
            regra.ativo = True
            if sobrescrever:
                regra.valor_padrao = valor

        registro = db.session.execute(
            select(RegraValor).where(
                RegraValor.conjunto_regras_id == conjunto.id,
                RegraValor.regra_id == regra.id,
            )
        ).scalar_one_or_none()
        if registro is None:
            db.session.add(
                RegraValor(
                    id=uuid_legado("regra-valor", f"{conjunto.id}:{regra.id}"),
                    conjunto_regras_id=conjunto.id,
                    regra_id=regra.id,
                    valor=valor,
                )
            )
            criadas += 1
        elif sobrescrever:
            registro.valor = valor
            atualizadas += 1
        else:
            ignoradas += 1

    db.session.commit()
    return {"criadas": criadas, "atualizadas": atualizadas, "ignoradas": ignoradas}
