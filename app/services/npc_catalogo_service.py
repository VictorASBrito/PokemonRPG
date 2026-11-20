"""Gerador de prévias, catálogo permanente e criação de grupos em campo.

Um NPC fixo é um MODELO. Ao usar no Campo cria-se uma cópia independente;
PV de batalha nunca modifica o modelo salvo. Rascunhos são guardados na
sessão autenticada, não em parâmetros ocultos arbitrários do formulário.
"""
from __future__ import annotations

import random
import uuid

from flask import session
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import (
    FormaPokemon, FormaPokemonAtributo, GrupoNPCEmCampo, HistoricoAlteracao,
    Natureza, NPCModelo, Personagem, PokemonNPCEmCampo, Usuario,
)
from app.services.ankar_formas_service import opcoes_formas
from app.services.campo_npc_service import (
    _campanha, _forma, _historico, _limites, _numero, _pv_maximo, _uuid,
)
from app.services.capturaveis_service import _genero_aleatorio, sortear_shiny
from app.services.gerador_npcs_ankar import selecionar_tabela, sortear_especies
from app.services.pokemon_db_service import carregar_regras_pokemon_db

CHAVE_RASCUNHO = "npc_ankar_rascunho"
TIPOS_GERADOR = ("fixo", "temporario", "horda")


def encontrados_campanha(campanha_id):
    personagens = db.session.execute(
        select(Personagem).join(Usuario, Usuario.id == Personagem.usuario_id)
        .where(Personagem.campanha_id == campanha_id, Personagem.ativo.is_(True),
               Usuario.ativo.is_(True), Usuario.perfil.in_(("jogador", "tester")))
        .order_by(func.lower(Personagem.nome))
    ).scalars().all()
    return [{"id": str(p.id), "nome": p.nome} for p in personagens]


def _validar_encontrador(campanha_id, identificador):
    uid = _uuid(identificador)
    if uid is None:
        raise ValueError("Selecione o treinador que encontrou a horda (para o sorteio Shiny).")
    personagem = db.session.execute(
        select(Personagem).join(Usuario, Usuario.id == Personagem.usuario_id)
        .where(Personagem.id == uid, Personagem.campanha_id == campanha_id,
               Personagem.ativo.is_(True), Usuario.ativo.is_(True),
               Usuario.perfil.in_(("jogador", "tester")))
    ).scalar_one_or_none()
    if personagem is None:
        raise ValueError("Treinador não pertence à campanha ativa.")
    return personagem


def _formas_disponiveis(tabela):
    nomes = {
        str(e.get("pokemon") or "").strip()
        for e in tabela.get("encontros", [])
        if e.get("pokemon") and not e.get("marcador")
    }
    formas = db.session.execute(
        select(FormaPokemon).where(FormaPokemon.ativo.is_(True))
    ).scalars().all()
    por_id = {str(f.id): f for f in formas}
    resolvidas = {}
    pendentes = []
    for nome in nomes:
        opcoes = opcoes_formas(nome, formas)
        if len(opcoes) == 1 and opcoes[0]["id"] in por_id:
            resolvidas[nome] = por_id[opcoes[0]["id"]]
        elif nome.casefold() not in ("x", "random"):
            pendentes.append(nome)
    return resolvidas, sorted(pendentes)


