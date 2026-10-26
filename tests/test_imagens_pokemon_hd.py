"""Qualidade de arte Pokémon e sincronização sem rede nos testes."""
from __future__ import annotations

import json
import struct
import uuid
import zlib

from sqlalchemy import select

from app.extensions import db
from app.models.db import FormaPokemon
from app.services import imagens_pokemon_hd as artes


def _png_rgba(largura=512, altura=512):
    def bloco(nome, conteudo):
        return (struct.pack('>I', len(conteudo)) + nome + conteudo
                + struct.pack('>I', zlib.crc32(nome + conteudo) & 0xffffffff))
    cabecalho = struct.pack('>IIBBBBB', largura, altura, 8, 6, 0, 0, 0)
    scanline = b'\0' + (b'\0\0\0\0' * largura)
    return (artes.PNG_ASSINATURA + bloco(b'IHDR', cabecalho)
            + bloco(b'IDAT', zlib.compress(scanline * altura, level=6))
            + bloco(b'IEND', b''))


def test_avaliacao_da_origem_preserva_uploads_e_artes_personalizadas():
    assert artes.imagem_do_catalogo_padrao('https://img.pokemondb.net/sprites/home/normal/bulbasaur.png')
    assert not artes.imagem_do_catalogo_padrao('/static/uploads/pokemons/meu-pokemon.png')
    assert not artes.imagem_do_catalogo_padrao('https://exemplo.com/meu-pokemon.png')
    assert artes.url_arte_confiavel(
        'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/1.png'
    )
    assert not artes.url_arte_confiavel('https://exemplo.com/imagem.png')


def test_validacao_eh_mais_exigente_que_arquivo_png_pequeno():
    assert artes.validar_png_hd(_png_rgba()) == (512, 512)
    import pytest
    with pytest.raises(ValueError, match='Resolução'):
        artes.validar_png_hd(_png_rgba(96, 96))
    with pytest.raises(ValueError, match='PNG'):
        artes.validar_png_hd(b'<html>erro</html>')


def test_busca_artes_home_na_forma_exata(monkeypatch):
    endereco_home = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/6.png'
    chamadas = []
    def ler(url, **_kwargs):
        chamadas.append(url)
        return json.dumps({'sprites': {'other': {'home': {'front_default': endereco_home}}}}).encode()
    monkeypatch.setattr(artes, '_ler', ler)
    resultado = artes.procurar_artes_hd('charizard-mega-x')
    assert resultado.normal == endereco_home
    assert resultado.shiny is None
    assert chamadas[0].endswith('/charizard-mega-x')


def test_comando_simula_por_padrao_e_aplica_sem_afetar_outros(app_db, monkeypatch, tmp_path):
    import app.commands.midia as midia
    caminho_static_teste = tmp_path / 'static'
    caminho_static_teste.mkdir()
    monkeypatch.setattr(app_db, 'static_folder', str(caminho_static_teste))
    comeco = 'https://img.pokemondb.net/sprites/home/normal/bulbasaur.png'
    comeco_shiny = 'https://img.pokemondb.net/sprites/home/shiny/bulbasaur.png'
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'bulbasaur')).scalar_one()
        forma.imagem_url, forma.imagem_shiny_url = comeco, comeco_shiny
        db.session.commit()
    runner = app_db.test_cli_runner()
    simulacao = runner.invoke(args=['midia', 'pokemon-hd', '--codigo', 'bulbasaur'])
    assert simulacao.exit_code == 0, simulacao.output
    assert 'SIMULAR: bulbasaur' in simulacao.output
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'bulbasaur')).scalar_one()
        assert forma.imagem_url == comeco

    url_hd = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/1.png'
    monkeypatch.setattr(midia, 'procurar_artes_hd', lambda _codigo: artes.ArteHD(url_hd, url_hd))
    monkeypatch.setattr(midia, 'baixar_arte_hd', lambda _url: _png_rgba())
    resultado = runner.invoke(args=['midia', 'pokemon-hd', '--codigo', 'bulbasaur', '--aplicar'])
    assert resultado.exit_code == 0, resultado.output
    assert 'ATUALIZADO: bulbasaur' in resultado.output
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'bulbasaur')).scalar_one()
        assert forma.imagem_url == '/static/img/pokemon-hd/bulbasaur.png'
        assert forma.imagem_shiny_url == '/static/img/pokemon-hd/bulbasaur-shiny.png'
    assert (caminho_static_teste / 'img/pokemon-hd/bulbasaur.png').exists()
    assert (caminho_static_teste / 'img/pokemon-hd/historico-sincronizacao.jsonl').exists()


