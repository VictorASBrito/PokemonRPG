from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.extensions import db
from app.models.db import (
    Atributo,
    CategoriaGolpe,
    EspeciePokemon,
    FormaPokemon,
    FormaPokemonAtributo,
    FormaPokemonTipo,
    Golpe,
    Natureza,
    NaturezaModificador,
    StatusCondicao,
    TipoPokemon,
)
from app.services.importacao.utils import (
    categoria_forma,
    decimal,
    nome_especie,
    slug,
    uuid_legado,
)


class CatalogoImporter:
    def __init__(self, fontes, resumo) -> None:
        self.fontes = fontes
        self.resumo = resumo
        self.atributos: dict[str, Atributo] = {}
        self.tipos: dict[str, TipoPokemon] = {}
        self.categorias: dict[str, CategoriaGolpe] = {}
        self.especies: dict[str, EspeciePokemon] = {}
        self.formas: dict[str, FormaPokemon] = {}
        self.golpes: dict[str, Golpe] = {}
        self.naturezas: dict[str, Natureza] = {}
        self.status: dict[str, StatusCondicao] = {}

    @staticmethod
    def _mapear(modelo, campo: str = "codigo") -> dict[str, Any]:
        registros = db.session.execute(select(modelo)).scalars().all()
        return {str(getattr(item, campo)): item for item in registros}

    def executar(self) -> None:
        self.importar_atributos()
        self.importar_tipos()
        self.importar_categorias_golpe()
        self.importar_especies_formas()
        self.importar_golpes()
        self.importar_naturezas()
        self.importar_status()
        db.session.flush()

    def importar_atributos(self) -> None:
        existentes = self._mapear(Atributo)
        definicoes: dict[str, dict[str, Any]] = {}

        for ordem, item in enumerate(self.fontes.regras_treinador.get("atributos", []), start=1):
            codigo = slug(item.get("id") or item.get("nome"))
            definicoes[codigo] = {
                "nome": item.get("nome", codigo),
                "escopo": "personagem",
                "ordem": ordem,
                "descricao": None,
            }

        deslocamento = len(definicoes) + 1
        for ordem, item in enumerate(self.fontes.regras_pokemon.get("atributos", []), start=deslocamento):
            codigo = slug(item.get("id") or item.get("nome"))
            definicoes[codigo] = {
                "nome": item.get("nome", codigo),
                "escopo": "pokemon",
                "ordem": ordem,
                "descricao": None,
            }

        for codigo, dados in definicoes.items():
            registro = existentes.get(codigo)
            if registro is None:
                registro = Atributo(
                    id=uuid_legado("atributo", codigo),
                    codigo=codigo,
                    tipo_valor="inteiro",
                    **dados,
                )
                db.session.add(registro)
                self.resumo.criado("atributos")
            else:
                registro.nome = dados["nome"]
                registro.escopo = dados["escopo"]
                registro.ordem = dados["ordem"]
                registro.ativo = True
                self.resumo.atualizado("atributos")
            self.atributos[codigo] = registro

        db.session.flush()

    def importar_tipos(self) -> None:
        existentes = self._mapear(TipoPokemon)
        nomes: set[str] = set()
        for pokemon in self.fontes.catalogo_pokemons.get("pokemons", []):
            nomes.update(str(item).strip() for item in pokemon.get("tipos", []) if str(item).strip())
        for golpe in self.fontes.catalogo_golpes.get("golpes", []):
            nome = str(golpe.get("tipo", "")).strip()
            if nome:
                nomes.add(nome)

        for nome in sorted(nomes, key=str.casefold):
            codigo = slug(nome)
            registro = existentes.get(codigo)
            if registro is None:
                registro = TipoPokemon(
                    id=uuid_legado("tipo", codigo), codigo=codigo, nome=nome
                )
                db.session.add(registro)
                self.resumo.criado("tipos_pokemon")
            else:
                registro.nome = nome
                registro.ativo = True
                self.resumo.atualizado("tipos_pokemon")
            self.tipos[codigo] = registro
        db.session.flush()

    def importar_categorias_golpe(self) -> None:
        existentes = self._mapear(CategoriaGolpe)
        nomes = {
            str(item.get("categoria", "")).strip()
            for item in self.fontes.catalogo_golpes.get("golpes", [])
            if str(item.get("categoria", "")).strip()
        }
        for nome in sorted(nomes, key=str.casefold):
            codigo = slug(nome)
            registro = existentes.get(codigo)
            if registro is None:
                registro = CategoriaGolpe(
                    id=uuid_legado("categoria-golpe", codigo),
                    codigo=codigo,
                    nome=nome,
                )
                db.session.add(registro)
                self.resumo.criado("categorias_golpe")
            else:
                registro.nome = nome
                registro.ativo = True
                self.resumo.atualizado("categorias_golpe")
            self.categorias[codigo] = registro
        db.session.flush()

    def importar_especies_formas(self) -> None:
        especies_existentes = self._mapear(EspeciePokemon)
        formas_existentes = self._mapear(FormaPokemon)
        por_especie: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for item in self.fontes.catalogo_pokemons.get("pokemons", []):
            base = nome_especie(str(item.get("nome", item.get("id", "Pokémon"))))
            por_especie[slug(base)].append(item)

        for codigo_especie, formas in por_especie.items():
            nome_base = nome_especie(str(formas[0].get("nome", codigo_especie)))
            especie = especies_existentes.get(codigo_especie)
            if especie is None:
                especie = EspeciePokemon(
                    id=uuid_legado("especie", codigo_especie),
                    codigo=codigo_especie,
                    nome=nome_base,
                    numero=None,
                    geracao=None,
                    personalizada=False,
                )
                db.session.add(especie)
                self.resumo.criado("especies_pokemon")
            else:
                especie.nome = nome_base
                especie.ativo = True
                self.resumo.atualizado("especies_pokemon")
            self.especies[codigo_especie] = especie

        db.session.flush()

        for item in self.fontes.catalogo_pokemons.get("pokemons", []):
            codigo_forma = str(item.get("id") or slug(item.get("nome")))
            base = slug(nome_especie(str(item.get("nome", codigo_forma))))
            especie = self.especies[base]
            forma = formas_existentes.get(codigo_forma)
            configuracoes = {
                "ordem_catalogo": item.get("ordem_catalogo"),
                "origem": self.fontes.catalogo_pokemons.get("origem"),
                "versao_sistema": self.fontes.catalogo_pokemons.get("versao_sistema"),
            }
            if forma is None:
                forma = FormaPokemon(
                    id=uuid_legado("forma", codigo_forma),
                    especie_id=especie.id,
                    codigo=codigo_forma,
                    nome=str(item.get("nome", codigo_forma)),
                    categoria=categoria_forma(item),
                    imagem_url=item.get("imagem") or None,
                    imagem_shiny_url=item.get("imagem_shiny") or None,
                    configuracoes=configuracoes,
                )
                db.session.add(forma)
                self.resumo.criado("formas_pokemon")
            else:
                forma.especie_id = especie.id
                forma.nome = str(item.get("nome", codigo_forma))
                forma.categoria = categoria_forma(item)
                forma.imagem_url = item.get("imagem") or None
                forma.imagem_shiny_url = item.get("imagem_shiny") or None
                forma.configuracoes = configuracoes
                forma.ativo = True
                self.resumo.atualizado("formas_pokemon")
            self.formas[codigo_forma] = forma

        db.session.flush()

        # Relações e atributos são sincronizados, não apenas acrescentados.
        for item in self.fontes.catalogo_pokemons.get("pokemons", []):
            forma = self.formas[str(item.get("id"))]
            tipos_desejados = [slug(nome) for nome in item.get("tipos", []) if str(nome).strip()]
            atuais_tipo = {rel.posicao: rel for rel in forma.tipos}
            for posicao, codigo_tipo in enumerate(tipos_desejados[:2], start=1):
                tipo = self.tipos[codigo_tipo]
                rel = atuais_tipo.get(posicao)
                if rel is None:
                    rel = FormaPokemonTipo(
                        id=uuid_legado("forma-tipo", f"{forma.codigo}:{posicao}"),
                        forma_pokemon_id=forma.id,
                        tipo_id=tipo.id,
                        posicao=posicao,
                    )
                    db.session.add(rel)
                    self.resumo.criado("forma_pokemon_tipos")
                else:
                    rel.tipo_id = tipo.id
                    self.resumo.atualizado("forma_pokemon_tipos")
            for posicao, rel in atuais_tipo.items():
                if posicao > len(tipos_desejados[:2]):
                    db.session.delete(rel)
                    self.resumo.removido("forma_pokemon_tipos")

            atributos_desejados = item.get("atributos_base", {})
            atuais_atributo = {rel.atributo.codigo: rel for rel in forma.atributos_base}
            for codigo, valor in atributos_desejados.items():
                codigo = slug(codigo)
                atributo = self.atributos.get(codigo)
                if atributo is None:
                    self.resumo.aviso(
                        f'Atributo "{codigo}" da forma "{forma.codigo}" não foi cadastrado.'
                    )
                    continue
                rel = atuais_atributo.get(codigo)
                if rel is None:
                    rel = FormaPokemonAtributo(
                        id=uuid_legado("forma-atributo", f"{forma.codigo}:{codigo}"),
                        forma_pokemon_id=forma.id,
                        atributo_id=atributo.id,
                        valor_base=decimal(valor),
                    )
                    db.session.add(rel)
                    self.resumo.criado("forma_pokemon_atributos")
                else:
                    rel.valor_base = decimal(valor)
                    self.resumo.atualizado("forma_pokemon_atributos")
        db.session.flush()

    def importar_golpes(self) -> None:
        existentes = self._mapear(Golpe)
        for item in self.fontes.catalogo_golpes.get("golpes", []):
            codigo = str(item.get("id") or slug(item.get("nome")))
            categoria = self.categorias.get(slug(item.get("categoria")))
            if categoria is None:
                self.resumo.erro(f'Categoria ausente para o golpe "{codigo}".')
                continue
            tipo = self.tipos.get(slug(item.get("tipo")))
            precisao = item.get("precisao")
            efeitos = {"texto": item.get("efeito")} if item.get("efeito") else None
            registro = existentes.get(codigo)
            if registro is None:
                registro = Golpe(
                    id=uuid_legado("golpe", codigo),
                    codigo=codigo,
                    nome=str(item.get("nome", codigo)),
                    tipo_id=tipo.id if tipo else None,
                    categoria_id=categoria.id,
                    expressao_dano=str(item.get("dano", "")).strip() or None,
                    precisao=decimal(precisao) if precisao is not None else None,
                    prioridade=0,
                    descricao=item.get("efeito") or None,
                    efeitos=efeitos,
                    personalizado=False,
                )
                db.session.add(registro)
                self.resumo.criado("golpes")
            else:
                registro.nome = str(item.get("nome", codigo))
                registro.tipo_id = tipo.id if tipo else None
                registro.categoria_id = categoria.id
                registro.expressao_dano = str(item.get("dano", "")).strip() or None
                registro.precisao = decimal(precisao) if precisao is not None else None
                registro.descricao = item.get("efeito") or None
                registro.efeitos = efeitos
                registro.ativo = True
                self.resumo.atualizado("golpes")
            self.golpes[codigo] = registro
        db.session.flush()

    def importar_naturezas(self) -> None:
        existentes = self._mapear(Natureza)
        for item in self.fontes.regras_pokemon.get("naturezas", []):
            nome = str(item.get("nome", "")).strip()
            if not nome:
                continue
            codigo = slug(nome)
            natureza = existentes.get(codigo)
            if natureza is None:
                natureza = Natureza(
                    id=uuid_legado("natureza", codigo), codigo=codigo, nome=nome
                )
                db.session.add(natureza)
                self.resumo.criado("naturezas")
            else:
                natureza.nome = nome
                natureza.ativo = True
                self.resumo.atualizado("naturezas")
            self.naturezas[codigo] = natureza

        db.session.flush()

        for item in self.fontes.regras_pokemon.get("naturezas", []):
            natureza = self.naturezas.get(slug(item.get("nome")))
            if natureza is None:
                continue
            desejados: dict[str, Decimal] = {}
            if item.get("aumenta"):
                desejados[slug(item["aumenta"])] = Decimal("0.10")
            if item.get("diminui"):
                desejados[slug(item["diminui"])] = Decimal("-0.10")
            atuais = {rel.atributo.codigo: rel for rel in natureza.modificadores}
            for codigo_atributo, valor in desejados.items():
                atributo = self.atributos.get(codigo_atributo)
                if atributo is None:
                    continue
                rel = atuais.get(codigo_atributo)
                if rel is None:
                    rel = NaturezaModificador(
                        id=uuid_legado(
                            "natureza-modificador", f"{natureza.codigo}:{codigo_atributo}"
                        ),
                        natureza_id=natureza.id,
                        atributo_id=atributo.id,
                        tipo_modificador="percentual",
                        valor=valor,
                    )
                    db.session.add(rel)
                    self.resumo.criado("natureza_modificadores")
                else:
                    rel.tipo_modificador = "percentual"
                    rel.valor = valor
                    self.resumo.atualizado("natureza_modificadores")
            for codigo_atributo, rel in atuais.items():
                if codigo_atributo not in desejados:
                    db.session.delete(rel)
                    self.resumo.removido("natureza_modificadores")
        db.session.flush()

    def importar_status(self) -> None:
        existentes = self._mapear(StatusCondicao)
        for item in self.fontes.regras_pokemon.get("status", []):
            nome = str(item.get("nome", "")).strip()
            if not nome or nome.casefold() == "nenhum":
                continue
            codigo = slug(nome)
            registro = existentes.get(codigo)
            if registro is None:
                registro = StatusCondicao(
                    id=uuid_legado("status", codigo),
                    codigo=codigo,
                    nome=nome,
                    descricao=item.get("descricao") or None,
                    efeitos={"texto": item.get("descricao")} if item.get("descricao") else None,
                )
                db.session.add(registro)
                self.resumo.criado("status_condicoes")
            else:
                registro.nome = nome
                registro.descricao = item.get("descricao") or None
                registro.efeitos = (
                    {"texto": item.get("descricao")} if item.get("descricao") else None
                )
                registro.ativo = True
                self.resumo.atualizado("status_condicoes")
            self.status[codigo] = registro
        db.session.flush()