def _sortear_um(rascunho, *, usados=None):
    _, _, tabela = selecionar_tabela(
        rascunho["local_id"], rascunho["zona_index"], rascunho["tabela_index"]
    )
    resolvidas, pendentes = _formas_disponiveis(tabela)
    nomes_permitidos = set(resolvidas)
    if usados:
        nomes_permitidos.difference_update(usados)
    escolhas, avisos = sortear_especies(
        tabela, 1, nomes_habilitados=nomes_permitidos,
        permitir_repetidos=True,
    )
    escolha = escolhas[0]
    forma = resolvidas[escolha["pokemon"]]
    nivel = random.randint(rascunho["nivel_min"], rascunho["nivel_max"])
    natureza = db.session.execute(
        select(Natureza).where(Natureza.ativo.is_(True))
        .order_by(func.lower(Natureza.nome))
    ).scalars().all()
    natureza_aleatoria = random.choice(natureza) if natureza else None
    campanha = _campanha(rascunho["campanha_codigo"], bloquear=False)
    shiny = False
    numero_shiny = None
    if rascunho["tipo"] == "horda":
        encontrador = _validar_encontrador(campanha.id, rascunho["encontrador_id"])
        shiny, numero_shiny = sortear_shiny(encontrador.numeros_shiny)
    return {
        "forma_id": str(forma.id),
        "nome": forma.nome,
        "nome_atlas": escolha["pokemon"],
        "imagem": (forma.imagem_shiny_url if shiny else forma.imagem_url) or forma.imagem_url or "",
        "nivel": nivel, "natureza_id": str(natureza_aleatoria.id) if natureza_aleatoria else None,
        "natureza": natureza_aleatoria.nome if natureza_aleatoria else "—",
        "genero": _genero_aleatorio(campanha.id),
        "shiny": bool(shiny), "sorteio_shiny": numero_shiny,
        "d100": escolha["d100"],
    }, avisos, pendentes


def gerar_rascunho(*, campanha_codigo, nome, tipo, local_id, zona_index, tabela_index,
                   quantidade, nivel_min, nivel_max, encontrador_id=None,
                   permitir_repetidos=False):
    tipo = str(tipo or "").strip().lower()
    if tipo not in TIPOS_GERADOR:
        raise ValueError("Escolha NPC fixo, NPC temporário ou horda.")
    nome = str(nome or "").strip()
    if not 1 <= len(nome) <= 120:
        raise ValueError("Informe o nome do encontro (até 120 caracteres).")
    quantidade = _numero(quantidade, minimo=1, maximo=6, nome="Quantidade")
    nivel_min = _numero(nivel_min, minimo=1, maximo=100, nome="Nível mínimo")
    nivel_max = _numero(nivel_max, minimo=1, maximo=100, nome="Nível máximo")
    if nivel_min > nivel_max:
        raise ValueError("O nível mínimo não pode superar o máximo.")
    campanha = _campanha(campanha_codigo, bloquear=False)
    local, zona, tabela = selecionar_tabela(local_id, zona_index, tabela_index)
    encontrador = None
    if tipo == "horda":
        encontrador = _validar_encontrador(campanha.id, encontrador_id)
    rascunho = {
        "campanha_codigo": campanha.codigo, "tipo": tipo, "nome": nome,
        "local_id": local["id"], "local_nome": local["nome"],
        "zona_index": int(zona_index), "tabela_index": int(tabela_index),
        "zona_nome": str(zona["nome"])[:120],
        "terreno": str(tabela.get("terreno") or "")[:120],
        "quantidade": quantidade, "nivel_min": nivel_min, "nivel_max": nivel_max,
        "encontrador_id": str(encontrador.id) if encontrador else None,
        "permitir_repetidos": bool(permitir_repetidos or tipo == "horda"),
        "pokemons": [], "avisos": {},
    }
    # Pré-análise não deve começar o sorteio se há poucos Pokémon distintos.
    resolvidas, pendentes = _formas_disponiveis(tabela)
    sorteados, avisos = sortear_especies(
        tabela, quantidade, nomes_habilitados=set(resolvidas),
        permitir_repetidos=rascunho["permitir_repetidos"],
    )
    # Mesmo gerador de atributos para cada membro, mas preserva a rolagem d100.
    for escolhido in sorteados:
        # Sortear atributos sem re-sortear a espécie/rolagem.
        forma = resolvidas[escolhido["pokemon"]]
        nivel = random.randint(nivel_min, nivel_max)
        naturezas = db.session.execute(
            select(Natureza).where(Natureza.ativo.is_(True))
            .order_by(func.lower(Natureza.nome))
        ).scalars().all()
        natureza = random.choice(naturezas) if naturezas else None
        shiny, numero_shiny = (sortear_shiny(encontrador.numeros_shiny)
                               if encontrador else (False, None))
        rascunho["pokemons"].append({
            "forma_id": str(forma.id), "nome": forma.nome,
            "nome_atlas": escolhido["pokemon"], "d100": escolhido["d100"],
            "imagem": (forma.imagem_shiny_url if shiny else forma.imagem_url) or forma.imagem_url or "",
            "nivel": nivel, "natureza_id": str(natureza.id) if natureza else None,
            "natureza": natureza.nome if natureza else "—",
            "genero": _genero_aleatorio(campanha.id),
            "shiny": bool(shiny), "sorteio_shiny": numero_shiny,
        })
    rascunho["avisos"] = {
        **avisos, "nomes_sem_forma_unica": pendentes[:15],
        "total_sem_forma_unica": len(pendentes),
    }
    session[CHAVE_RASCUNHO] = rascunho
    session.modified = True
    return rascunho


