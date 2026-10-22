"""Cobertura das fichas Excel recebidas para os participantes de Ankar."""
from app.commands.planilhas_jogadores import carregar_fichas, normalizar


def test_nove_jogadores_e_senhas_temporarias():
    pacote = carregar_fichas()
    assert pacote["campanha"] == "ankar"
    assert pacote["senha_padrao"] == "12345"
    assert {p["login"] for p in pacote["jogadores"]} == {
        "tuts", "manu", "braz", "jao", "nanda", "lucas", "jare", "vini", "mari",
    }


def test_niveis_atributos_e_estruturas_das_fichas():
    pacote = carregar_fichas()
    for player in pacote["jogadores"]:
        assert player["personagem"]["nivel"] > 0
        assert len(player["equipe"]) <= 6
        assert len(player["box"]) <= 100
        assert set(player["personagem"]["atributos"]) == {
            "fisico", "destreza", "saude", "conhecimento", "comunicacao", "espirito"
        }
        assert all(len(p["golpes"]) <= 4 for p in player["equipe"] + player["box"])
    assert sum(len(j["equipe"]) for j in pacote["jogadores"]) == 54
    assert sum(len(j["box"]) for j in pacote["jogadores"]) == 155


def test_normalizacao_portuguesa_sem_misturar_especies():
    assert normalizar("Jão") == "jao"
    assert normalizar("Ás dos Ares") == normalizar("As Dos Ares")
    assert normalizar("Sandslash (Alola)") != normalizar("Sandslash")


def test_revisoes_confirmadas_pelo_mestre_antes_da_importacao():
    jogadores = {j["login"]: j for j in carregar_fichas()["jogadores"]}
    # Scolipede foi identificado pelo mestre; "Mega?" é a referência da lore
    # na planilha, não uma forma que deve ser criada no catálogo.
    primeiro = jogadores["jao"]["equipe"][0]
    assert primeiro["especie"] == "Scolipede"
    assert primeiro["identificacao_origem"] == "Mega?"
    assert primeiro["apelido"] == "Yoda"
    assert primeiro["natureza"] == "Valente"
    assert primeiro["pv_atual"] == 138
    assert primeiro["golpes"] == [
        "Venochoque", "Terremoto", "Deslize De Pedras", "Megachifre",
    ]

    assert jogadores["manu"]["personagem"]["numeros_shiny"] == [
        1, 12, 20, 26, 37, 45, 60, 80, 82, 100,
    ]
    assert jogadores["vini"]["personagem"]["numeros_shiny"] == [
        4, 75, 14, 36, 97, 5, 35, 42, 76, 17,
    ]
    for login in ("manu", "vini"):
        assert len(set(jogadores[login]["personagem"]["numeros_shiny"])) == 10
        assert all(1 <= n <= 100 for n in jogadores[login]["personagem"]["numeros_shiny"])
        assert not any(
            "número shiny" in aviso.casefold()
            for aviso in jogadores[login].get("avisos", [])
        )

    # Pedido explícito do mestre: manter os PV informados por Mari.
    mari = jogadores["mari"]
    assert mari["personagem"]["pv_atual"] == 30
    assert any("30/24" in aviso for aviso in mari.get("avisos", []))


def test_naturezas_corrigidas_na_ordem_das_boxes_e_shiny_preservado():
    jogadores = {j["login"]: j for j in carregar_fichas()["jogadores"]}
    listas = {
        "braz": [
            "Quieto", "Peculiar", "Tímido", "Inflexível", "Quieto", "Gentil",
        ],
        "nanda": [
            "Calmo", "Inflexível", "Relaxado", "Inflexível", "Tímido", "Valente",
            "Atrevido", "Cuidadoso", "Calmo", "Inflexível", "Corajoso", "Tímido",
            "Ousado", "Desobediente", "Relaxado", "Inflexível", "Modesto",
            "Desobediente", "Corajoso", "Precipitado",
        ],
        "lucas": [
            "Reservado", "Descuidado", "Moderado", "Dócil", "Relaxado",
            "Desobediente", "Descuidado", "Dócil", "Quieto", "Inflexível",
            "Relaxado", "Calmo",
        ],
        "vini": [
            "Ingênuo", "Inflexível", "Atrevido", "Apressado", "Tímido",
            "Gentil", "Cuidadoso", "Ousado", "Sério", "Ingênuo",
            "Corajoso", "Modesto",
        ],
    }
    for login, naturezas in listas.items():
        box = jogadores[login]["box"]
        assert [p["natureza"] for p in box] == naturezas
        assert all(p["natureza"] not in {"Comum", "Shiny"} for p in box)

    assert [p["especie"] for p in jogadores["nanda"]["box"] if p["shiny"]] == [
        "Axew", "Prinplup", "Simipour",
    ]
    assert [p["especie"] for p in jogadores["lucas"]["box"] if p["shiny"]] == ["Corsola"]
    assert not any(p["shiny"] for p in jogadores["braz"]["box"])
    assert not any(p["shiny"] for p in jogadores["vini"]["box"])


def test_bulbasaur_vinculo_sera_forma_independente_sem_sobrescrever_a_normal():
    pacote = carregar_fichas()
    forma = pacote["formas_personalizadas"]["Bulbasaur (Vínculo)"]
    assert forma["especie"] == "Bulbasaur"
    assert forma["categoria"] == "personalizada"
    assert forma["tipos"] == ["Grama", "Veneno"]
    assert forma["atributos_base"] == {
        "pv": 70, "ataque": 9, "defesa": 9, "ataque_especial": 12,
        "defesa_especial": 11, "velocidade": 9,
    }
    assert forma["imagem_url"] == forma["imagem_shiny_url"]
    assert forma["imagem_url"].startswith("https://raw.githubusercontent.com/")
    assert forma["dados_adicionais_originais"] == ["236", "6%"]
    jogadores = {j["login"]: j for j in pacote["jogadores"]}
    assert any(p["especie"] == "Bulbasaur (Vínculo)" for p in jogadores["manu"]["equipe"])


def test_mari_vai_importar_com_trinta_de_trinta_pv():
    jogadores = {j["login"]: j for j in carregar_fichas()["jogadores"]}
    mari = jogadores["mari"]
    assert mari["personagem"]["pv_atual"] == 30
    assert mari["personagem"]["atributos"]["saude"] == 3
    assert not any("30/24" in aviso for aviso in mari.get("avisos", []))
