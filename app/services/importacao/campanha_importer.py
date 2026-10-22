from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    Atributo,
    Campanha,
    CampanhaMembro,
    CategoriaItem,
    ConjuntoRegras,
    Insignia,
    Item,
    Personagem,
    PersonagemAtributo,
    PersonagemInsignia,
    PersonagemItem,
    Pokemon,
    PokemonBonusAtributo,
    PokemonGolpe,
    PokemonStatus,
    Regra,
    RegraValor,
    Usuario,
)
from app.services.importacao.utils import booleano, data_hora, inteiro, slug, uuid_legado


def _normalizar_mapa_atributos(valor: Any) -> dict[str, Any]:
    if not isinstance(valor, dict):
        return {}
    return {str(codigo).replace("_", "-"): numero for codigo, numero in valor.items()}


def _normalizar_estilos_combate(valor: Any) -> dict[str, Any]:
    if not isinstance(valor, dict):
        return {}
    return {
        str(estilo): _normalizar_mapa_atributos(modificadores)
        for estilo, modificadores in valor.items()
    }


class CampanhaImporter:
    def __init__(self, fontes, catalogo, resumo) -> None:
        self.fontes = fontes
        self.catalogo = catalogo
        self.resumo = resumo
        self.usuarios: dict[str, Usuario] = {}
        self.campanhas: dict[str, Campanha] = {}
        self.personagens: dict[str, Personagem] = {}

    @staticmethod
    def _todos(modelo) -> list[Any]:
        return list(db.session.execute(select(modelo)).scalars())

    def executar(self) -> None:
        self.importar_usuarios()
        self.importar_campanhas()
        self.importar_regras()
        self.importar_personagens()
        db.session.flush()

    def importar_usuarios(self) -> None:
        por_login = {item.login: item for item in self._todos(Usuario)}
        por_id = {item.id: item for item in self._todos(Usuario)}
        for item in self.fontes.usuarios.get("usuarios", []):
            login = str(item.get("login", "")).strip().lower()
            if not login:
                self.resumo.aviso("Um usuário sem login foi ignorado.")
                continue
            id_deterministico = uuid_legado("usuario", item.get("id") or login)
            usuario = por_id.get(id_deterministico) or por_login.get(login)
            if usuario is None:
                usuario = Usuario(
                    id=id_deterministico,
                    login=login,
                    nome=str(item.get("nome") or login),
                    senha_hash=str(item.get("senha_hash") or ""),
                    perfil=self._perfil(item.get("perfil")),
                    ativo=booleano(item.get("ativo"), True),
                )
                db.session.add(usuario)
                self.resumo.criado("usuarios")
            else:
                usuario.login = login
                usuario.nome = str(item.get("nome") or login)
                usuario.senha_hash = str(item.get("senha_hash") or usuario.senha_hash)
                usuario.perfil = self._perfil(item.get("perfil"))
                usuario.ativo = booleano(item.get("ativo"), True)
                self.resumo.atualizado("usuarios")
            self.usuarios[str(item.get("id") or login)] = usuario
        db.session.flush()

    @staticmethod
    def _perfil(valor: Any) -> str:
        perfil = str(valor or "jogador").strip().lower()
        return perfil if perfil in {"administrador", "mestre", "tester", "jogador"} else "jogador"

    def importar_campanhas(self) -> None:
        existentes = {item.codigo: item for item in self._todos(Campanha)}
        membros_existentes = {
            (item.campanha_id, item.usuario_id): item
            for item in self._todos(CampanhaMembro)
        }

        for item in self.fontes.campanhas:
            codigo = slug(item.get("id") or item.get("nome"), padrao="campanha")
            campanha = existentes.get(codigo)
            if campanha is None:
                campanha = Campanha(
                    id=uuid_legado("campanha", codigo),
                    codigo=codigo,
                    nome=str(item.get("nome") or codigo),
                    descricao=item.get("descricao") or None,
                )
                db.session.add(campanha)
                self.resumo.criado("campanhas")
            else:
                campanha.nome = str(item.get("nome") or codigo)
                campanha.descricao = item.get("descricao") or None
                campanha.ativo = True
                self.resumo.atualizado("campanhas")
            self.campanhas[str(item.get("id") or codigo)] = campanha

        db.session.flush()

        # Mestres são vinculados a todas as campanhas encontradas.
        for campanha in self.campanhas.values():
            for usuario in self.usuarios.values():
                if usuario.perfil not in {"mestre", "administrador"}:
                    continue
                chave = (campanha.id, usuario.id)
                membro = membros_existentes.get(chave)
                if membro is None:
                    db.session.add(
                        CampanhaMembro(
                            id=uuid_legado("campanha-membro", f"{campanha.id}:{usuario.id}"),
                            campanha_id=campanha.id,
                            usuario_id=usuario.id,
                            papel="mestre",
                        )
                    )
                    self.resumo.criado("campanha_membros")
                elif membro.papel != "mestre":
                    membro.papel = "mestre"
                    self.resumo.atualizado("campanha_membros")
        db.session.flush()

    def importar_regras(self) -> None:
        regras_pokemon = self.fontes.regras_pokemon
        regras_treinador = self.fontes.regras_treinador
        definicoes = {
            "tamanho-equipe": ("Tamanho da equipe", "limites", "inteiro", regras_pokemon.get("limites", {}).get("tamanho_equipe", 6)),
            "tamanho-box": ("Tamanho da Box", "limites", "inteiro", regras_pokemon.get("boxes", {}).get("espacos", 100)),
            "golpes-por-pokemon": ("Golpes por Pokémon", "limites", "inteiro", regras_pokemon.get("limites", {}).get("golpes_por_pokemon", 4)),
            "nivel-pokemon-igual-jogador": ("Nível Pokémon igual ao jogador", "pokemon", "booleano", True),
            "usar-pp": ("Usar Pontos de Poder", "pokemon", "booleano", False),
            "usar-experiencia": ("Usar experiência", "pokemon", "booleano", False),
            "usar-amizade": ("Usar amizade", "pokemon", "booleano", False),
            "usar-taxa-captura": ("Usar taxa de captura", "pokemon", "booleano", False),
            "usar-struggle": ("Usar golpe Luta/Struggle", "pokemon", "booleano", False),
            "pv-por-ponto-saude": ("PV por ponto de Saúde", "personagem", "inteiro", regras_treinador.get("pv_por_ponto_saude", 10)),
            "nivel-minimo": ("Nível mínimo", "personagem", "inteiro", regras_treinador.get("nivel_minimo", 1)),
            "nivel-maximo": ("Nível máximo", "personagem", "inteiro", regras_treinador.get("nivel_maximo", 100)),
            "limite-numeros-shiny": ("Limite de números Shiny", "personagem", "inteiro", regras_treinador.get("limite_numeros_shiny", 10)),
            "nivel-inicial": ("Nível inicial", "personagem", "inteiro", regras_treinador.get("nivel_inicial", 1)),
            "atributos-personagem-config": ("Configuração dos atributos do personagem", "personagem", "json", regras_treinador.get("atributos", [])),
            "origens-personagem": ("Origens de personagem", "personagem", "json", regras_treinador.get("origens", [])),
            "classes-personagem": ("Classes de personagem", "personagem", "json", regras_treinador.get("classes", [])),
            "estilos-combate-personagem": ("Estilos de combate do personagem", "personagem", "json", regras_treinador.get("estilos_combate", [])),
            "bonus-shiny": (
                "Bônus Shiny",
                "pokemon",
                "json",
                _normalizar_mapa_atributos(regras_pokemon.get("bonus_shiny", {})),
            ),
            "progressao-pv": ("Progressão de PV", "pokemon", "json", regras_pokemon.get("progressao_pv", [])),
            "progressao-atributos": ("Progressão dos atributos", "pokemon", "json", regras_pokemon.get("progressao_atributos", [])),
            "estilos-combate": (
                "Estilos de combate",
                "pokemon",
                "json",
                _normalizar_estilos_combate(regras_pokemon.get("estilos_combate", {})),
            ),
        }

        regras_existentes = {item.codigo: item for item in self._todos(Regra)}
        conjuntos = {
            (item.campanha_id, item.versao): item for item in self._todos(ConjuntoRegras)
        }
        valores_existentes = {
            (item.conjunto_regras_id, item.regra_id): item
            for item in self._todos(RegraValor)
        }

        regras_obj: dict[str, Regra] = {}
        for codigo, (nome, categoria, tipo, valor) in definicoes.items():
            regra = regras_existentes.get(codigo)
            if regra is None:
                regra = Regra(
                    id=uuid_legado("regra", codigo),
                    codigo=codigo,
                    nome=nome,
                    categoria=categoria,
                    tipo_valor=tipo,
                    valor_padrao=valor,
                )
                db.session.add(regra)
                self.resumo.criado("regras")
            else:
                regra.nome = nome
                regra.categoria = categoria
                regra.tipo_valor = tipo
                regra.valor_padrao = valor
                regra.ativo = True
                self.resumo.atualizado("regras")
            regras_obj[codigo] = regra

        db.session.flush()

        for fonte in self.fontes.campanhas:
            campanha = self.campanhas[str(fonte.get("id") or slug(fonte.get("nome")))]
            versao = str(
                fonte.get("configuracoes", {}).get("versao_regras")
                or regras_treinador.get("versao")
                or regras_pokemon.get("versao")
                or "inicial"
            )[:40]
            conjunto = conjuntos.get((campanha.id, versao))

            # Desativa a versão anterior antes de inserir uma nova. A ordem é
            # importante porque existe um índice parcial que permite apenas um
            # conjunto em uso por campanha.
            for outro in self._todos(ConjuntoRegras):
                if outro.campanha_id == campanha.id and (
                    conjunto is None or outro.id != conjunto.id
                ):
                    outro.em_uso = False
            db.session.flush()

            if conjunto is None:
                conjunto = ConjuntoRegras(
                    id=uuid_legado("conjunto-regras", f"{campanha.codigo}:{versao}"),
                    campanha_id=campanha.id,
                    nome=f"Regras de {campanha.nome}",
                    versao=versao,
                    descricao="Conjunto importado dos arquivos JSON legados.",
                    em_uso=True,
                )
                db.session.add(conjunto)
                self.resumo.criado("conjuntos_regras")
            else:
                conjunto.nome = f"Regras de {campanha.nome}"
                conjunto.em_uso = True
                conjunto.ativo = True
                self.resumo.atualizado("conjuntos_regras")
            db.session.flush()

            for codigo, regra in regras_obj.items():
                valor = definicoes[codigo][3]
                chave = (conjunto.id, regra.id)
                registro = valores_existentes.get(chave)
                if registro is None:
                    registro = RegraValor(
                        id=uuid_legado("regra-valor", f"{conjunto.id}:{regra.id}"),
                        conjunto_regras_id=conjunto.id,
                        regra_id=regra.id,
                        valor=valor,
                    )
                    db.session.add(registro)
                    self.resumo.criado("regra_valores")
                else:
                    registro.valor = valor
                    self.resumo.atualizado("regra_valores")
        db.session.flush()

    def importar_personagens(self) -> None:
        usuarios_por_id = {str(item.id): item for item in self._todos(Usuario)}
        personagens_existentes = {item.id: item for item in self._todos(Personagem)}
        membros_existentes = {
            (item.campanha_id, item.usuario_id): item
            for item in self._todos(CampanhaMembro)
        }
        proxima_ordem_por_campanha: dict[uuid.UUID, int] = {}

        for jogador in self.fontes.jogadores:
            legado_id = str(jogador.get("id") or "")
            usuario_legado = str(jogador.get("usuario_id") or "")
            usuario = self.usuarios.get(usuario_legado)
            if usuario is None:
                usuario = usuarios_por_id.get(str(uuid_legado("usuario", usuario_legado)))
            campanha = self.campanhas.get(str(jogador.get("campanha_id")))
            if usuario is None or campanha is None:
                self.resumo.erro(
                    f'Jogador "{legado_id}" não pôde ser importado: usuário ou campanha ausente.'
                )
                continue

            treinador = jogador.get("treinador", {})
            personagem_id = uuid_legado("personagem", legado_id)
            personagem = personagens_existentes.get(personagem_id)
            if personagem is None:
                personagem = Personagem(
                    id=personagem_id,
                    usuario_id=usuario.id,
                    campanha_id=campanha.id,
                    nome=str(treinador.get("nome") or usuario.nome),
                    nivel=max(1, inteiro(treinador.get("nivel"), 1)),
                    pokedolares=max(0, inteiro(treinador.get("pokedolares"), 0)),
                    pv_atual=max(0, inteiro(treinador.get("pv_atual"), 0)),
                )
                db.session.add(personagem)
                self.resumo.criado("personagens")
            else:
                self.resumo.atualizado("personagens")

            personagem.usuario_id = usuario.id
            personagem.campanha_id = campanha.id
            personagem.nome = str(treinador.get("nome") or usuario.nome)
            personagem.foto_url = treinador.get("foto_url") or None
            personagem.nivel = max(1, inteiro(treinador.get("nivel"), 1))
            personagem.idade = treinador.get("idade")
            personagem.genero = treinador.get("genero") or None
            personagem.origem = treinador.get("origem") or None
            personagem.classe = treinador.get("classe") or None
            personagem.estilo_combate = treinador.get("estilo_combate") or None
            personagem.numeros_shiny = treinador.get("numeros_shiny") or []
            personagem.pokedolares = max(0, inteiro(treinador.get("pokedolares"), 0))
            personagem.pv_atual = max(0, inteiro(treinador.get("pv_atual"), 0))
            personagem.beneficios_habilidades = treinador.get("beneficios_habilidades") or None
            personagem.anotacoes = treinador.get("anotacoes") or None
            personagem.ativo = True
            if personagem.ordem_painel is None:
                proxima_ordem = proxima_ordem_por_campanha.get(campanha.id, 0) + 1
                proxima_ordem_por_campanha[campanha.id] = proxima_ordem
                personagem.ordem_painel = proxima_ordem
            criado_em = data_hora(jogador.get("criado_em"))
            atualizado_em = data_hora(jogador.get("atualizado_em"))
            if criado_em:
                personagem.criado_em = criado_em
            if atualizado_em:
                personagem.atualizado_em = atualizado_em
            self.personagens[legado_id] = personagem

            chave_membro = (campanha.id, usuario.id)
            membro = membros_existentes.get(chave_membro)
            if membro is None:
                db.session.add(
                    CampanhaMembro(
                        id=uuid_legado("campanha-membro", f"{campanha.id}:{usuario.id}"),
                        campanha_id=campanha.id,
                        usuario_id=usuario.id,
                        papel="jogador",
                    )
                )
                self.resumo.criado("campanha_membros")
            elif membro.papel != "jogador" and usuario.perfil in {"jogador", "tester"}:
                membro.papel = "jogador"
                self.resumo.atualizado("campanha_membros")

            db.session.flush()
            self._importar_atributos_personagem(personagem, treinador)
            self._importar_inventario(personagem, jogador.get("inventario", []))
            self._importar_insigneas(personagem, jogador.get("insigneas", []))
            self._importar_pokemons(personagem, jogador)
        db.session.flush()

    def _importar_atributos_personagem(self, personagem: Personagem, treinador: dict[str, Any]) -> None:
        existentes = {item.atributo.codigo: item for item in personagem.atributos}
        for codigo, valor in treinador.get("atributos", {}).items():
            atributo = self.catalogo.atributos.get(slug(codigo))
            if atributo is None:
                continue
            registro = existentes.get(atributo.codigo)
            if registro is None:
                db.session.add(
                    PersonagemAtributo(
                        id=uuid_legado("personagem-atributo", f"{personagem.id}:{atributo.id}"),
                        personagem_id=personagem.id,
                        atributo_id=atributo.id,
                        valor=inteiro(valor),
                    )
                )
                self.resumo.criado("personagem_atributos")
            else:
                registro.valor = inteiro(valor)
                self.resumo.atualizado("personagem_atributos")

    def _categoria_item(self, codigo: str, nome: str) -> CategoriaItem:
        registro = db.session.execute(
            select(CategoriaItem).where(CategoriaItem.codigo == codigo)
        ).scalar_one_or_none()
        if registro is None:
            registro = CategoriaItem(
                id=uuid_legado("categoria-item", codigo), codigo=codigo, nome=nome
            )
            db.session.add(registro)
            db.session.flush()
            self.resumo.criado("categorias_item")
        return registro

    def _item(self, nome: str, categoria: CategoriaItem) -> Item:
        codigo = slug(nome)
        registro = db.session.execute(select(Item).where(Item.codigo == codigo)).scalar_one_or_none()
        if registro is None:
            registro = Item(
                id=uuid_legado("item", codigo),
                codigo=codigo,
                nome=nome,
                categoria_id=categoria.id,
                personalizado=True,
            )
            db.session.add(registro)
            db.session.flush()
            self.resumo.criado("itens")
        return registro

    def _importar_inventario(self, personagem: Personagem, itens: list[dict[str, Any]]) -> None:
        categoria = self._categoria_item("inventario-legado", "Inventário legado")
        existentes = {item.item.codigo: item for item in personagem.inventario}
        for dados in itens:
            nome = str(dados.get("nome", "")).strip()
            if not nome:
                continue
            item = self._item(nome, categoria)
            registro = existentes.get(item.codigo)
            quantidade = max(0, inteiro(dados.get("quantidade"), 0))
            if registro is None:
                db.session.add(
                    PersonagemItem(
                        id=uuid_legado("personagem-item", f"{personagem.id}:{item.id}"),
                        personagem_id=personagem.id,
                        item_id=item.id,
                        quantidade=quantidade,
                    )
                )
                self.resumo.criado("personagem_itens")
            else:
                registro.quantidade = quantidade
                self.resumo.atualizado("personagem_itens")

    def _importar_insigneas(self, personagem: Personagem, dados: list[dict[str, Any]]) -> None:
        existentes_catalogo = {item.codigo: item for item in self._todos(Insignia)}
        existentes_personagem = {item.insignia.codigo: item for item in personagem.insignias}
        for entrada in dados:
            nome = str(entrada.get("nome", "")).strip()
            if not nome:
                continue
            codigo = slug(nome)
            insignia = existentes_catalogo.get(codigo)
            if insignia is None:
                insignia = Insignia(
                    id=uuid_legado("insignia", codigo), codigo=codigo, nome=nome
                )
                db.session.add(insignia)
                db.session.flush()
                existentes_catalogo[codigo] = insignia
                self.resumo.criado("insignias")
            if codigo not in existentes_personagem:
                db.session.add(
                    PersonagemInsignia(
                        id=uuid_legado("personagem-insignia", f"{personagem.id}:{insignia.id}"),
                        personagem_id=personagem.id,
                        insignia_id=insignia.id,
                    )
                )
                self.resumo.criado("personagem_insignias")

    def _importar_pokemons(self, personagem: Personagem, jogador: dict[str, Any]) -> None:
        existentes = {item.id: item for item in personagem.pokemons}
        equipe = [str(item) for item in jogador.get("equipe", [])]
        box_ids: list[str] = []
        for box in jogador.get("boxes", []):
            box_ids.extend(str(item) for item in box.get("pokemon_ids", []))
        posicoes_equipe = {pokemon_id: indice for indice, pokemon_id in enumerate(equipe, start=1)}
        posicoes_box = {pokemon_id: indice for indice, pokemon_id in enumerate(box_ids, start=1)}

        sem_local = [
            str(item.get("id"))
            for item in jogador.get("pokemons", [])
            if str(item.get("id")) not in posicoes_equipe and str(item.get("id")) not in posicoes_box
        ]
        inicio = len(posicoes_box)
        for indice, pokemon_id in enumerate(sem_local, start=inicio + 1):
            posicoes_box[pokemon_id] = indice

        for dados in jogador.get("pokemons", []):
            legado_id = str(dados.get("id") or "")
            forma = self.catalogo.formas.get(str(dados.get("especie_id")))
            if forma is None:
                self.resumo.erro(
                    f'Pokémon "{legado_id}" não pôde ser importado: forma '
                    f'"{dados.get("especie_id")}" ausente.'
                )
                continue
            pokemon_id = uuid_legado("pokemon", legado_id)
            pokemon = existentes.get(pokemon_id)
            if pokemon is None:
                pokemon = Pokemon(
                    id=pokemon_id,
                    personagem_id=personagem.id,
                    forma_pokemon_id=forma.id,
                    pv_atual=max(0, inteiro(dados.get("pv_atual"), 0)),
                )
                db.session.add(pokemon)
                self.resumo.criado("pokemons")
            else:
                self.resumo.atualizado("pokemons")

            pokemon.forma_pokemon_id = forma.id
            pokemon.apelido = dados.get("apelido") or None
            pokemon.genero = dados.get("genero") or None
            pokemon.shiny = booleano(dados.get("shiny"), False)
            natureza = self.catalogo.naturezas.get(slug(dados.get("natureza")))
            pokemon.natureza_id = natureza.id if natureza else None
            pokemon.pv_atual = max(0, inteiro(dados.get("pv_atual"), 0))
            pokemon.anotacoes = dados.get("anotacoes") or None
            pokemon.ativo = True
            if legado_id in posicoes_equipe:
                pokemon.localizacao = "equipe"
                pokemon.posicao = posicoes_equipe[legado_id]
            else:
                pokemon.localizacao = "box"
                pokemon.posicao = posicoes_box[legado_id]

            item_nome = str(dados.get("item_carregado", "")).strip()
            if item_nome:
                categoria = self._categoria_item("item-carregado", "Itens carregados")
                pokemon.item_equipado_id = self._item(item_nome, categoria).id
            else:
                pokemon.item_equipado_id = None

            db.session.flush()
            self._importar_bonus_pokemon(pokemon, dados.get("bonus", {}))
            self._importar_golpes_pokemon(pokemon, dados.get("golpes", []))
            self._importar_status_pokemon(pokemon, dados.get("status"))

    def _importar_bonus_pokemon(self, pokemon: Pokemon, bonus: dict[str, Any]) -> None:
        existentes = {item.atributo.codigo: item for item in pokemon.bonus_atributos}
        for codigo, valor in bonus.items():
            atributo = self.catalogo.atributos.get(slug(codigo))
            if atributo is None:
                continue
            registro = existentes.get(atributo.codigo)
            if registro is None:
                db.session.add(
                    PokemonBonusAtributo(
                        id=uuid_legado("pokemon-bonus", f"{pokemon.id}:{atributo.id}"),
                        pokemon_id=pokemon.id,
                        atributo_id=atributo.id,
                        valor=inteiro(valor),
                    )
                )
                self.resumo.criado("pokemon_bonus_atributos")
            else:
                registro.valor = inteiro(valor)
                self.resumo.atualizado("pokemon_bonus_atributos")

    def _importar_golpes_pokemon(self, pokemon: Pokemon, golpes: list[Any]) -> None:
        atuais = {item.posicao: item for item in pokemon.golpes}
        desejados: list[str] = []
        for entrada in golpes[:4]:
            if isinstance(entrada, dict):
                codigo = entrada.get("golpe_id") or entrada.get("id") or entrada.get("nome")
            else:
                codigo = entrada
            codigo = str(codigo or "").strip()
            if codigo:
                desejados.append(codigo)

        for posicao, codigo in enumerate(desejados, start=1):
            golpe = self.catalogo.golpes.get(codigo) or self.catalogo.golpes.get(slug(codigo))
            if golpe is None:
                self.resumo.aviso(f'Golpe "{codigo}" do Pokémon "{pokemon.id}" foi ignorado.')
                continue
            registro = atuais.get(posicao)
            if registro is None:
                db.session.add(
                    PokemonGolpe(
                        id=uuid_legado("pokemon-golpe", f"{pokemon.id}:{posicao}"),
                        pokemon_id=pokemon.id,
                        golpe_id=golpe.id,
                        posicao=posicao,
                    )
                )
                self.resumo.criado("pokemon_golpes")
            else:
                registro.golpe_id = golpe.id
                self.resumo.atualizado("pokemon_golpes")
        for posicao, registro in atuais.items():
            if posicao > len(desejados):
                db.session.delete(registro)
                self.resumo.removido("pokemon_golpes")

    def _importar_status_pokemon(self, pokemon: Pokemon, valor: Any) -> None:
        nome = str(valor or "").strip()
        atuais = {item.status.codigo: item for item in pokemon.status_ativos}
        desejado = None if not nome or nome.casefold() == "nenhum" else self.catalogo.status.get(slug(nome))
        for codigo, registro in atuais.items():
            if desejado is None or codigo != desejado.codigo:
                db.session.delete(registro)
                self.resumo.removido("pokemon_status")
        if desejado and desejado.codigo not in atuais:
            db.session.add(
                PokemonStatus(
                    id=uuid_legado("pokemon-status", f"{pokemon.id}:{desejado.id}"),
                    pokemon_id=pokemon.id,
                    status_id=desejado.id,
                )
            )
            self.resumo.criado("pokemon_status")
