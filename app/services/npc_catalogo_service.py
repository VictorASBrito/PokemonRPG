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


def _resolver_formas(tabelas):
    """Vincula nomes do Atlas ao catálogo vivo em uma única consulta."""
    nomes = {
        str(e.get("pokemon") or "").strip()
        for meta in tabelas for e in meta["tabela"].get("encontros", [])
        if e.get("pokemon") and not e.get("marcador")
    }
    formas = db.session.execute(
        select(FormaPokemon).where(FormaPokemon.ativo.is_(True))
    ).scalars().all()
    por_id = {str(f.id): f for f in formas}
    resultado = {}
    nao_resolvidas = []
    for nome in sorted(nomes):
        if nome.casefold() in ("x", "random"):
            continue
        opcoes = opcoes_formas(nome, formas)
        if len(opcoes) == 1 and opcoes[0]["id"] in por_id:
            resultado[nome] = por_id[opcoes[0]["id"]]
        else:
            nao_resolvidas.append(nome)
    return resultado, nao_resolvidas


def _montar_membro(forma, *, nivel, campanha, natureza, encontrador=None,
                   fonte=None):
    """Natureza, gênero e Shiny são sorteados uma única vez por membro."""
    shiny, numero_shiny = (sortear_shiny(encontrador.numeros_shiny)
                           if encontrador else (False, None))
    return {
        "forma_id": str(forma.id), "nome": forma.nome,
        "nome_atlas": (fonte or {}).get("pokemon") or forma.nome,
        "d100": (fonte or {}).get("d100"),
        "local_nome": (fonte or {}).get("local_nome", ""),
        "zona_nome": (fonte or {}).get("zona_nome", ""),
        "terreno": (fonte or {}).get("terreno", ""),
        "imagem": (forma.imagem_shiny_url if shiny else forma.imagem_url)
                  or forma.imagem_url or "",
        "nivel": nivel,
        "natureza_id": str(natureza.id) if natureza else None,
        "natureza": natureza.nome if natureza else "—",
        "genero": _genero_aleatorio(campanha.id),
        "shiny": bool(shiny), "sorteio_shiny": numero_shiny,
    }


def _naturais():
    return db.session.execute(
        select(Natureza).where(Natureza.ativo.is_(True))
        .order_by(func.lower(Natureza.nome))
    ).scalars().all()


def _sortear_um(rascunho, *, usados=None):
    if rascunho.get("modo") != "aleatorio":
        raise ValueError("A seleção manual não utiliza o sorteio aleatório.")
    from app.services.gerador_npcs_ankar import (
        tabelas_de_ankar, sortear_encontros_regionais,
    )
    tabelas = tabelas_de_ankar(
        local_id=rascunho["local_id"],
        zona_index=rascunho["zona_index"],
        tabela_index=rascunho["tabela_index"],
    )
    resolvidas, pendentes = _resolver_formas(tabelas)
    escolhidos, avisos = sortear_encontros_regionais(
        tabelas, 1, nomes_habilitados=set(resolvidas),
        permitir_repetidos=rascunho["permitir_repetidos"], usados=usados,
    )
    campanha = _campanha(rascunho["campanha_codigo"], bloquear=False)
    encontrador = (
        _validar_encontrador(campanha.id, rascunho["encontrador_id"])
        if rascunho["tipo"] == "horda" else None
    )
    naturezas = _naturais()
    membro = _montar_membro(
        resolvidas[escolhidos[0]["pokemon"]],
        nivel=rascunho["nivel"], campanha=campanha,
        natureza=random.choice(naturezas) if naturezas else None,
        encontrador=encontrador, fonte=escolhidos[0],
    )
    return membro, avisos, pendentes


