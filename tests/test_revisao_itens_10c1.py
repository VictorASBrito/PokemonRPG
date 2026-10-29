from __future__ import annotations
import importlib.util
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[1] / "scripts/revisar_itens_ankar_10c1.py"
spec = importlib.util.spec_from_file_location("revisao_itens", ARQUIVO)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_sinonimos_sem_corrigir_banco():
    assert mod.sugestao("Poke Bolas") == "Poké Bola"
    assert mod.sugestao("Pokéball") == "Poké Bola"
    assert mod.sugestao("GreatBall") == "Grande Bola"
    assert mod.sugestao("Colar Quebrado") == ""
    assert mod.sugestao("Mega pedra") == ""


def test_img_sem_url_e_protecao_diretorio(tmp_path):
    assert mod.status_imagem(None, tmp_path) == "sem imagem"
    assert mod.status_imagem("/static/../fora.png", tmp_path) == "caminho inseguro"
    (tmp_path / "ok.png").write_bytes(b"png")
    assert mod.status_imagem("/static/ok.png", tmp_path) == "local encontrada"
    assert mod.status_imagem("https://example.com/item.png", tmp_path).startswith("externa")


def test_exportacao_pura_sem_escrita_no_banco(tmp_path):
    catalogo = [{"codigo": "bola", "nome": "Poke Bolas", "categoria": "", "preco": 0,
       "consumivel": True, "equipavel": False, "uso_em_batalha": True,
       "ativo": True, "personalizado": False, "imagem_url": "", "inventario_unidades": 4, "equipados": 0}]
    inventarios = [{"login": "teste", "personagem": "Teste", "item_codigo": "bola",
      "nome_item": "Poke Bolas", "categoria": "", "quantidade": 4, "imagem_url": ""},
      {"login": "outro", "personagem": "Outro", "item_codigo": "bola",
      "nome_item": "Pokéball", "categoria": "", "quantidade": 2, "imagem_url": ""}]
    dados = mod.exportar_relatorio(destino=tmp_path, catalogo=catalogo, inventarios=inventarios, origem="teste")
    assert dados["unidades_inventario"] == 6
    assert dados["grupos_para_revisar"] == 1
    assert (tmp_path / "imagens_pendentes.csv").exists()
    assert "NUNCA" in (tmp_path / "LEIA_PRIMEIRO.md").read_text(encoding="utf-8")
    assert len((tmp_path / "modelo_distribuicao.csv").read_text(encoding="utf-8-sig").splitlines()) == 1


def test_registro_documentacao_idempotente(tmp_path):
    (tmp_path/'docs').mkdir()
    for nome in ('CONTINUIDADE_PROJETO.md', 'DIARIO_DESENVOLVIMENTO.md'):
        (tmp_path/'docs'/nome).write_text('CONTEÚDO INTACTO\n',encoding='utf-8')
    (tmp_path/'.gitignore').write_text('*.pyc\n',encoding='utf-8')
    script = ARQUIVO.parent/'registrar_revisao_itens_10c1.py'
    spec = importlib.util.spec_from_file_location('reg10c1',script)
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    assert len(inst.registrar(tmp_path))==3
    assert inst.registrar(tmp_path)==[]
    texto=(tmp_path/'docs/DIARIO_DESENVOLVIMENTO.md').read_text(encoding='utf-8')
    assert texto.count(inst.MARCADOR)==1
    assert texto.startswith('CONTEÚDO INTACTO')
