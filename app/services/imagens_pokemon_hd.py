"""Sincronização conservadora de artes Pokémon HD.

Somente arquivos oficiais do repositório PokéAPI/sprites são aceitos.
As variantes do catálogo Ankar recebem aliases explícitos: nunca se troca uma
variante por sua espécie base somente porque uma imagem HD está faltando.
"""
from __future__ import annotations

import json
import re
import struct
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

API_BASE = "https://pokeapi.co/api/v2/pokemon/"
API_FORM_BASE = "https://pokeapi.co/api/v2/pokemon-form/"
PREFIXO_ARTE = "/PokeAPI/sprites/master/sprites/pokemon/"
LIMITE_BYTES = 8 * 1024 * 1024
LIMITE_API_BYTES = 5 * 1024 * 1024
MINIMO_RESOLUCAO = 256
CODIGO_VALIDO = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
PNG_ASSINATURA = b"\x89PNG\r\n\x1a\n"
WEBP_ASSINATURA = b"WEBP"

# IDs de espécies que correspondem às formas padrão do catálogo. A busca
# numérica complementa URLs incompletas da API; não substitui uma Mega ou
# forma regional por outra forma. Zacian/Zamazenta nos IDs 888/889 são Hero.
IDS_ESPECIAIS = {
    "frillish": 592,
    "jellicent": 593,
    "pyroar": 668,
    "zacian-heroi": 888,
    "zamazenta-heroi": 889,
}

# Estas três exceções não possuem uma arte Shiny/cores genérica inequívoca.
# Só são usadas com autorização explícita (--representativas).
REPRESENTATIVAS = {
    "eevee-parceiro": ("eevee", 133, ("shiny",)),
    "pikachu-parceiro": ("pikachu", 25, ("shiny",)),
    "minior-nucleo": ("minior-red", None, ("normal", "shiny")),
}


# Alterações de idioma/nomenclatura do catálogo da campanha para os nomes
# próprios da PokéAPI. Não há fallback indiscriminado para a espécie base.
ALIASES_POKEAPI = {
    "aegislash-escudo": "aegislash-shield",
    "aegislash-lamina": "aegislash-blade",
    "basculin-azul": "basculin-blue-striped",
    "basculin-vermelho": "basculin-red-striped",
    "burmy-arenoso": "burmy-sandy",
    "burmy-entulho": "burmy-trash",
    "burmy-planta": "burmy-plant",
    "calyrex-cavaleiro-gelado": "calyrex-ice",
    "calyrex-cavaleiro-sombrio": "calyrex-shadow",
    "castform-chuvoso": "castform-rainy",
    "castform-ensolarado": "castform-sunny",
    "castform-nevado": "castform-snowy",
    "darmanitan-galar-normal": "darmanitan-galar-standard",
    "darmanitan-normal": "darmanitan-standard",
    "deoxys-ataque": "deoxys-attack",
    "deoxys-velocidade": "deoxys-speed",
    "eevee-parceiro": "eevee-starter",
    "eiscue-congelado": "eiscue-ice",
    "eiscue-revelado": "eiscue-noice",
    "farfetch-d": "farfetchd",
    "farfetch-d-galar": "farfetchd-galar",
    "giratina-alternativa": "giratina-altered",
    "giratina-origem": "giratina-origin",
    "gourgeist-gigante": "gourgeist-super",
    "gourgeist-grande": "gourgeist-large",
    "gourgeist-medio": "gourgeist-average",
    "gourgeist-pequeno": "gourgeist-small",
    "groudon-primitivo": "groudon-primal",
    "hoopa-confinado": "hoopa",
    "hoopa-livre": "hoopa-unbound",
    "indeedee-femea": "indeedee-female",
    "indeedee-macho": "indeedee-male",
    "keldeo-corajoso": "keldeo-resolute",
    "keldeo-normal": "keldeo-ordinary",
    "kyogre-primitivo": "kyogre-primal",
    "kyurem-branco": "kyurem-white",
    "kyurem-preto": "kyurem-black",
    "landorus-animal": "landorus-therian",
    "landorus-corporeo": "landorus-incarnate",
    "lycanroc-crepusculo": "lycanroc-dusk",
    "lycanroc-meia-noite": "lycanroc-midnight",
    "lycanroc-meio-dia": "lycanroc-midday",
    "meloetta-melodia": "meloetta-aria",
    "meloetta-pirueta": "meloetta-pirouette",
    "meowstic-femea": "meowstic-female",
    "meowstic-macho": "meowstic-male",
    "mimikyu": "mimikyu-disguised",
    "minior-meteoro": "minior-red-meteor",  # meteoros partilham a aparência cinza
    # minior-nucleo representa várias cores: só escolher vermelho com --representativas.
    "morpeko-faminto": "morpeko-hangry",
    "morpeko-satisfeito": "morpeko-full-belly",
    "necrozma-alvorada": "necrozma-dawn",
    "necrozma-crepusculo-mane": "necrozma-dusk",
    "nidoran": "nidoran-f",  # confirmado pelo nome Nidoran♀ no catálogo
    "nidoran-2": "nidoran-m",  # confirmado pelo nome Nidoran♂ no catálogo
    "oricorio-pa-hu": "oricorio-pau",
    "pikachu-parceiro": "pikachu-starter",
    "pumpkaboo-gigante": "pumpkaboo-super",
    "pumpkaboo-grande": "pumpkaboo-large",
    "pumpkaboo-medio": "pumpkaboo-average",
    "pumpkaboo-pequeno": "pumpkaboo-small",
    "rotom-aparador": "rotom-mow",
    "rotom-geladeira": "rotom-frost",
    "rotom-maquina-de-lavar": "rotom-wash",
    "rotom-microondas": "rotom-heat",
    "rotom-ventilador": "rotom-fan",
    "shaymin-ceu": "shaymin-sky",
    "shaymin-terra": "shaymin-land",
    "sirfetch-d": "sirfetchd",
    "thundurus-animal": "thundurus-therian",
    "thundurus-corporeo": "thundurus-incarnate",
    "tornadus-animal": "tornadus-therian",
    "tornadus-corporeo": "tornadus-incarnate",
    "toxtricity-amplificado": "toxtricity-amped",
    "toxtricity-suave": "toxtricity-low-key",
    "urshifu-ataque-rapido": "urshifu-rapid-strike",
    "urshifu-golpe-unico": "urshifu-single-strike",
    "wishiwashi-cardume": "wishiwashi-school",
    "wishiwashi-sozinho": "wishiwashi-solo",
    "wormadam-arenoso": "wormadam-sandy",
    "wormadam-entulho": "wormadam-trash",
    "wormadam-planta": "wormadam-plant",
    "zacian-espada": "zacian-crowned",
    "zacian-heroi": "zacian-hero",
    "zamazenta-escudo": "zamazenta-crowned",
    "zamazenta-heroi": "zamazenta-hero",
    "zygarde-100": "zygarde-complete",
}