def refazer_pokemon_rascunho(*, campanha_codigo, indice):
    rascunho = rascunho_atual(campanha_codigo)
    idx = _numero(indice, minimo=0, maximo=len(rascunho["pokemons"]) - 1, nome="Integrante")
    usados = ({x["nome_atlas"] for i, x in enumerate(rascunho["pokemons"]) if i != idx}
              if not rascunho["permitir_repetidos"] else None)
    novo, avisos, _ = _sortear_um(rascunho, usados=usados)
    rascunho["pokemons"][idx] = novo
    rascunho["avisos"]["ultimo_novo_sorteio"] = avisos
    session[CHAVE_RASCUNHO] = rascunho
    session.modified = True
    return rascunho


def rascunho_atual(campanha_codigo):
    rascunho = session.get(CHAVE_RASCUNHO)
    if not isinstance(rascunho, dict) or rascunho.get("campanha_codigo") != campanha_codigo:
        raise ValueError("Prévia não encontrada ou pertencente a outra campanha. Gere novamente.")
    if not 1 <= len(rascunho.get("pokemons", [])) <= 6:
        raise ValueError("Prévia inválida; gere a equipe novamente.")
    return rascunho


def modelos_campanha(*, campanha_codigo):
    campanha = _campanha(campanha_codigo, bloquear=False)
    modelos = db.session.execute(
        select(NPCModelo).where(NPCModelo.campanha_id == campanha.id, NPCModelo.ativo.is_(True))
        .order_by(func.lower(NPCModelo.nome))
    ).scalars().all()
    return [{
        "id": str(m.id), "nome": m.nome, "local_id": m.local_id,
        "zona_nome": m.zona_nome, "terreno": m.terreno,
        "equipe": m.equipe, "quantidade": len(m.equipe),
    } for m in modelos]


def _modelo(campanha_id, modelo_id):
    uid = _uuid(modelo_id)
    if uid is None:
        raise ValueError("NPC fixo inválido.")
    modelo = db.session.execute(
        select(NPCModelo).where(NPCModelo.id == uid, NPCModelo.campanha_id == campanha_id,
                                NPCModelo.ativo.is_(True))
    ).scalar_one_or_none()
    if modelo is None:
        raise ValueError("NPC não encontrado no catálogo desta campanha.")
    return modelo


def _colocar_no_campo(campanha, equipe, *, nome, tipo, time_numero,
                     local_id, zona_nome, terreno, usuario_id, encontrador_id=None, modelo_id=None):
    time = _numero(time_numero, minimo=1, maximo=16, nome="Time")
    if not 1 <= len(equipe) <= 6:
        raise ValueError("A equipe precisa ter de 1 a 6 Pokémon.")
    _limites(campanha.id, novos_grupos=1, novos_pokemons=len(equipe))
    grupo = GrupoNPCEmCampo(
        campanha_id=campanha.id, nome=nome, tipo=tipo, time_numero=time,
        modelo_id=modelo_id, encontrado_por_personagem_id=_uuid(encontrador_id),
        local_id=local_id, zona_nome=zona_nome, terreno=terreno,
    )
    db.session.add(grupo)
    db.session.flush()
    regras = carregar_regras_pokemon_db(campanha.id)
    for item in equipe:
        forma = _forma(item["forma_id"])   # Verifica forma ativa ao instanciar modelo.
        nivel = _numero(item["nivel"], minimo=1, maximo=100, nome="Nível")
        db.session.add(PokemonNPCEmCampo(
            grupo_id=grupo.id, forma_pokemon_id=forma.id, nivel=nivel,
            pv_maximo=_pv_maximo(forma, nivel, regras),
            pv_atual=_pv_maximo(forma, nivel, regras),
            shiny=bool(item.get("shiny", False)),
            natureza_id=_uuid(item.get("natureza_id")),
            genero=item.get("genero"),
        ))
    _historico(usuario_id, grupo.id, "criar_regional", depois={
        "nome": nome, "tipo": tipo, "time": time, "local_id": local_id,
        "zona": zona_nome, "terreno": terreno, "quantidade": len(equipe),
        "modelo_id": str(modelo_id) if modelo_id else None,
    })
    db.session.commit()
    return f"{nome}: {len(equipe)} Pokémon adicionados ao Time {time}."


