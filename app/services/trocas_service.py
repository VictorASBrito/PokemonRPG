"""Trocas bilaterais: validar a mesma revisão e transferir sem duplicar Pokémon."""
from uuid import UUID

from sqlalchemy import or_, select
from app.extensions import db
from app.models.db import (
    Campanha, CampanhaMembro, HistoricoAlteracao, Personagem,
    Pokemon, PokemonEmCampo, TrocaPokemon, Usuario,
)
from app.services.pokemon_db_service import carregar_regras_pokemon_db, calcular_pokemon

ATIVAS = ("pendente", "negociacao")


class ErroTroca(ValueError):
    pass


def uuid_valido(valor):
    try:
        return UUID(str(valor))
    except (ValueError, TypeError, AttributeError):
        raise ErroTroca("Identificador inválido.") from None


def jogadores(campanha):
    return (select(Personagem)
            .join(Usuario, Usuario.id == Personagem.usuario_id)
            .join(Campanha, Campanha.id == Personagem.campanha_id)
            .join(CampanhaMembro, (CampanhaMembro.usuario_id == Usuario.id) &
                  (CampanhaMembro.campanha_id == Campanha.id))
            .where(Personagem.campanha_id == campanha, Personagem.ativo.is_(True),
                   Usuario.ativo.is_(True), Usuario.perfil == "jogador",
                   Campanha.ativo.is_(True), CampanhaMembro.papel == "jogador"))


def titular(sessao):
    if sessao.get("perfil") != "jogador":
        raise ErroTroca("Apenas jogadores podem negociar.")
    p = db.session.scalar(jogadores(uuid_valido(sessao.get("campanha_id"))).where(
        Personagem.id == uuid_valido(sessao.get("personagem_id")),
        Personagem.usuario_id == uuid_valido(sessao.get("usuario_id"))))
    if p is None:
        raise ErroTroca("Ficha não autorizada.")
    return p


def criar(autor, destino):
    pid = uuid_valido(destino)
    if pid == autor.id or not db.session.scalar(jogadores(autor.campanha_id).where(Personagem.id == pid)):
        raise ErroTroca("Selecione outro jogador ativo da campanha.")
    troca = TrocaPokemon(campanha_id=autor.campanha_id, proponente_id=autor.id,
                         destinatario_id=pid, oferta_a=[], oferta_b=[])
    db.session.add(troca)
    db.session.flush()
    return troca


def consulta(autor):
    return select(TrocaPokemon).where(
        TrocaPokemon.campanha_id == autor.campanha_id,
        or_(TrocaPokemon.proponente_id == autor.id, TrocaPokemon.destinatario_id == autor.id))


def buscar(autor, codigo, bloquear=False):
    q = consulta(autor).where(TrocaPokemon.id == uuid_valido(codigo))
    if bloquear:
        q = q.with_for_update().execution_options(populate_existing=True)
    return db.session.scalar(q)


def elegivel(p, campo):
    return (p.ativo and p.localizacao == "box" and p.item_equipado_id is None
            and p.forma_temporaria_id is None and p.id not in campo)


def campo_ids(ids):
    if not ids:
        return set()
    return set(db.session.scalars(select(PokemonEmCampo.pokemon_id).where(
        PokemonEmCampo.pokemon_id.in_(ids))).all())


def oferta_valida(autor, ids):
    if len(ids) > 3:
        raise ErroTroca("Ofereça no máximo três Pokémon.")
    uuids = [uuid_valido(i) for i in ids]
    if len(set(uuids)) != len(uuids):
        raise ErroTroca("Não repita Pokémon na oferta.")
    registros = list(db.session.scalars(select(Pokemon).where(
        Pokemon.personagem_id == autor.id, Pokemon.id.in_(uuids))).all())
    campo = campo_ids(uuids)
    if len(registros) != len(uuids) or any(not elegivel(p, campo) for p in registros):
        raise ErroTroca("A oferta contém Pokémon indisponíveis. Use apenas sua Box, sem item equipado ou transformação.")
    return [str(i) for i in uuids]