TIPOS_ARCEUS = {
    "agua": "water", "dragao": "dragon", "eletrico": "electric", "fada": "fairy",
    "fantasma": "ghost", "fogo": "fire", "gelo": "ice", "grama": "grass",
    "inseto": "bug", "lutador": "fighting", "metal": "steel", "normal": "normal",
    "noturno": "dark", "pedra": "rock", "psiquico": "psychic", "terra": "ground",
    "veneno": "poison", "voador": "flying",
}


@dataclass(frozen=True)
class ArteHD:
    normal: str | None
    shiny: str | None
    alternativas_normal: tuple[str, ...] = ()
    alternativas_shiny: tuple[str, ...] = ()
    codigo_fonte: str = ""

    def candidatas(self, tipo: str) -> tuple[str, ...]:
        if tipo == "normal":
            return tuple(dict.fromkeys(url for url in (self.normal, *self.alternativas_normal) if url))
        if tipo == "shiny":
            return tuple(dict.fromkeys(url for url in (self.shiny, *self.alternativas_shiny) if url))
        raise ValueError("Tipo de arte inválido.")


def codigo_pokeapi(codigo: str, *, representativas: bool = False) -> str:
    if not CODIGO_VALIDO.fullmatch(codigo):
        raise ValueError("Código de forma Pokémon inválido para consulta externa.")
    if representativas and codigo in REPRESENTATIVAS:
        return REPRESENTATIVAS[codigo][0]
    if codigo.startswith("arceus-") and codigo.split("-", 1)[1] in TIPOS_ARCEUS:
        return "arceus-" + TIPOS_ARCEUS[codigo.split("-", 1)[1]]
    return ALIASES_POKEAPI.get(codigo, codigo)


def imagem_do_catalogo_padrao(url: str | None) -> bool:
    """Somente URLs padrão antigas são substituídas, nunca uploads manuais."""
    if not url:
        return False
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.hostname == "img.pokemondb.net"
            and parsed.path.startswith("/sprites/home/") and parsed.path.endswith(".png"))


def url_arte_confiavel(url: str | None) -> bool:
    if not url:
        return False
    endereco = urlparse(url)
    return (endereco.scheme == "https"
            and endereco.hostname == "raw.githubusercontent.com"
            and endereco.port in (None, 443)
            and endereco.username is None and endereco.password is None
            and endereco.path.startswith(PREFIXO_ARTE)
            and endereco.path.endswith((".png", ".webp"))
            and not endereco.query and not endereco.fragment)


