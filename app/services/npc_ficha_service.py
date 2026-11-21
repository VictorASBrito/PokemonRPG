"""Ficha permanente de NPC, com regras de personagem e equipe próprias.

NPCModelo não é Usuario/Personagem: não recebe login, inventário, Box ou
permissões. Atributos e PV seguem a configuração vigente da campanha.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.db import FormaPokemon, FormaPokemonTipo, Golpe, Natureza, NaturezaModificador, NPCModelo
from app.services.campo_npc_service import _campanha, _forma, _historico, _numero, _pv_maximo, _uuid
from app.services.personagem_service import carregar_regras_personagem
from app.services.pokemon_db_service import carregar_regras_pokemon_db
from app.services.calculo_atributos import calcular_progressao, aplicar_aumento, aplicar_diminuicao
from app.services.transformacoes_service import listar_formas_por_base


def regras_npc(campanha_id):
    return carregar_regras_personagem(campanha_id)


def atributos_iniciais(regras):
    return {
        str(item["id"]): int(item.get("valor_inicial", item.get("minimo", 1)))
        for item in regras.get("atributos", [])
    }


def atributos_efetivos(modelo, regras):
    valores = atributos_iniciais(regras)
    if isinstance(modelo.atributos, dict):
        for chave, valor in modelo.atributos.items():
            if chave in valores:
                try:
                    valores[chave] = int(valor)
                except (TypeError, ValueError):
                    continue
    return valores


def _pv_maximo_npc(atributos, regras):
    return max(0, int(atributos.get("saude", 1)) *
               int(regras.get("pv_por_ponto_saude", 10)))


def _nivel(modelo):
    if modelo.nivel is not None:
        return int(modelo.nivel)
    equipe = modelo.equipe if isinstance(modelo.equipe, list) else []
    if equipe:
        try:
            return int(equipe[0].get("nivel", 1))
        except (ValueError, TypeError, AttributeError):
            pass
    return 1


def _imagem(url):
    valor = str(url or "").strip()
    if not valor:
        return None
    if len(valor) > 500 or not (
        valor.startswith("https://") or valor.startswith("http://")
        or valor.startswith("/static/")
    ):
        raise ValueError("A imagem deve usar uma URL HTTP(S) ou um caminho /static/ válido.")
    return valor


def _texto(dados, campo, *, limite, obrigatorio=False):
    valor = str(dados.get(campo) or "").strip()
    if obrigatorio and not valor:
        raise ValueError(f"O campo {campo} é obrigatório.")
    if len(valor) > limite:
        raise ValueError(f"O campo {campo} aceita até {limite} caracteres.")
    return valor


def _dados_entrada(formulario, regras):
    nome = _texto(formulario, "nome", limite=120, obrigatorio=True)
    classe = _texto(formulario, "classe", limite=160)
    origem = _texto(formulario, "origem", limite=160)
    foto = _imagem(formulario.get("foto_url"))
    notas = _texto(formulario, "anotacoes", limite=10000)
    nivel = _numero(formulario.get("nivel"), minimo=1, maximo=100, nome="Nível")
    atributos = {}
    for item in regras.get("atributos", []):
        codigo = str(item["id"])
        minimo = int(item.get("minimo", 1))
        maximo = int(item.get("maximo", 6))
        valor = _numero(formulario.get(f"atributo_{codigo}", item.get("valor_inicial", minimo)),
                        minimo=minimo, maximo=maximo, nome=item["nome"])
        atributos[codigo] = valor
    return dict(nome=nome, classe=classe, origem=origem, foto_url=foto,
                anotacoes=notas, nivel=nivel, atributos=atributos)


def _consulta_modelos(campanha_id):
    return db.session.execute(
        select(NPCModelo)
        .where(NPCModelo.campanha_id == campanha_id, NPCModelo.ativo.is_(True))
        .order_by(func.lower(NPCModelo.nome), NPCModelo.id)
    ).scalars().all()


def _modelo(campanha_id, identificador):
    uid = _uuid(identificador)
    if uid is None:
        raise ValueError("NPC inválido.")
    modelo = db.session.scalar(
        select(NPCModelo)
        .where(NPCModelo.id == uid,
               NPCModelo.campanha_id == campanha_id,
               NPCModelo.ativo.is_(True))
    )
    if modelo is None:
        raise ValueError("NPC não encontrado na campanha.")
    return modelo


def dados_ficha_npc(*, campanha_codigo, modelo_id=None):
    campanha = _campanha(campanha_codigo, bloquear=False)
    regras = regras_npc(campanha.id)
    modelo = _modelo(campanha.id, modelo_id) if modelo_id else None
    valores = atributos_efetivos(modelo, regras) if modelo else atributos_iniciais(regras)
    return {
        "modelo": modelo, "regras": regras, "valores": valores,
        "nivel": _nivel(modelo) if modelo else int(regras.get("nivel_inicial", 1)),
        "pv_atual": (
            modelo.pv_atual if modelo and modelo.pv_atual is not None
            else _pv_maximo_npc(valores, regras)
        ),
    }


def salvar_ficha_npc(*, campanha_codigo, modelo_id, dados, usuario_id):
    campanha = _campanha(campanha_codigo)
    regras = regras_npc(campanha.id)
    atualizado = _dados_entrada(dados, regras)
    modelo = _modelo(campanha.id, modelo_id) if modelo_id else None
    antes = {"nome": modelo.nome, "nivel": _nivel(modelo)} if modelo else None
    if modelo is None:
        modelo = NPCModelo(
            campanha_id=campanha.id,
            nome=atualizado["nome"], nivel=atualizado["nivel"],
            equipe=[], local_id="", zona_nome="", terreno="", ativo=True,
        )
        db.session.add(modelo)
    valores_anteriores = atributos_efetivos(modelo, regras)
    pv_anterior = (
        modelo.pv_atual if modelo.pv_atual is not None
        else _pv_maximo_npc(valores_anteriores, regras)
    )
    for chave, valor in atualizado.items():
        setattr(modelo, chave, valor)
    nivel = atualizado["nivel"]
    # Modelo tem nível único; editar nível propaga para toda a equipe salva.
    if modelo.equipe:
        modelo.equipe = [dict(membro, nivel=nivel) for membro in modelo.equipe]
    pv_max = _pv_maximo_npc(atualizado["atributos"], regras)
    modelo.pv_atual = max(-9999, min(int(pv_anterior), pv_max)) if antes else pv_max
    db.session.flush()
    _historico(usuario_id, modelo.id, "atualizar_ficha" if antes else "criar_ficha",
               antes=antes, depois={"nome": modelo.nome, "nivel": nivel,
                                    "classe": modelo.classe,
                                    "atributos": atualizado["atributos"]})
    db.session.commit()
    return str(modelo.id)


def _formas_do_catalogo(ids):
    from app.models.db import FormaPokemonAtributo
    return {
        str(forma.id): forma for forma in db.session.execute(
            select(FormaPokemon).where(FormaPokemon.id.in_(ids))
            .options(
                selectinload(FormaPokemon.tipos).selectinload(FormaPokemonTipo.tipo),
                selectinload(FormaPokemon.atributos_base).selectinload(FormaPokemonAtributo.atributo),
            )
        ).scalars()
    }


def _cartoes_modelos(campanha, modelos, *, incluir_acoes=False):
    regras = regras_npc(campanha.id)
    regras_pokemon = carregar_regras_pokemon_db(campanha.id)
    equipe_ids, natureza_ids, golpe_ids = set(), set(), set()
    for modelo in modelos:
        for membro in (modelo.equipe or []):
            if not isinstance(membro, dict):
                continue
            uid = _uuid(membro.get("forma_id"))
            if uid:
                equipe_ids.add(uid)
            overlay = _uuid(membro.get("forma_temporaria_id"))
            if overlay and membro.get("tipo_transformacao") in ("mega", "alternativa"):
                equipe_ids.add(overlay)
            natureza = _uuid(membro.get("natureza_id"))
            if natureza:
                natureza_ids.add(natureza)
            for golpe_id in membro.get("golpes", []) if isinstance(membro.get("golpes"), list) else []:
                golpe = _uuid(golpe_id)
                if golpe:
                    golpe_ids.add(golpe)
    formas = _formas_do_catalogo(equipe_ids) if equipe_ids else {}
    naturezas = {
        str(item.id): item for item in db.session.scalars(
            select(Natureza).where(Natureza.id.in_(natureza_ids))
            .options(selectinload(Natureza.modificadores).selectinload(NaturezaModificador.atributo))
        )
    } if natureza_ids else {}
    golpes_catalogo = {
        str(item.id): item for item in db.session.scalars(
            select(Golpe).where(Golpe.id.in_(golpe_ids))
            .options(selectinload(Golpe.tipo), selectinload(Golpe.categoria))
        )
    } if golpe_ids else {}
    cartoes = []
    for modelo in modelos:
        # Uma única Mega ativa por treinador NPC, independente da tela Campo.
        mega_ativa = any(
            isinstance(membro, dict) and membro.get("tipo_transformacao") == "mega"
            and membro.get("forma_temporaria_id")
            for membro in (modelo.equipe or [])
        )
        valores = atributos_efetivos(modelo, regras)
        pv_max = _pv_maximo_npc(valores, regras)
        equipe = []
        for indice_real, item in enumerate(modelo.equipe or []):
            forma = formas.get(str(item.get("forma_id"))) if isinstance(item, dict) else None
            if forma is None:
                continue
            # A forma base nunca é sobrescrita; a transformação é um overlay JSON.
            overlay = formas.get(str(item.get("forma_temporaria_id")))
            tipo_atual = item.get("tipo_transformacao")
            if not (
                overlay and overlay.ativo and overlay.especie_id == forma.especie_id
                and ((tipo_atual == "mega" and overlay.categoria == "mega")
                     or (tipo_atual == "alternativa" and overlay.categoria != "mega"))
            ):
                overlay, tipo_atual = None, None
            visivel = overlay or forma
            nivel_pokemon = _nivel(modelo)
            maximo = _pv_maximo(visivel, nivel_pokemon, regras_pokemon)
            atual = item.get("pv_atual")
            atual = maximo if atual is None else max(-9999, min(int(atual), maximo))
            bases = {
                atributo.atributo.codigo.replace("-", "_"): int(atributo.valor_base)
                for atributo in visivel.atributos_base if atributo.atributo and atributo.atributo.ativo
            }
            totais = {
                codigo: calcular_progressao(
                    base, nivel_pokemon,
                    regras_pokemon.get("progressao_pv" if codigo == "pv" else "progressao_atributos", []),
                )
                for codigo, base in bases.items()
            }
            if item.get("shiny"):
                for codigo, bonus in (regras_pokemon.get("bonus_shiny") or {}).items():
                    chave = codigo.replace("-", "_")
                    if chave in bases:
                        bases[chave] += int(bonus)
                        totais[chave] = calcular_progressao(
                            bases[chave], nivel_pokemon,
                            regras_pokemon.get("progressao_pv" if chave == "pv" else "progressao_atributos", []),
                        )
            natureza = naturezas.get(str(item.get("natureza_id")))
            if natureza:
                for modificador in natureza.modificadores:
                    if not modificador.atributo:
                        continue
                    codigo = modificador.atributo.codigo.replace("-", "_")
                    if codigo not in totais:
                        continue
                    valor = float(modificador.valor)
                    if modificador.tipo_modificador == "percentual":
                        totais[codigo] = (
                            aplicar_aumento(totais[codigo], valor) if valor >= 0
                            else aplicar_diminuicao(totais[codigo], -valor)
                        )
                    else:
                        totais[codigo] = max(0, totais[codigo] + int(valor))
            golpe_ids_membro = item.get("golpes") if isinstance(item.get("golpes"), list) else []
            golpes = []
            for golpe_id in golpe_ids_membro[:4]:
                golpe = golpes_catalogo.get(str(golpe_id))
                if golpe and golpe.ativo:
                    golpes.append({
                        "id": str(golpe.id), "nome": golpe.nome,
                        "tipo": golpe.tipo.nome if golpe.tipo else "—",
                        "categoria": golpe.categoria.nome if golpe.categoria else "—",
                        "dano": golpe.expressao_dano or "Estado",
                        "precisao": str(golpe.precisao) if golpe.precisao is not None else "—",
                    })
            acoes = {"alternativas": [], "megas": [], "pode_reverter": bool(overlay),
                     "tipo": tipo_atual, "pode_transformar": atual > 0,
                     "outra_mega_ativa": mega_ativa and tipo_atual != "mega"}
            if incluir_acoes:
                permissoes = listar_formas_por_base(forma, atual=overlay, tipo=tipo_atual)
                def _opcao(destino):
                    return {
                        "id": str(destino.id), "nome": destino.nome,
                        "imagem": (
                            (destino.imagem_shiny_url if item.get("shiny") else destino.imagem_url)
                            or destino.imagem_url or ""
                        ),
                    }
                acoes["alternativas"] = [_opcao(destino) for destino in permissoes["alternativas"]]
                acoes["megas"] = [_opcao(destino) for destino in permissoes["mega"]]
            equipe.append({
                "id": str(forma.id), "forma_id": str(forma.id),
                "nome": (visivel.nome if item.get("nome") == forma.nome else item.get("nome")) or visivel.nome,
                "especie": visivel.nome, "imagem": (
                    (visivel.imagem_shiny_url if item.get("shiny") else visivel.imagem_url)
                    or visivel.imagem_url or ""
                ),
                "forma_original": forma.nome, "tipo_transformacao": tipo_atual,
                "forma_temporaria_id": str(overlay.id) if overlay else None,
                "acoes": acoes,
                "shiny": bool(item.get("shiny")),
                "nivel": nivel_pokemon, "pv_atual": atual, "pv_maximo": maximo,
                "tipos": [
                    rel.tipo.nome for rel in sorted(visivel.tipos, key=lambda t: t.posicao)
                    if rel.tipo and rel.tipo.ativo
                ],
                "indice": indice_real, "natureza": natureza.nome if natureza else item.get("natureza") or "Não definida",
                "natureza_id": str(natureza.id) if natureza else "",
                "genero": item.get("genero") or "Ø", "bases": bases, "totais": totais,
                "golpes": golpes, "golpe_ids": [g["id"] for g in golpes],
                "dados_defesa": f"{(totais.get('velocidade', 0) + 9) // 10}d6",
            })
        cartoes.append({
            "id": str(modelo.id), "nome": modelo.nome, "nivel": _nivel(modelo),
            "classe": modelo.classe or "", "origem": modelo.origem or "",
            "foto_url": modelo.foto_url or "", "anotacoes": modelo.anotacoes or "",
            "local_id": modelo.local_id or "", "zona_nome": modelo.zona_nome or "",
            "terreno": modelo.terreno or "", "quantidade": len(equipe),
            "atributos": [
                {"codigo": item["id"], "nome": item["nome"],
                 "valor": valores.get(item["id"], 1)}
                for item in regras.get("atributos", [])
            ],
            "pv_atual": (
                int(modelo.pv_atual) if modelo.pv_atual is not None else pv_max
            ), "pv_maximo": pv_max, "equipe": equipe,
            "alertas": (["Treinador com PV baixo"] if (
                pv_max > 0 and (modelo.pv_atual if modelo.pv_atual is not None else pv_max)
                <= max(1, pv_max // 4)
            ) else []),
        })
    return cartoes


def cards_catalogo_npc(*, campanha_codigo):
    campanha = _campanha(campanha_codigo, bloquear=False)
    return _cartoes_modelos(campanha, _consulta_modelos(campanha.id))


def ficha_card_npc(*, campanha_codigo, modelo_id):
    campanha = _campanha(campanha_codigo, bloquear=False)
    return _cartoes_modelos(campanha, [_modelo(campanha.id, modelo_id)], incluir_acoes=True)[0]


def adicionar_pokemon_ficha(*, campanha_codigo, modelo_id, forma_id, usuario_id):
    from app.services.npc_catalogo_service import _montar_membro
    campanha = _campanha(campanha_codigo)
    modelo = _modelo(campanha.id, modelo_id)
    equipe = list(modelo.equipe or [])
    if len(equipe) >= 6:
        raise ValueError("A equipe do NPC já possui seis Pokémon.")
    forma = _forma(forma_id)
    nivel = _nivel(modelo)
    membro = _montar_membro(forma, nivel=nivel, campanha=campanha, natureza=None)
    membro["pv_atual"] = _pv_maximo(
        forma, nivel, carregar_regras_pokemon_db(campanha.id)
    )
    equipe.append(membro)
    modelo.equipe = equipe
    _historico(usuario_id, modelo.id, "adicionar_pokemon_ficha",
               depois={"forma": str(forma.id), "nivel": nivel})
    db.session.commit()
    return "Pokémon adicionado à equipe do NPC."


def remover_pokemon_ficha(*, campanha_codigo, modelo_id, indice, usuario_id):
    campanha = _campanha(campanha_codigo)
    modelo = _modelo(campanha.id, modelo_id)
    equipe = list(modelo.equipe or [])
    indice = _numero(indice, minimo=0, maximo=max(0, len(equipe) - 1), nome="Posição")
    if not equipe or indice >= len(equipe):
        raise ValueError("Pokémon não encontrado nesta equipe.")
    removido = equipe.pop(indice)
    modelo.equipe = equipe
    _historico(usuario_id, modelo.id, "remover_pokemon_ficha",
               antes={"forma_id": removido.get("forma_id"), "posicao": indice})
    db.session.commit()
    return "Pokémon retirado da equipe do NPC."


def ajustar_pv_npc(*, campanha_codigo, modelo_id, delta, usuario_id,
                   pokemon_indice=None):
    delta = int(delta)
    if not -9999 <= delta <= 9999 or not delta:
        raise ValueError("Ajuste de PV inválido.")
    campanha = _campanha(campanha_codigo)
    modelo = _modelo(campanha.id, modelo_id)
    regras = regras_npc(campanha.id)
    if pokemon_indice is None:
        maximo = _pv_maximo_npc(atributos_efetivos(modelo, regras), regras)
        atual = modelo.pv_atual if modelo.pv_atual is not None else maximo
        novo = max(-9999, min(maximo, atual + delta))
        modelo.pv_atual = novo
    else:
        equipe = list(modelo.equipe or [])
        idx = _numero(pokemon_indice, minimo=0, maximo=max(0, len(equipe) - 1), nome="Posição")
        if not equipe or idx >= len(equipe):
            raise ValueError("Pokémon não pertence à equipe deste NPC.")
        item = dict(equipe[idx])
        forma = _forma(item.get("forma_id"))
        maximo = _pv_maximo(forma, _nivel(modelo), carregar_regras_pokemon_db(campanha.id))
        atual = int(item.get("pv_atual")) if item.get("pv_atual") is not None else maximo
        novo = max(-9999, min(maximo, atual + delta))
        item["pv_atual"] = novo
        equipe[idx] = item
        modelo.equipe = equipe
    _historico(usuario_id, modelo.id, "ajustar_pv_npc",
               antes={"pv": atual, "pokemon_indice": pokemon_indice},
               depois={"pv": novo, "pokemon_indice": pokemon_indice})
    db.session.commit()
    return novo, maximo


def opcoes_edicao_npc(*, campanha_codigo):
    """Listas pequenas para o mestre; o catálogo de golpes usa autocomplete."""
    campanha = _campanha(campanha_codigo, bloquear=False)
    naturezas = db.session.scalars(
        select(Natureza).where(Natureza.ativo.is_(True)).order_by(Natureza.nome)
    ).all()
    regras = carregar_regras_pokemon_db(campanha.id)
    return {
        "naturezas": [{"id": str(item.id), "nome": item.nome} for item in naturezas],
        "generos": list(regras.get("generos") or ["Ø", "♂", "♀"]),
    }


def editar_pokemon_ficha(*, campanha_codigo, modelo_id, indice, dados, usuario_id):
    """Edita o integrante salvo no NPC; nunca altera Pokémon dos jogadores."""
    campanha = _campanha(campanha_codigo)
    modelo = _modelo(campanha.id, modelo_id)
    equipe = list(modelo.equipe or [])
    idx = _numero(indice, minimo=0, maximo=5, nome="Posição")
    if idx >= len(equipe):
        raise ValueError("Pokémon não encontrado nesta equipe.")
    anterior = dict(equipe[idx])
    item = dict(anterior)
    forma_antiga = _forma(item.get("forma_id"))
    forma = _forma(dados.get("forma_id") or item["forma_id"])
    if forma.categoria == "mega":
        raise ValueError("A Mega Evolução é temporária; selecione a forma base do Pokémon.")
    nome = str(dados.get("nome") or "").strip()
    if len(nome) > 160:
        raise ValueError("O apelido aceita até 160 caracteres.")
    nid = str(dados.get("natureza_id") or "").strip()
    if nid:
        uid = _uuid(nid)
        natureza = db.session.get(Natureza, uid) if uid else None
        if natureza is None or not natureza.ativo:
            raise ValueError("Selecione uma natureza válida do catálogo.")
    else:
        natureza = None
    genero = str(dados.get("genero") or "Ø").strip()
    permitidos = carregar_regras_pokemon_db(campanha.id).get("generos") or ["Ø", "♂", "♀"]
    if genero not in permitidos:
        raise ValueError("Gênero inválido para esta campanha.")
    shiny = str(dados.get("shiny") or "") == "1"
    regras = carregar_regras_pokemon_db(campanha.id)
    nivel = _nivel(modelo)
    pv_antigo = _pv_maximo(forma_antiga, nivel, regras)
    pv_novo = _pv_maximo(forma, nivel, regras)
    atual = int(item.get("pv_atual")) if item.get("pv_atual") is not None else pv_antigo
    dano = max(0, pv_antigo - min(pv_antigo, atual))

    nomes_golpes = dados.getlist("golpe_nome") if hasattr(dados, "getlist") else dados.get("golpe_nome", [])
    if isinstance(nomes_golpes, str):
        nomes_golpes = [nomes_golpes]
    if len(nomes_golpes) > 4:
        raise ValueError("A equipe permite até quatro golpes por Pokémon.")
    selecionados, usados = [], set()
    for nome_golpe in nomes_golpes:
        nome_golpe = str(nome_golpe or "").strip()
        if not nome_golpe:
            continue
        golpe = db.session.scalar(
            select(Golpe).where(Golpe.ativo.is_(True), func.lower(Golpe.nome) == nome_golpe.lower())
        )
        if golpe is None:
            raise ValueError(f"Golpe não cadastrado: {nome_golpe[:80]}.")
        if golpe.id in usados:
            raise ValueError("Um golpe não pode ocupar dois espaços da equipe.")
        usados.add(golpe.id)
        selecionados.append(str(golpe.id))

    item.update(
        forma_id=str(forma.id), nome=nome or forma.nome,
        imagem=(forma.imagem_shiny_url if shiny else forma.imagem_url) or forma.imagem_url or "",
        shiny=shiny, natureza_id=str(natureza.id) if natureza else None,
        natureza=natureza.nome if natureza else "—", genero=genero, golpes=selecionados,
        nivel=nivel,
        pv_atual=max(0, min(pv_novo, pv_novo - dano)),
    )
    equipe[idx] = item
    modelo.equipe = equipe
    _historico(usuario_id, modelo.id, "editar_pokemon_npc",
               antes={"indice": idx, "pokemon": anterior},
               depois={"indice": idx, "pokemon": item})
    db.session.commit()
    return "Pokémon do NPC atualizado com sucesso."


def mover_pokemon_ficha(*, campanha_codigo, modelo_id, indice, direcao, usuario_id):
    campanha = _campanha(campanha_codigo)
    modelo = _modelo(campanha.id, modelo_id)
    equipe = list(modelo.equipe or [])
    idx = _numero(indice, minimo=0, maximo=5, nome="Posição")
    proximo = idx + (1 if direcao == "baixo" else -1 if direcao == "cima" else 999)
    if idx >= len(equipe) or proximo < 0 or proximo >= len(equipe):
        raise ValueError("Não é possível mover o Pokémon para essa posição.")
    equipe[idx], equipe[proximo] = equipe[proximo], equipe[idx]
    modelo.equipe = equipe
    _historico(usuario_id, modelo.id, "reordenar_equipe_npc",
               antes={"de": idx}, depois={"para": proximo})
    db.session.commit()
    return "Ordem da equipe atualizada."