def _concluir(t, autor):
    # Ordem estável de bloqueio: participantes e depois todos os seus Pokémon.
    # A negociação já está bloqueada por buscar(..., bloquear=True).
    donos = [t.proponente_id, t.destinatario_id]
    participantes = list(db.session.scalars(
        select(Personagem).where(Personagem.id.in_(donos)).order_by(Personagem.id)
        .with_for_update().execution_options(populate_existing=True)).all())
    ativos = {p.id for p in db.session.scalars(jogadores(t.campanha_id).where(Personagem.id.in_(donos))).all()}
    if ativos != set(donos):
        raise ErroTroca("Um dos jogadores não está mais disponível.")
    por_dono = {p.id: p for p in participantes}
    registros = list(db.session.scalars(
        select(Pokemon).where(Pokemon.personagem_id.in_(donos)).order_by(Pokemon.id)
        .with_for_update().execution_options(populate_existing=True)).all())
    por_id = {str(p.id): p for p in registros}
    ofertas = [(donos[0], donos[1], t.oferta_a), (donos[1], donos[0], t.oferta_b)]
    ids = t.oferta_a + t.oferta_b
    if not ids or len(set(ids)) != len(ids) or any(len(o[2]) > 3 for o in ofertas):
        raise ErroTroca("Ofertas inválidas para conclusão.")
    campo = campo_ids([uuid_valido(i) for i in ids])
    for origem, _, oferta in ofertas:
        for identidade in oferta:
            p = por_id.get(identidade)
            if p is None or p.personagem_id != origem or not elegivel(p, campo):
                raise ErroTroca("Uma oferta mudou ou deixou de estar disponível. Revise os Pokémon antes de confirmar.")
    regras = carregar_regras_pokemon_db(t.campanha_id)
    limite = int(regras["boxes"]["espacos"])
    ultimas = {}
    for origem, destino, oferta in ofertas:
        ocupados = sum(p.ativo and p.localizacao == "box" and p.personagem_id == destino for p in registros)
        saida = len(t.oferta_b if destino == donos[1] else t.oferta_a)
        if ocupados - saida + len(oferta) > limite:
            raise ErroTroca("A Box de um dos jogadores não comporta a troca.")
        ultimas[destino] = max((p.posicao or 0 for p in registros
                               if p.personagem_id == destino and p.localizacao == "box"), default=0)
    # Libera posições antes de mudar donos para não colidir com chave única.
    for identidade in ids:
        por_id[identidade].posicao = None
    db.session.flush()
    for origem, destino, oferta in ofertas:
        for identidade in oferta:
            p = por_id[identidade]
            ultimas[destino] += 1
            p.personagem_id = destino
            p.posicao = ultimas[destino]
            # A progressão depende do treinador; não curar durante a troca.
            maximo = calcular_pokemon(p, por_dono[destino], regras)["totais"]["pv"]
            p.pv_atual = min(p.pv_atual, maximo)
            db.session.add(HistoricoAlteracao(
                usuario_id=autor.usuario_id, entidade="pokemon", registro_id=p.id,
                acao="troca", dados_anteriores={"personagem_id": str(origem)},
                dados_novos={"personagem_id": str(destino), "troca_id": str(t.id)}))
    t.estado = "concluida"
    t.revisao += 1
    db.session.flush()


def agir(t, autor, acao, revisao, ids=()):
    if t.estado not in ATIVAS or str(t.revisao) != str(revisao):
        raise ErroTroca("A troca foi atualizada. Revise as ofertas atuais.")
    a = t.proponente_id == autor.id
    if not a and t.destinatario_id != autor.id:
        raise ErroTroca("Troca não autorizada.")
    if acao == "cancelar":
        t.estado = "cancelada"
        t.revisao += 1
        return
    if t.estado == "pendente":
        if a or acao not in ("aceitar", "recusar"):
            raise ErroTroca("Apenas o destinatário pode responder ao convite.")
        t.estado = "negociacao" if acao == "aceitar" else "recusada"
        t.revisao += 1
        return
    if acao == "ofertar":
        novos = oferta_valida(autor, ids)
        campo = "oferta_a" if a else "oferta_b"
        if novos != getattr(t, campo):
            setattr(t, campo, novos)
            t.confirmou_a = t.confirmou_b = False
            t.revisao += 1
        return
    if acao == "desconfirmar":
        t.confirmou_a = t.confirmou_b = False
        t.revisao += 1
        return
    if acao != "confirmar":
        raise ErroTroca("Ação inválida.")
    if not t.oferta_a and not t.oferta_b:
        raise ErroTroca("Ao menos um Pokémon deve ser oferecido.")
    if a:
        t.confirmou_a = True
    else:
        t.confirmou_b = True
    if t.confirmou_a and t.confirmou_b:
        _concluir(t, autor)