def _ler(url: str, *, max_bytes: int = LIMITE_BYTES, timeout: int = 25, tentativas: int = 3) -> bytes:
    """Repetir apenas erros transitórios; 404 não melhora com tentativas."""
    request = Request(url, headers={"User-Agent": "PokeRPG-Ankar/1.1 (media-sync)"})
    for indice in range(tentativas):
        try:
            with urlopen(request, timeout=timeout) as resposta:
                dados = resposta.read(max_bytes + 1)
                if len(dados) > max_bytes:
                    raise ValueError("Resposta excede o tamanho máximo permitido.")
                return dados
        except HTTPError as erro:
            if erro.code not in (408, 429, 500, 502, 503, 504) or indice == tentativas - 1:
                raise
        except (TimeoutError, ConnectionError, URLError):
            if indice == tentativas - 1:
                raise
        time.sleep(min(1.5 * (indice + 1), 4))
    raise RuntimeError("Falha inesperada no download.")


def _primeiras_artes(dados: dict) -> ArteHD:
    """Obtém HOME e arte oficial, depois renders 512px WebP das gerações VIII/IX.

    Sprites de sexo feminino só entram como último recurso quando o sprite
    padrão correspondente está ausente. No catálogo, essas espécies não têm
    uma forma exclusiva por sexo.
    """
    sprites = dados.get("sprites") or {}
    outro = sprites.get("other") or {}
    home = outro.get("home") or {}
    artwork = outro.get("official-artwork") or {}
    versoes = sprites.get("versions") or {}
    geracao8 = versoes.get("generation-viii") or {}
    geracao9 = versoes.get("generation-ix") or {}
    outras = (
        geracao9.get("scarlet-violet") or {},
        geracao8.get("sword-shield") or {},
        geracao8.get("brilliant-diamond-shining-pearl") or {},
    )
    urls_normais = [home.get("front_default"), artwork.get("front_default")]
    urls_shiny = [home.get("front_shiny"), artwork.get("front_shiny")]
    urls_normais.extend(v.get("front_default") for v in outras)
    urls_shiny.extend(v.get("front_shiny") for v in outras)
    if not any(urls_normais):
        urls_normais.extend([home.get("front_female"), *(v.get("front_female") for v in outras)])
    if not any(urls_shiny):
        urls_shiny.extend([home.get("front_shiny_female"), *(v.get("front_shiny_female") for v in outras)])

    def seguras(urls):
        return tuple(dict.fromkeys(u for u in urls if url_arte_confiavel(u)))
    normais = seguras(urls_normais)
    shiny = seguras(urls_shiny)
    return ArteHD(normais[0] if normais else None, shiny[0] if shiny else None,
                  normais[1:], shiny[1:])


def _candidatas_pelo_id(numero: int, tipo: str) -> tuple[str, ...]:
    """Reservas por ID para espécies cujos metadados não listam tudo.

    URLs são apenas candidatas, não garantias: todas passam por download e
    validação antes da atualização do banco.
    """
    base = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/"
    sufixo = "shiny/" if tipo == "shiny" else ""
    return tuple(
        base + caminho + sufixo + f"{numero}.{extensao}"
        for caminho, extensao in (
            ("other/home/", "png"),
            ("other/official-artwork/", "png"),
            ("versions/generation-ix/scarlet-violet/", "webp"),
            ("versions/generation-viii/sword-shield/", "webp"),
            ("versions/generation-viii/brilliant-diamond-shining-pearl/", "webp"),
        )
    )


def _completar_artes(artes: ArteHD, codigo: str, *, representativas: bool,
                     numero_api: int | None = None) -> ArteHD:
    numero = IDS_ESPECIAIS.get(codigo)
    tipos_habilitados = ("normal", "shiny")
    if representativas and codigo in REPRESENTATIVAS:
        _equivalente, numero, tipos_habilitados = REPRESENTATIVAS[codigo]
        if codigo == "minior-nucleo":
            numero = numero_api
    def lista(tipo: str) -> tuple[str, ...]:
        urls = artes.candidatas(tipo) if tipo in tipos_habilitados else ()
        if numero is not None and tipo in tipos_habilitados:
            urls += _candidatas_pelo_id(numero, tipo)
        return tuple(dict.fromkeys(urls))
    n, s = lista("normal"), lista("shiny")
    return ArteHD(n[0] if n else None, s[0] if s else None,
                  n[1:], s[1:], artes.codigo_fonte)


