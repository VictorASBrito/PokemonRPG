from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.models.jogador import agora_iso, estrutura_jogador_padrao
from app.services.backup_service import criar_backup
from app.services.json_service import ler_json, salvar_json


def caminho_campanha(data_dir: str | Path, campanha_id: str) -> Path:
    return Path(data_dir) / "campanhas" / campanha_id


def caminho_jogador(data_dir: str | Path, campanha_id: str, jogador_id: str) -> Path:
    return caminho_campanha(data_dir, campanha_id) / "jogadores" / f"{jogador_id}.json"


def caminho_regras_treinador(data_dir: str | Path) -> Path:
    return Path(data_dir) / "catalogo" / "regras_treinador.json"


def carregar_regras_treinador(data_dir: str | Path) -> dict[str, Any]:
    return ler_json(
        caminho_regras_treinador(data_dir),
        {
            "versao": "custom",
            "pv_por_ponto_saude": 10,
            "nivel_minimo": 1,
            "nivel_maximo": 100,
            "nivel_inicial": 1,
            "limite_numeros_shiny": 10,
            "atributos": [],
            "origens": [],
            "classes": [],
            "estilos_combate": [],
        },
    )


def carregar_jogador(
    data_dir: str | Path,
    campanha_id: str,
    jogador_id: str,
) -> dict[str, Any] | None:
    return ler_json(caminho_jogador(data_dir, campanha_id, jogador_id), None)


def criar_jogador(
    *,
    data_dir: str | Path,
    campanha_id: str,
    jogador_id: str,
    usuario_id: str,
    nome: str,
) -> dict[str, Any]:
    regras = carregar_regras_treinador(data_dir)
    jogador = estrutura_jogador_padrao(
        jogador_id=jogador_id,
        usuario_id=usuario_id,
        campanha_id=campanha_id,
        nome=nome,
        regras=regras,
    )
    salvar_json(caminho_jogador(data_dir, campanha_id, jogador_id), jogador)
    return jogador


def salvar_jogador(
    *,
    data_dir: str | Path,
    campanha_id: str,
    jogador: dict[str, Any],
) -> None:
    jogador_id = str(jogador["id"])
    arquivo = caminho_jogador(data_dir, campanha_id, jogador_id)
    pasta_backup = caminho_campanha(data_dir, campanha_id) / "backups"
    criar_backup(arquivo, pasta_backup)
    jogador["atualizado_em"] = agora_iso()
    salvar_json(arquivo, jogador)


def listar_jogadores(
    data_dir: str | Path,
    campanha_id: str,
) -> list[dict[str, Any]]:
    base = caminho_campanha(data_dir, campanha_id)
    campanha = ler_json(base / "campanha.json", {"jogadores": []})
    resultado: list[dict[str, Any]] = []

    for jogador_id in campanha.get("jogadores", []):
        jogador = carregar_jogador(data_dir, campanha_id, str(jogador_id))
        if jogador:
            resultado.append(jogador)

    resultado.sort(
        key=lambda item: str(item.get("treinador", {}).get("nome", "")).casefold()
    )
    return resultado


def adicionar_jogador_na_campanha(
    data_dir: str | Path,
    campanha_id: str,
    jogador_id: str,
) -> None:
    arquivo = caminho_campanha(data_dir, campanha_id) / "campanha.json"
    campanha = ler_json(arquivo, {"id": campanha_id, "jogadores": []})
    jogadores = [str(item) for item in campanha.setdefault("jogadores", [])]
    if jogador_id not in jogadores:
        jogadores.append(jogador_id)
    campanha["jogadores"] = jogadores
    salvar_json(arquivo, campanha)


def remover_jogador_da_campanha(
    data_dir: str | Path,
    campanha_id: str,
    jogador_id: str,
) -> None:
    arquivo = caminho_campanha(data_dir, campanha_id) / "campanha.json"
    campanha = ler_json(arquivo, {"id": campanha_id, "jogadores": []})
    campanha["jogadores"] = [
        item for item in campanha.get("jogadores", []) if str(item) != jogador_id
    ]
    salvar_json(arquivo, campanha)


def _inteiro(valor: Any, *, padrao: int = 0) -> int:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return padrao


