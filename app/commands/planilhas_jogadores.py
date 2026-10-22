"""Importador das nove fichas Excel recebidas para a campanha Ankar.

Os dados foram extraídos das planilhas originais e congelados em JSON. Isso
permite importar usando o projeto normalmente, sem depender de bibliotecas
Excel ou de arquivos .xlsx no computador do mestre.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import click
from flask import Blueprint, current_app
from sqlalchemy import func, select

from app.extensions import db
from app.models.db import (
    Atributo, CampanhaMembro, EspeciePokemon, FormaPokemon, FormaPokemonAtributo,
    FormaPokemonTipo, Golpe, Item, Natureza, Personagem, PersonagemAtributo,
    PersonagemItem, Pokemon, PokemonGolpe, TipoPokemon, Usuario,
)
from app.services.importacao.utils import slug
from app.services.senha_service import gerar_hash_senha
from app.services.usuario_service import obter_campanha

planilhas_jogadores_cli = Blueprint("planilhas_jogadores_cli", __name__)


def normalizar(texto: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return re.sub(
        r"[^a-z0-9]", "",
        "".join(c for c in texto if not unicodedata.combining(c)).lower(),
    )


def carregar_fichas() -> dict[str, Any]:
    caminho = Path(__file__).resolve().parent.parent / "seed" / "fichas_jogadores_ankar.json"
    return json.loads(caminho.read_text(encoding="utf-8"))


def catalogar(registros: list[Any], *campos: str) -> dict[str, list[Any]]:
    """Indexa nomes normalizados; ambiguidades são mantidas, não adivinhadas."""
    resultado: dict[str, list[Any]] = defaultdict(list)
    for registro in registros:
        for campo in campos:
            valor = getattr(registro, campo, None)
            if valor is None:
                continue
            codigo = normalizar(valor)
            if codigo and registro not in resultado[codigo]:
                resultado[codigo].append(registro)
    return resultado


def procurar(indice: dict[str, list[Any]], nome: str):
    encontrados = indice.get(normalizar(nome), [])
    return encontrados[0] if len(encontrados) == 1 else None


def indexar_formas(formas: list[FormaPokemon]):
    """Evita selecionar uma forma regional quando o nome da espécie é ambíguo."""
    nomes = catalogar(formas, "nome", "codigo")
    for forma in formas:
        if forma.categoria == "normal" and forma.especie:
            chave = normalizar(forma.especie.nome)
            if forma not in nomes[chave]:
                nomes[chave].append(forma)
    return nomes


def _rotulo(registro: dict[str, Any]) -> str:
    return f"{registro['login']} / {registro['personagem']['nome']}"


def _catalago_db():
    atributos = list(db.session.execute(select(Atributo).where(Atributo.ativo.is_(True))).scalars())
    formas = list(db.session.execute(select(FormaPokemon)).scalars())
    especies = list(db.session.execute(select(EspeciePokemon)).scalars())
    tipos = list(db.session.execute(select(TipoPokemon)).scalars())
    naturezas = list(db.session.execute(select(Natureza)).scalars())
    golpes = list(db.session.execute(select(Golpe)).scalars())
    itens = list(db.session.execute(select(Item)).scalars())
    return {
        "atributos": catalogar(atributos, "codigo", "nome"),
        "formas": indexar_formas(formas),
        "especies": catalogar(especies, "nome", "codigo"),
        "tipos": catalogar(tipos, "nome", "codigo"),
        "atributos_pokemon": catalogar(
            [a for a in atributos if a.escopo in ("pokemon", "ambos")], "nome", "codigo"
        ),
        "naturezas": catalogar(naturezas, "nome", "codigo"),
        "golpes": catalogar(golpes, "nome", "codigo"),
        "itens": catalogar(itens, "nome", "codigo"),
    }




def _especificacao_forma(nome: str, especificacoes: dict[str, Any],
                        catalogos: dict[str, Any]) -> dict[str, Any] | None:
    """Valida uma forma especial antes de permitir sua criação no catálogo."""
    if procurar(catalogos["formas"], nome) is not None:
        return None
    especificacao = especificacoes.get(nome)
    if not especificacao:
        return None
    if procurar(catalogos["especies"], especificacao["especie"]) is None:
        raise ValueError(f"{nome}: espécie base '{especificacao['especie']}' ausente/ambígua no catálogo.")
    if not especificacao.get("tipos") or len(especificacao["tipos"]) > 2:
        raise ValueError(f"{nome}: informe um ou dois tipos válidos.")
    tipos = [procurar(catalogos["tipos"], tipo) for tipo in especificacao["tipos"]]
    if any(tipo is None for tipo in tipos) or len({tipo.id for tipo in tipos}) != len(tipos):
        raise ValueError(f"{nome}: tipos não encontrados, duplicados ou ambíguos.")
    atributos = especificacao.get("atributos_base", {})
    obrigatorios = {"pv", "ataque", "defesa", "ataque_especial", "defesa_especial", "velocidade"}
    if set(atributos) != obrigatorios:
        raise ValueError(f"{nome}: os seis atributos base não estão completos.")
    for codigo, valor in atributos.items():
        if procurar(catalogos["atributos_pokemon"], codigo) is None:
            raise ValueError(f"{nome}: atributo Pokémon '{codigo}' ausente/ambíguo.")
        if Decimal(str(valor)) < 0:
            raise ValueError(f"{nome}: atributo '{codigo}' negativo.")
    return especificacao


def _preparar_formas_especiais(dados: dict[str, Any], seed: dict[str, Any],
                              catalogos: dict[str, Any], *, aplicar: bool) -> list[str]:
    """Cria a forma apenas durante a importação de quem a possui, na mesma transação.

    Na simulação, não grava nada; a forma normal Bulbasaur permanece intacta.
    """
    avisos = []
    especificacoes = seed.get("formas_personalizadas", {})
    presentes = {p["especie"] for setor in ("equipe", "box") for p in dados[setor]}
    for nome in presentes & especificacoes.keys():
        especificacao = _especificacao_forma(nome, especificacoes, catalogos)
        if especificacao is None:
            continue
        codigo = f"ficha-ankar-{slug(nome)}"
        conflito = db.session.scalar(select(FormaPokemon).where(FormaPokemon.codigo == codigo))
        if conflito is not None:
            raise ValueError(f"{nome}: código '{codigo}' já utilizado por outra forma.")
        if not aplicar:
            avisos.append(f"FORMA ESPECIAL: '{nome}' será cadastrada com atributos e imagens próprios ao aplicar.")
            continue
        especie = procurar(catalogos["especies"], especificacao["especie"])
        forma = FormaPokemon(
            especie_id=especie.id, codigo=codigo, nome=nome,
            categoria="personalizada", ativo=True,
            imagem_url=especificacao["imagem_url"],
            imagem_shiny_url=especificacao["imagem_shiny_url"],
            configuracoes={
                "origem": "ficha-ankar",
                "observacoes": especificacao.get("observacoes", ""),
                "dados_adicionais_originais": especificacao.get("dados_adicionais_originais", []),
            },
        )
        db.session.add(forma)
        db.session.flush()
        for indice, nome_tipo in enumerate(especificacao["tipos"], 1):
            tipo = procurar(catalogos["tipos"], nome_tipo)
            db.session.add(FormaPokemonTipo(
                forma_pokemon_id=forma.id, tipo_id=tipo.id, posicao=indice,
            ))
        for atributo_codigo, valor in especificacao["atributos_base"].items():
            atributo = procurar(catalogos["atributos_pokemon"], atributo_codigo)
            db.session.add(FormaPokemonAtributo(
                forma_pokemon_id=forma.id, atributo_id=atributo.id,
                valor_base=Decimal(str(valor)),
            ))
        catalogos["formas"].setdefault(normalizar(nome), []).append(forma)
        catalogos["formas"].setdefault(normalizar(codigo), []).append(forma)
        avisos.append(f"FORMA ESPECIAL: '{nome}' cadastrada para {dados['login']}.")
    return avisos


def _validar_registro(dados: dict[str, Any], catalogos: dict[str, Any],
                      formas_especiais: dict[str, Any] | None = None) -> list[str]:
    alertas = list(dados.get("avisos", []))
    especiais = formas_especiais or {}
    for localizacao in ("equipe", "box"):
        for pokemon in dados[localizacao]:
            forma = procurar(catalogos["formas"], pokemon["especie"])
            if forma is None and pokemon["especie"] not in especiais:
                alertas.append(
                    f"{localizacao}: espécie/forma sem correspondência exata: "
                    f"{pokemon['especie']} (será ignorado até revisão)."
                )
            if pokemon.get("natureza") and not procurar(catalogos["naturezas"], pokemon["natureza"]):
                alertas.append(f"{pokemon['especie']}: natureza não encontrada: {pokemon['natureza']}.")
            for golpe in pokemon.get("golpes", []):
                if not procurar(catalogos["golpes"], golpe):
                    alertas.append(f"{pokemon['especie']}: golpe não encontrado: {golpe}.")
    return alertas


def _item(nome: str, catalogos: dict[str, Any], criados: list[str], *, equipavel: bool = False) -> Item:
    item = procurar(catalogos["itens"], nome)
    if item is not None:
        return item
    # Um nome ainda não cadastrado vira item personalizado, sem efeitos
    # inventados. Não se altera a configuração de itens já cadastrados.
    codigo = f"importado-ficha-{slug(nome)}"[:140]
    item = Item(
        codigo=codigo,
        nome=nome.strip(),
        personalizado=True,
        equipavel=equipavel,
        consumivel=False,
        uso_em_batalha=False,
        ativo=True,
    )
    db.session.add(item)
    db.session.flush()
    catalogos["itens"].setdefault(normalizar(nome), []).append(item)
    criados.append(nome)
    return item


def _gravar_jogador(dados: dict[str, Any], campanha, catalogos: dict[str, Any],
                    senha: str, warnings: list[str], itens_novos: list[str]) -> tuple[int,int,int]:
    jogador = dados["personagem"]
    usuario = Usuario(
        nome=dados["nome_jogador"], login=dados["login"],
        perfil="jogador", senha_hash=gerar_hash_senha(senha), ativo=True,
    )
    proxima_posicao = int(db.session.execute(
        select(func.coalesce(func.max(Personagem.ordem_painel), 0) + 1)
        .where(Personagem.campanha_id == campanha.id, Personagem.ativo.is_(True))
    ).scalar_one())
    personagem = Personagem(
        usuario=usuario, campanha=campanha,
        nome=jogador["nome"], idade=jogador["idade"],
        origem=jogador["origem"], estilo_combate=jogador["estilo_combate"],
        classe=jogador["classe"], nivel=jogador["nivel"],
        numeros_shiny=jogador["numeros_shiny"],
        pokedolares=jogador["pokedolares"], pv_atual=jogador["pv_atual"],
        beneficios_habilidades=jogador["beneficios_habilidades"],
        ordem_painel=proxima_posicao, ativo=True,
    )
    db.session.add_all([usuario, personagem, CampanhaMembro(
        usuario=usuario, campanha=campanha, papel="jogador")])
    db.session.flush()
    for codigo, valor in jogador["atributos"].items():
        attr = procurar(catalogos["atributos"], codigo)
        if attr is None:
            warnings.append(f"Atributo sem correspondência: {codigo}.")
            continue
        db.session.add(PersonagemAtributo(
            personagem_id=personagem.id, atributo_id=attr.id, valor=Decimal(str(valor))))

    itens_agrupados: dict[str, int] = defaultdict(int)
    nome_item: dict[str, str] = {}
    for registro in dados["inventario"]:
        chave = normalizar(registro["nome"])
        itens_agrupados[chave] += int(registro["quantidade"])
        nome_item[chave] = registro["nome"]
    for chave, quantidade in itens_agrupados.items():
        item = _item(nome_item[chave], catalogos, itens_novos)
        db.session.add(PersonagemItem(
            personagem_id=personagem.id, item_id=item.id, quantidade=quantidade))

    contadores = {"equipe": 0, "box": 0}
    for localizacao in ("equipe", "box"):
        for registro in dados[localizacao]:
            forma = procurar(catalogos["formas"], registro["especie"])
            if forma is None:
                continue
            if contadores[localizacao] >= (6 if localizacao == "equipe" else 100):
                warnings.append(f"Limite de {localizacao} atingido; registro ignorado.")
                continue
            natureza = procurar(catalogos["naturezas"], registro.get("natureza", ""))
            item_carregado = None
            if registro.get("item"):
                item_carregado = _item(registro["item"], catalogos, itens_novos, equipavel=True)
                # Um item já existente não é modificado sem autorização.
                if not item_carregado.equipavel:
                    warnings.append(f"{registro['especie']}: item '{registro['item']}' não equipável no catálogo; não equipado.")
                    item_carregado = None
            pokemon = Pokemon(
                personagem_id=personagem.id,
                forma_pokemon_id=forma.id,
                apelido=registro.get("apelido"),
                genero=registro.get("genero") or None,
                shiny=bool(registro.get("shiny")),
                natureza_id=natureza.id if natureza else None,
                pv_atual=max(0, int(registro.get("pv_atual", 0))) if localizacao == "equipe" else 0,
                localizacao=localizacao,
                posicao=contadores[localizacao] + 1,
                item_equipado_id=item_carregado.id if item_carregado else None,
                ativo=True,
            )
            db.session.add(pokemon)
            db.session.flush()
            golpes_usados: set[Any] = set()
            for nome in registro.get("golpes", []):
                golpe = procurar(catalogos["golpes"], nome)
                if golpe is None or golpe.id in golpes_usados:
                    continue
                golpes_usados.add(golpe.id)
                if len(golpes_usados) > 4:
                    break
                db.session.add(PokemonGolpe(
                    pokemon_id=pokemon.id, golpe_id=golpe.id, posicao=len(golpes_usados)))
            contadores[localizacao] += 1
    return (contadores["equipe"], contadores["box"], len(itens_agrupados))


@planilhas_jogadores_cli.cli.group("jogadores-planilhas")
def grupo_planilhas() -> None:
    """Importar contas e fichas dos nove jogadores a partir das planilhas."""


@grupo_planilhas.command("importar")
@click.option("--aplicar", is_flag=True, help="Grava as fichas no PostgreSQL; sem isso apenas simula.")
@click.option("--login", "so_login", help="Processar somente um login (ex.: manu).")
def importar(aplicar: bool, so_login: str | None) -> None:
    seed = carregar_fichas()
    campanha = obter_campanha(str(current_app.config["CAMPANHA_PADRAO"]))
    if campanha is None:
        raise click.ClickException("Campanha não encontrada. Confira o .env e as migrations.")
    catalogos = _catalago_db()
    logins = {u.login.lower() for u in db.session.execute(select(Usuario)).scalars()}
    nomes = {n.lower() for n in db.session.execute(
        select(Personagem.nome).where(Personagem.campanha_id == campanha.id, Personagem.ativo.is_(True))
    ).scalars()}
    jogadores = seed["jogadores"]
    if so_login:
        jogadores = [j for j in jogadores if j["login"] == so_login.strip().lower()]
        if not jogadores:
            raise click.ClickException(f"Login não encontrado no pacote: {so_login}")
    if aplicar:
        click.echo("ATENÇÃO: a senha inicial solicitada é 12345. Troque as senhas antes de divulgar o link público!")
    click.echo(f"Campanha: {campanha.codigo} | Modo: {'APLICAR' if aplicar else 'SIMULAÇÃO (sem alterações)'}")
    criados = 0
    for dados in jogadores:
        rotulo = _rotulo(dados)
        if dados["login"].lower() in logins:
            click.echo(f"[PULAR] {rotulo}: login já existe; nenhum dado foi sobrescrito.")
            continue
        if dados["personagem"]["nome"].lower() in nomes:
            click.echo(f"[PULAR] {rotulo}: personagem com este nome já existe na campanha; revisão manual necessária.")
            continue
        try:
            avisos_formas = _preparar_formas_especiais(
                dados, seed, catalogos, aplicar=False,
            )
        except (ValueError, KeyError, TypeError) as erro:
            raise click.ClickException(f"Forma personalizada de {rotulo}: {erro}") from erro
        alertas = avisos_formas + _validar_registro(
            dados, catalogos, seed.get("formas_personalizadas", {}),
        )
        click.echo(f"[{'IMPORTAR' if aplicar else 'PREVER'}] {rotulo} — equipe: {len(dados['equipe'])}, Box: {len(dados['box'])}, itens: {len(dados['inventario'])}")
        for aviso in alertas:
            click.echo(f"    AVISO: {aviso}")
        if not aplicar:
            continue
        itens_novos: list[str] = []
        try:
            _preparar_formas_especiais(dados, seed, catalogos, aplicar=True)
            equipe, box, itens = _gravar_jogador(
                dados, campanha, catalogos, seed["senha_padrao"], alertas, itens_novos)
            db.session.commit()
        except Exception as erro:
            db.session.rollback()
            # Catálogo em memória não pode conservar itens criados pela transação revertida.
            catalogos = _catalago_db()
            raise click.ClickException(f"Falha ao importar {rotulo}; transação revertida: {erro}") from erro
        criados += 1
        logins.add(dados["login"].lower())
        nomes.add(dados["personagem"]["nome"].lower())
        click.echo(f"    OK: {equipe} equipe; {box} Box; {itens} itens; {len(itens_novos)} itens novos no catálogo.")
    if aplicar:
        click.echo(f"Importação finalizada: {criados} novo(s) jogador(es). Os existentes não foram alterados.")
    else:
        click.echo("SIMULAÇÃO CONCLUÍDA. Para gravar, repita com --aplicar.")