def procurar_artes_hd(codigo: str, *, representativas: bool = False) -> ArteHD:
    """Consulta uma forma exata e tenta reservas verificáveis quando necessário.

    --representativas permite a imagem Shiny normal da mesma espécie para
    parceiros e a cor vermelha como exemplar do núcleo de Minior. Nunca usa
    uma espécie diferente ou uma imagem normal no lugar da Shiny.
    """
    nome = codigo_pokeapi(codigo, representativas=representativas)
    ultima_404 = None
    id_pokemon = None
    for base in (API_BASE, API_FORM_BASE):
        try:
            dados = json.loads(_ler(base + quote(nome, safe="-"), max_bytes=LIMITE_API_BYTES))
        except HTTPError as erro:
            if erro.code != 404:
                raise
            ultima_404 = erro
            continue
        if (base == API_BASE and isinstance(dados.get("id"), int)
                and dados["id"] > 0):
            id_pokemon = dados["id"]
        artes = _primeiras_artes(dados)
        if artes.normal or artes.shiny:
            return _completar_artes(
                ArteHD(artes.normal, artes.shiny,
                       artes.alternativas_normal, artes.alternativas_shiny, nome),
                codigo, representativas=representativas,
                numero_api=id_pokemon)
    vazia = _completar_artes(ArteHD(None, None, codigo_fonte=nome),
                            codigo, representativas=representativas,
                numero_api=id_pokemon)
    if vazia.normal or vazia.shiny:
        return vazia
    if ultima_404 is not None:
        raise LookupError(f"Nenhuma arte HD encontrada para {codigo} (PokéAPI: {nome}).")
    return vazia


def validar_png_hd(conteudo: bytes) -> tuple[int, int]:
    if len(conteudo) > LIMITE_BYTES or len(conteudo) < 45 or not conteudo.startswith(PNG_ASSINATURA):
        raise ValueError("Arquivo não é um PNG válido ou excede 8 MB.")
    if conteudo[12:16] != b"IHDR" or struct.unpack(">I", conteudo[8:12])[0] != 13:
        raise ValueError("Cabeçalho PNG inválido.")
    largura, altura = struct.unpack(">II", conteudo[16:24])
    if min(largura, altura) < MINIMO_RESOLUCAO or max(largura, altura) > 4096:
        raise ValueError(f"Resolução {largura}x{altura} insuficiente ou inesperada.")
    if not conteudo.endswith(b"IEND\xaeB`\x82"):
        raise ValueError("PNG incompleto.")
    return largura, altura


def baixar_arte_hd(url: str) -> bytes:
    if not url_arte_confiavel(url):
        raise ValueError("Fonte de imagem não permitida.")
    conteudo = _ler(url)
    if extensao_arte_hd(conteudo) == "png":
        validar_png_hd(conteudo)
    else:
        validar_webp_hd(conteudo)
    return conteudo


def validar_webp_hd(conteudo: bytes) -> tuple[int, int]:
    """Verifica contêiner RIFF e dimensões WebP (VP8, VP8L ou VP8X)."""
    if (len(conteudo) < 30 or len(conteudo) > LIMITE_BYTES
            or conteudo[:4] != b"RIFF" or conteudo[8:12] != WEBP_ASSINATURA):
        raise ValueError("Arquivo não é um WebP válido ou excede 8 MB.")
    if int.from_bytes(conteudo[4:8], "little") + 8 != len(conteudo):
        raise ValueError("WebP truncado ou comprimento inválido.")
    tipo = conteudo[12:16]
    if tipo == b"VP8X":
        largura = int.from_bytes(conteudo[24:27], "little") + 1
        altura = int.from_bytes(conteudo[27:30], "little") + 1
    elif tipo == b"VP8L" and len(conteudo) >= 25 and conteudo[20] == 0x2F:
        a, b, c, d = conteudo[21:25]
        largura = 1 + a + ((b & 0x3F) << 8)
        altura = 1 + (b >> 6) + (c << 2) + ((d & 0x0F) << 10)
    elif tipo == b"VP8 " and len(conteudo) >= 30 and conteudo[23:26] == b"\x9d\x01\x2a":
        largura = int.from_bytes(conteudo[26:28], "little") & 0x3FFF
        altura = int.from_bytes(conteudo[28:30], "little") & 0x3FFF
    else:
        raise ValueError("Cabeçalho WebP inválido ou formato não reconhecido.")
    if min(largura, altura) < MINIMO_RESOLUCAO or max(largura, altura) > 4096:
        raise ValueError(f"Resolução WebP {largura}x{altura} insuficiente ou inesperada.")
    return largura, altura


def extensao_arte_hd(conteudo: bytes) -> str:
    if conteudo.startswith(PNG_ASSINATURA):
        return "png"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == WEBP_ASSINATURA:
        return "webp"
    raise ValueError("Imagem recebida não é PNG nem WebP.")