def test_aliases_especiais_preservam_formas_distintas():
    assert artes.codigo_pokeapi('basculin-azul') == 'basculin-blue-striped'
    assert artes.codigo_pokeapi('rotom-geladeira') == 'rotom-frost'
    assert artes.codigo_pokeapi('aegislash-escudo') == 'aegislash-shield'
    assert artes.codigo_pokeapi('arceus-agua') == 'arceus-water'
    assert artes.codigo_pokeapi('arceus-noturno') == 'arceus-dark'
    assert artes.codigo_pokeapi('nidoran') == 'nidoran-f'
    assert artes.codigo_pokeapi('nidoran-2') == 'nidoran-m'
    assert artes.codigo_pokeapi('minior-nucleo') == 'minior-nucleo'  # ambíguo: sem inventar cor


def test_404_pokemon_recuperado_por_pokemon_form(monkeypatch):
    from urllib.error import HTTPError
    chamadas = []
    url = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/10041.png'
    def ler(endereco, **_kwargs):
        chamadas.append(endereco)
        if '/pokemon/' in endereco and '/pokemon-form/' not in endereco:
            raise HTTPError(endereco, 404, 'Not Found', None, None)
        return json.dumps({'sprites': {'other': {'home': {'front_default': url}}}}).encode()
    monkeypatch.setattr(artes, '_ler', ler)
    resultado = artes.procurar_artes_hd('arceus-inseto')
    assert resultado.normal == url
    assert chamadas[0].endswith('/pokemon/arceus-bug')
    assert chamadas[1].endswith('/pokemon-form/arceus-bug')


def test_timeout_repetido_apos_erro_transitorio(monkeypatch):
    from io import BytesIO
    class FakeResponse:
        def __init__(self, conteudo):
            self._arquivo = BytesIO(conteudo)
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def read(self, n): return self._arquivo.read(n)
    chamadas = []
    def abrir(_request, timeout):
        chamadas.append(timeout)
        if len(chamadas) < 3:
            raise TimeoutError('temporario')
        return FakeResponse(b'ok')
    monkeypatch.setattr(artes, 'urlopen', abrir)
    monkeypatch.setattr(artes.time, 'sleep', lambda _seg: None)
    assert artes._ler('https://pokeapi.co/api/v2/pokemon/beautifly') == b'ok'
    assert len(chamadas) == 3


def test_busca_mew_permita_resposta_de_api_maior(monkeypatch):
    limites = []
    def ler(_url, *, max_bytes, **_kwargs):
        limites.append(max_bytes)
        return json.dumps({'sprites': {'other': {'home': {'front_default':
            'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/151.png'
        }}}}).encode()
    monkeypatch.setattr(artes, '_ler', ler)
    assert artes.procurar_artes_hd('mew').normal is not None
    assert limites == [artes.LIMITE_API_BYTES]
    assert artes.LIMITE_API_BYTES > 450_000