def _lista_opcoes(regras: dict[str, Any], chave: str) -> set[str]:
    opcoes: set[str] = set()
    for item in regras.get(chave, []):
        if isinstance(item, dict):
            valor = str(item.get("nome", item.get("id", ""))).strip()
        else:
            valor = str(item).strip()
        if valor:
            opcoes.add(valor)
    return opcoes


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
        if numero < 1 or numero > 100:
            erros.append(f"O número shiny {numero} deve estar entre 1 e 100.")
            continue
        if numero not in encontrados:
            encontrados.append(numero)

    encontrados.sort()
    return encontrados, erros


def _normalizar_inventario(nomes: Iterable[str], quantidades: Iterable[str]) -> list[dict[str, Any]]:
    inventario: list[dict[str, Any]] = []
    for nome, quantidade in zip(nomes, quantidades):
        nome_limpo = str(nome).strip()
        if not nome_limpo:
            continue
        qtd = max(0, _inteiro(quantidade, padrao=0))
        inventario.append({"nome": nome_limpo, "quantidade": qtd})
    return inventario


def _normalizar_insigneas(nomes: Iterable[str]) -> list[dict[str, Any]]:
    insigneas: list[dict[str, Any]] = []
    for nome in nomes:
        nome_limpo = str(nome).strip()
        if nome_limpo:
            insigneas.append({"nome": nome_limpo})
    return insigneas


def atualizar_ficha_treinador(
    *,
    jogador: dict[str, Any],
    formulario: Any,
    regras: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    erros: list[str] = []
    treinador_atual = jogador.setdefault("treinador", {})

    nome = str(formulario.get("nome", "")).strip()
    if not nome:
        erros.append("Informe o nome do treinador.")

    idade_texto = str(formulario.get("idade", "")).strip()
    idade: int | None
    if idade_texto:
        idade = _inteiro(idade_texto, padrao=-1)
        if idade < 0 or idade > 150:
            erros.append("A idade deve estar entre 0 e 150.")
    else:
        idade = None

    nivel_minimo = int(regras.get("nivel_minimo", 1))
    nivel_maximo = int(regras.get("nivel_maximo", 100))
    nivel = _inteiro(
        formulario.get("nivel"),
        padrao=int(treinador_atual.get("nivel", regras.get("nivel_inicial", 1))),
    )
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
        opcoes = _lista_opcoes(regras, chave)
        if valor and opcoes and valor not in opcoes:
            erros.append(f"Selecione um {rotulo} disponível na configuração atual.")

    atributos: dict[str, int] = {}
    for atributo in regras.get("atributos", []):
        atributo_id = str(atributo.get("id", "")).strip()
        if not atributo_id:
            continue
        minimo = int(atributo.get("minimo", 1))
        maximo = int(atributo.get("maximo", 6))
        valor = _inteiro(formulario.get(f"atributo_{atributo_id}"), padrao=minimo)
        if valor < minimo or valor > maximo:
            erros.append(
                f'{atributo.get("nome", atributo_id)} deve estar entre {minimo} e {maximo}.'
            )
        atributos[atributo_id] = valor

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
    pv_por_saude = int(regras.get("pv_por_ponto_saude", 10))
    pv_maximo = max(0, saude * pv_por_saude)
    pv_atual = _inteiro(formulario.get("pv_atual"), padrao=pv_maximo)
    if pv_atual > pv_maximo:
        erros.append("Os PV atuais não podem ultrapassar os PV máximos.")
    if pv_atual < -pv_maximo:
        erros.append("Os PV atuais não podem ficar abaixo do limite negativo máximo.")

    candidato = {
        **treinador_atual,
        "nome": nome,
        "nivel": nivel,
        "foto_url": str(formulario.get("foto_url", "")).strip(),
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

    if erros:
        jogador_temporario = dict(jogador)
        jogador_temporario["treinador"] = candidato
        jogador_temporario["inventario"] = _normalizar_inventario(
            formulario.getlist("item_nome"), formulario.getlist("item_quantidade")
        )
        jogador_temporario["insigneas"] = _normalizar_insigneas(
            formulario.getlist("insignea_nome")
        )
        return jogador_temporario, erros

    jogador["treinador"] = candidato
    jogador["inventario"] = _normalizar_inventario(
        formulario.getlist("item_nome"), formulario.getlist("item_quantidade")
    )
    jogador["insigneas"] = _normalizar_insigneas(
        formulario.getlist("insignea_nome")
    )
    jogador["atualizado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return jogador, []