def gerar_rascunho(*, campanha_codigo, nome, tipo, quantidade, nivel,
                   modo="aleatorio", local_id="", zona_index="", tabela_index="",
                   formas_manuais=None, encontrador_id=None, permitir_repetidos=False):
    from app.services.gerador_npcs_ankar import (
        tabelas_de_ankar, sortear_encontros_regionais,
    )
    tipo = str(tipo or "").strip().lower()
    if tipo not in TIPOS_GERADOR:
        raise ValueError("Escolha NPC fixo, NPC temporário ou horda.")
    modo = str(modo or "").strip().lower()
    if modo not in ("manual", "aleatorio"):
        raise ValueError("Escolha o modo Manual ou Aleatório.")
    nome = str(nome or "").strip()
    if not 1 <= len(nome) <= 120:
        raise ValueError("Informe o nome do NPC ou horda (até 120 caracteres).")
    qtd = _numero(quantidade, minimo=1, maximo=6, nome="Quantidade")
    nivel = _numero(nivel, minimo=1, maximo=100, nome="Nível")
    campanha = _campanha(campanha_codigo, bloquear=False)
    encontrador = (
        _validar_encontrador(campanha.id, encontrador_id)
        if tipo == "horda" else None
    )
    rascunho = {
        "campanha_codigo": campanha.codigo, "tipo": tipo, "nome": nome,
        "modo": modo, "nivel": nivel, "quantidade": qtd,
        "local_id": "", "local_nome": "Ankar — todas as localidades",
        "zona_index": "", "tabela_index": "", "zona_nome": "", "terreno": "",
        "encontrador_id": str(encontrador.id) if encontrador else None,
        "permitir_repetidos": bool(permitir_repetidos or tipo == "horda"),
        "pokemons": [], "avisos": {},
    }
    naturezas = _naturais()
    if modo == "manual":
        ids = list(formas_manuais or [])
        if len(ids) != qtd:
            raise ValueError(f"Escolha exatamente {qtd} Pokémon no modo Manual.")
        formas = [_forma(fid) for fid in ids]
        if not rascunho["permitir_repetidos"] and len({f.id for f in formas}) != qtd:
            raise ValueError("A equipe NPC não permite espécies repetidas; marque a opção para repetir.")
        rascunho["local_nome"] = "Seleção manual"
        for forma in formas:
            rascunho["pokemons"].append(_montar_membro(
                forma, nivel=nivel, campanha=campanha,
                natureza=random.choice(naturezas) if naturezas else None,
                encontrador=encontrador,
            ))
    else:
        tabelas = tabelas_de_ankar(
            local_id=local_id, zona_index=zona_index, tabela_index=tabela_index,
        )
        if local_id:
            rascunho["local_id"] = str(local_id)
            loc = tabelas[0]
            rascunho["local_nome"] = loc["local_nome"]
            if str(zona_index or "").strip():
                rascunho["zona_index"] = str(zona_index)
                rascunho["zona_nome"] = loc["zona_nome"]
            if str(tabela_index or "").strip():
                rascunho["tabela_index"] = str(tabela_index)
                rascunho["terreno"] = loc["terreno"]
        resolvidas, pendentes = _resolver_formas(tabelas)
        escolhas, avisos = sortear_encontros_regionais(
            tabelas, qtd, nomes_habilitados=set(resolvidas),
            permitir_repetidos=rascunho["permitir_repetidos"],
        )
        for escolha in escolhas:
            rascunho["pokemons"].append(_montar_membro(
                resolvidas[escolha["pokemon"]], nivel=nivel,
                campanha=campanha,
                natureza=random.choice(naturezas) if naturezas else None,
                encontrador=encontrador, fonte=escolha,
            ))
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
            modelo.nivel = rascunho["nivel"]
            modelo.equipe = rascunho["pokemons"]
            modelo.local_id, modelo.zona_nome, modelo.terreno = (
                rascunho["local_id"], rascunho["zona_nome"], rascunho["terreno"]
            )
            acao_historico = "atualizar_modelo"
        else:
            from app.services.npc_ficha_service import (
                atributos_iniciais, regras_npc, _pv_maximo_npc
            )
            regras_ficha = regras_npc(campanha.id)
            atributos = atributos_iniciais(regras_ficha)
            modelo = NPCModelo(
                campanha_id=campanha.id, nome=rascunho["nome"],
                nivel=rascunho["nivel"], atributos=atributos,
                pv_atual=_pv_maximo_npc(atributos, regras_ficha),
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