def test_comando_salva_normal_mesmo_se_shiny_falhar(app_db, monkeypatch, tmp_path):
    import app.commands.midia as midia
    static = tmp_path / 'static'
    static.mkdir()
    monkeypatch.setattr(app_db, 'static_folder', str(static))
    normal = 'https://img.pokemondb.net/sprites/home/normal/bulbasaur.png'
    shiny = 'https://img.pokemondb.net/sprites/home/shiny/bulbasaur.png'
    fonte_normal = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/1.png'
    fonte_shiny = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/shiny/1.png'
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'bulbasaur')).scalar_one()
        forma.imagem_url, forma.imagem_shiny_url = normal, shiny
        db.session.commit()
    monkeypatch.setattr(midia, 'procurar_artes_hd', lambda _c: artes.ArteHD(fonte_normal, fonte_shiny))
    def download(url):
        if url == fonte_shiny:
            raise OSError('shiny indisponivel')
        return _png_rgba()
    monkeypatch.setattr(midia, 'baixar_arte_hd', download)
    runner = app_db.test_cli_runner()
    resultado = runner.invoke(args=['midia', 'pokemon-hd', '--aplicar', '--codigo', 'bulbasaur'])
    assert resultado.exit_code == 0, resultado.output
    assert 'PARCIAL: bulbasaur' in resultado.output
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'bulbasaur')).scalar_one()
        assert forma.imagem_url.startswith('/static/img/pokemon-hd/')
        assert forma.imagem_shiny_url == shiny
    assert (static / 'img/pokemon-hd/relatorio-ultima-sincronizacao.json').exists()

    # A execução seguinte não baixa a imagem normal que já foi atualizada.
    monkeypatch.setattr(midia, 'baixar_arte_hd', lambda _url: _png_rgba())
    proxima = runner.invoke(args=['midia', 'pokemon-hd', '--aplicar', '--codigo', 'bulbasaur'])
    assert proxima.exit_code == 0, proxima.output
    assert 'ATUALIZADO: bulbasaur — imagem_shiny_url' in proxima.output
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'bulbasaur')).scalar_one()
        assert forma.imagem_shiny_url.endswith('/bulbasaur-shiny.png')


def test_arvore_artes_oficial_como_reserva_do_home():
    home = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/25.png'
    oficial = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png'
    resultado = artes._primeiras_artes({'sprites': {'other': {
        'home': {'front_default': home}, 'official-artwork': {'front_default': oficial}
    }}})
    assert resultado.candidatas('normal') == (home, oficial)
    assert resultado.candidatas('shiny') == ()


def test_comando_usa_arte_reserva_se_home_404(app_db, monkeypatch, tmp_path):
    import app.commands.midia as midia
    static = tmp_path / 'static'
    static.mkdir()
    monkeypatch.setattr(app_db, 'static_folder', str(static))
    inicio = 'https://img.pokemondb.net/sprites/home/normal/bulbasaur.png'
    home = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/1.png'
    arte = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png'
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'bulbasaur')).scalar_one()
        forma.imagem_url, forma.imagem_shiny_url = inicio, '/static/uploads/meu-shiny.png'
        db.session.commit()
    monkeypatch.setattr(midia, 'procurar_artes_hd', lambda _c: artes.ArteHD(home, None, (arte,)))
    tentativas = []
    def baixar(url):
        tentativas.append(url)
        if url == home:
            raise OSError('404')
        return _png_rgba()
    monkeypatch.setattr(midia, 'baixar_arte_hd', baixar)
    runner = app_db.test_cli_runner()
    resp = runner.invoke(args=['midia', 'pokemon-hd', '--aplicar', '--codigo', 'bulbasaur'])
    assert resp.exit_code == 0, resp.output
    assert tentativas == [home, arte]
    with app_db.app_context():
        forma = db.session.execute(select(FormaPokemon).where(FormaPokemon.codigo == 'bulbasaur')).scalar_one()
        assert forma.imagem_url.endswith('/bulbasaur.png')
        assert forma.imagem_shiny_url == '/static/uploads/meu-shiny.png'


