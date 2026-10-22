"""Contrato da grade de seis cartões com quatro posições de golpes.

A renderização destes testes é independente do PostgreSQL; serve para prevenir
regressões visuais quando o catálogo retornar 0, 1 ou 4 golpes equipados.
"""

from pathlib import Path

from html.parser import HTMLParser
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]

class _EstruturaCartoes(HTMLParser):
    """Conta os slots dentro de cada cartão, sem dependências de testes novas."""

    def __init__(self):
        super().__init__()
        self.cartoes = []
        self.atual = None
        self.espacos_livres = 0

    def handle_starttag(self, tag, atributos):
        atributos = dict(atributos)
        classes = atributos.get("class", "").split()
        if "pokemon-dashboard-vazio" in classes:
            self.espacos_livres += 1
        if tag == "article" and "data-dashboard-pokemon-card" in atributos:
            self.atual = {"compactos": 0, "detalhados": 0,
                          "vazios_compactos": 0, "vazios_detalhados": 0,
                          "mensagens": 0}
            self.cartoes.append(self.atual)
        if self.atual is None or tag != "div":
            return
        if "golpe-dashboard-preenchido" in classes or "golpe-dashboard-vazio" in classes:
            self.atual["compactos"] += 1
        if "pokemon-dashboard-golpe-detalhado" in classes:
            self.atual["detalhados"] += 1
        if "golpe-dashboard-vazio" in classes:
            self.atual["vazios_compactos"] += 1
        if "pokemon-dashboard-golpe-vazio" in classes:
            self.atual["vazios_detalhados"] += 1

    def handle_data(self, data):
        if self.atual is not None and data.strip() == "Sem golpe definido":
            self.atual["mensagens"] += 1

    def handle_endtag(self, tag):
        if tag == "article":
            self.atual = None



def _renderizar_dashboard():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"))
    base = {"pv": 49, "ataque": 13, "defesa": 6, "ataque_especial": 9,
            "defesa_especial": 11, "velocidade": 6}
    golpes = [
        {"nome": f"Golpe {i+1}", "dano": "4d6", "tipo": "Fogo",
         "categoria": "Físico", "precisao_texto": "100%", "prioridade": 0}
        for i in range(4)
    ]
    equipe = []
    for numero, quantidade in enumerate((0, 1, 4)):
        equipe.append({
            "pokemon": {"id": str(numero), "apelido": f"Pokémon {numero}", "pv_atual": 100},
            "especie": {"nome": f"Espécie {numero}", "tipos": ["Fogo"],
                        "imagem": "/teste.png"},
            "calculos": {"totais": {**base, "pv": 100}, "bases": base,
                         "nivel": 50, "golpes": golpes[:quantidade]},
        })

    html = env.get_template("jogador/dashboard.html").render(
        treinador={"nome": "Teste", "pv_atual": 10, "pv_maximo": 10,
                   "nivel": 50, "atributos": {}},
        nome_jogador="Jogador", equipe=equipe, limite_equipe=6,
        atributos_config=[{"id": "fisico", "nome": "Físico"}],
        session={"usuario_id": "teste", "nome": "Jogador", "perfil": "jogador"},
        url_for=lambda *_args, **_kwargs: "/teste",
        get_flashed_messages=lambda **_kwargs: [],
    )
    estrutura = _EstruturaCartoes()
    estrutura.feed(html)
    return estrutura


def test_quatro_slots_por_pokemon_com_placeholders_corretos():
    html = _renderizar_dashboard()
    assert len(html.cartoes) == 3

    for card, quantidade in zip(html.cartoes, (0, 1, 4)):
        assert card["compactos"] == 4
        assert card["detalhados"] == 4
        assert card["vazios_compactos"] == 4 - quantidade
        assert card["vazios_detalhados"] == 4 - quantidade
        assert card["mensagens"] == 2 * (4 - quantidade)

    assert html.espacos_livres == 3


def test_duas_fileiras_e_areas_internas_ocupam_altura_uniforme():
    css = (ROOT / "static" / "css" / "dashboard.css").read_text(encoding="utf-8")
    assert "Grade uniforme até o limite inferior da ficha do treinador" in css
    assert "grid-template-rows: repeat(2, minmax(0, 1fr))" in css
    assert "grid-template-rows: repeat(4, minmax(0, 1fr))" in css
    assert ".golpes-pokemon-dashboard > .golpe-dashboard-vazio" in css
    assert "body:not(.dashboard-foco-aberto)" in css