def aplicar_rascunho(*, campanha_codigo, acao, time_numero=None,
                     usuario_id=None, modelo_id=None):
    rascunho = rascunho_atual(campanha_codigo)
    campanha = _campanha(campanha_codigo)
    if acao in ("salvar_fixo", "atualizar_fixo"):
        if rascunho["tipo"] != "fixo":
            raise ValueError("Somente NPCs fixos podem ser salvos no catálogo.")
        if acao == "atualizar_fixo":
            modelo = _modelo(campanha.id, modelo_id)
            modelo.nome = rascunho["nome"]
            modelo.equipe = rascunho["pokemons"]
            modelo.local_id, modelo.zona_nome, modelo.terreno = (
                rascunho["local_id"], rascunho["zona_nome"], rascunho["terreno"]
            )
            acao_historico = "atualizar_modelo"
        else:
            modelo = NPCModelo(
                campanha_id=campanha.id, nome=rascunho["nome"],
                local_id=rascunho["local_id"], zona_nome=rascunho["zona_nome"],
                terreno=rascunho["terreno"], equipe=rascunho["pokemons"],
                ativo=True,
            )
            db.session.add(modelo)
            acao_historico = "salvar_modelo"
        db.session.flush()
        _historico(usuario_id, modelo.id, acao_historico,
                   depois={"nome": modelo.nome, "quantidade": len(modelo.equipe)})
        db.session.commit()
        resultado = "NPC fixo salvo no catálogo."
    elif acao == "colocar_campo":
        if rascunho["tipo"] == "fixo":
            raise ValueError("Salve o NPC fixo no catálogo antes de colocá-lo em campo.")
        resultado = _colocar_no_campo(
            campanha, rascunho["pokemons"], nome=rascunho["nome"],
            tipo="horda" if rascunho["tipo"] == "horda" else "npc",
            time_numero=time_numero, local_id=rascunho["local_id"],
            zona_nome=rascunho["zona_nome"], terreno=rascunho["terreno"],
            usuario_id=usuario_id, encontrador_id=rascunho["encontrador_id"],
        )
    else:
        raise ValueError("Operação de geração inválida.")
    session.pop(CHAVE_RASCUNHO, None)
    return resultado


def colocar_modelo(*, campanha_codigo, modelo_id, time_numero, usuario_id):
    campanha = _campanha(campanha_codigo)
    modelo = _modelo(campanha.id, modelo_id)
    return _colocar_no_campo(
        campanha, modelo.equipe, nome=modelo.nome, tipo="npc",
        time_numero=time_numero, local_id=modelo.local_id,
        zona_nome=modelo.zona_nome, terreno=modelo.terreno,
        usuario_id=usuario_id, modelo_id=modelo.id,
    )


def arquivar_modelo(*, campanha_codigo, modelo_id, usuario_id):
    campanha = _campanha(campanha_codigo)
    modelo = _modelo(campanha.id, modelo_id)
    modelo.ativo = False
    _historico(usuario_id, modelo.id, "arquivar_modelo", antes={"nome": modelo.nome})
    db.session.commit()
    return f"{modelo.nome} arquivado do catálogo (instâncias ativas preservadas)."