def test_ultimos_pendentes_possuem_candidatos_hd_alternativos(monkeypatch):
    """Consultas podem devolver sprites vazios, mas IDs exatos dão alternativas."""
    import app.services.imagens_pokemon_hd as hd
    monkeypatch.setattr(hd, '_ler', lambda *_args, **_kwargs: b'{"sprites":{}}')
    for codigo, numero in (
        ('frillish', 592), ('jellicent', 593), ('pyroar', 668),
        ('zacian-heroi', 888), ('zamazenta-heroi', 889),
    ):
        arte = hd.procurar_artes_hd(codigo)
        assert any(f'/{numero}.png' in url for url in arte.candidatas('normal'))
        assert any(f'/{numero}.webp' in url for url in arte.candidatas('shiny'))
        assert all(hd.url_arte_confiavel(url) for url in
                   arte.candidatas('normal') + arte.candidatas('shiny'))


def test_sprites_hd_webp_sao_candidatos_secundarios():
    from app.services import imagens_pokemon_hd as hd
    prefixo = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/'
    casa = prefixo + 'other/home/592.png'
    outra = prefixo + 'versions/generation-viii/sword-shield/592.webp'
    brilho = prefixo + 'versions/generation-viii/sword-shield/shiny/592.webp'
    dados = {'sprites': {
        'other': {'home': {'front_default': casa}},
        'versions': {'generation-viii': {'sword-shield': {
            'front_default': outra, 'front_shiny': brilho,
        }}},
    }}
    resultado = hd._primeiras_artes(dados)
    assert resultado.candidatas('normal') == (casa, outra)
    assert resultado.candidatas('shiny') == (brilho,)
    assert hd.url_arte_confiavel(brilho)


def test_webp_512_valida_e_rejeita_resolucao_baixa():
    from app.services import imagens_pokemon_hd as hd
    def webp_vp8x(width, height):
        payload = (b'VP8X' + (10).to_bytes(4, 'little')
                   + b'\x00' * 4 + (width-1).to_bytes(3, 'little')
                   + (height-1).to_bytes(3, 'little'))
        return b'RIFF' + (4 + len(payload)).to_bytes(4, 'little') + b'WEBP' + payload
    img = webp_vp8x(512, 512)
    assert hd.validar_webp_hd(img) == (512, 512)
    assert hd.extensao_arte_hd(img) == 'webp'
    import pytest
    with pytest.raises(ValueError, match='Resolução'):
        hd.validar_webp_hd(webp_vp8x(96, 96))
    with pytest.raises(ValueError, match='truncado'):
        hd.validar_webp_hd(img + b'erro')


def test_arte_representativa_exige_opt_in(monkeypatch):
    import pytest
    import app.services.imagens_pokemon_hd as hd
    requisicoes = []
    def ler(url, **_kwargs):
        requisicoes.append(url)
        if url.endswith('/minior-nucleo'):
            from urllib.error import HTTPError
            raise HTTPError(url, 404, 'Not Found', None, None)
        if url.endswith('/minior-red'):
            return b'{"id":10136,"sprites":{}}'
        return b'{"sprites":{}}'
    monkeypatch.setattr(hd, '_ler', ler)
    assert hd.codigo_pokeapi('minior-nucleo') == 'minior-nucleo'
    assert hd.codigo_pokeapi('minior-nucleo', representativas=True) == 'minior-red'
    with pytest.raises(LookupError):
        hd.procurar_artes_hd('minior-nucleo')
    vermelho = hd.procurar_artes_hd('minior-nucleo', representativas=True)
    assert '/10136.' in vermelho.normal
    assert '/10136.' in vermelho.shiny
    assert any(url.endswith('/minior-red') for url in requisicoes)
    assert hd.procurar_artes_hd('eevee-parceiro', representativas=True).shiny.endswith('/shiny/133.png')
    assert hd.procurar_artes_hd('pikachu-parceiro', representativas=True).shiny.endswith('/shiny/25.png')
