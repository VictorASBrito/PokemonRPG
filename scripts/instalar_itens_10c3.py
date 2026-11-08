"""Instala integração dos efeitos terapêuticos e visualização estática do mapa.
Não executa migrations, não acessa DB nem remove imagens; cria backups .bak-10c3.
"""
from __future__ import annotations
import argparse
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MARCADOR = 'ANKAR_10C3_CURA'


def trocar_unico(s: str, antigo: str, novo: str, caminho: str) -> str:
    if novo in s: return s
    if s.count(antigo) != 1:
        raise RuntimeError(f'Âncora não encontrada/ambígua em {caminho}. Nenhuma gravação realizada. ({s.count(antigo)})')
    return s.replace(antigo, novo, 1)


def preparar(origem: Path) -> dict[Path,str]:
    caminhos=['app/services/inventario_service.py','app/routes/inventario.py','templates/jogador/inventario.html']
    arquivos={p:(origem/p).read_text(encoding='utf-8') for p in caminhos}
    result={}
    p=caminhos[0];s=arquivos[p]
    if MARCADOR not in s:
        inicio=s.index('def usar_item_consumivel(')
        fim=s.index('\ndef equipar_item_pokemon(',inicio)
        trecho=s[inicio:fim]
        trecho=trocar_unico(trecho,'    quantidade: Any = 1,\n','    quantidade: Any = 1,\n    pokemon_id: str | uuid.UUID | None = None,\n',p)
        trecho=trocar_unico(trecho,'    registro = _registro_inventario(personagem.id, item.id, bloquear=True)\n    antes = _snapshot_registro(registro)\n',
'''    # ANKAR_10C3_CURA — confirma o alvo e aplica cura/status antes do consumo.
    from app.services.efeitos_itens_10c3 import exige_alvo_pokemon, aplicar_efeitos_terapeuticos
    registro = _registro_inventario(personagem.id, item.id, bloquear=True)
    if registro is None or registro.quantidade < quantidade_int:
        raise ValueError(f"Quantidade insuficiente de {item.nome} no inventário.")
    resultado_terapia = None
    if exige_alvo_pokemon(item):
        resultado_terapia = aplicar_efeitos_terapeuticos(
            item=item, personagem=personagem, pokemon_id=pokemon_id, quantidade=quantidade_int
        )
    antes = _snapshot_registro(registro)
''',p)
        trecho=trocar_unico(trecho, '            "efeitos": item.efeitos,\n',
                                   '            "efeitos": item.efeitos,\n            "efeitos_aplicados": resultado_terapia,\n',p)
        s=s[:inicio]+trecho+s[fim:]
    result[origem/p]=s
    p=caminhos[1];s=arquivos[p]
    if MARCADOR not in s:
        s=trocar_unico(s,'from app.services.inventario_apresentacao import BOLSAS, VERSAO_INTERFACE, preparar_equipe, preparar_itens',
                       'from app.services.inventario_apresentacao import BOLSAS, VERSAO_INTERFACE, preparar_equipe, preparar_itens\nfrom app.services.efeitos_itens_10c3 import exige_alvo_pokemon  # ANKAR_10C3_CURA',p)
        s=trocar_unico(s,'        bolsas=BOLSAS,\n','        bolsas=BOLSAS,\n        item_exige_pokemon=exige_alvo_pokemon,\n',p)
        s=trocar_unico(s,'        quantidade=request.form.get("quantidade", 1),\n',
                       '        quantidade=request.form.get("quantidade", 1),\n        pokemon_id=request.form.get("pokemon_id"),\n',p)
    result[origem/p]=s
    p=caminhos[2];s=arquivos[p]
    if MARCADOR not in s:
        s=trocar_unico(s,'{% block estilos_finais %}',
                       '{% block estilos_finais %}\n{# ANKAR_10C3_CURA #}\n<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/efeitos-itens-10c3.css\') }}">',p)
        needle='                                <button type="submit" class="inventario-nds-acao">Usar</button>'
        trecho='''                                {% if item_exige_pokemon(item) %}
                                <label>Aplicar em Pokémon
                                    <select name="pokemon_id" required>
                                        <option value="">Selecione o Pokémon</option>
                                        {% for p in contexto.pokemons if p.ativo %}
                                        <option value="{{ p.id }}">{{ p.apelido or p.forma_pokemon.nome }} — {{ p.pv_atual }} PV</option>
                                        {% endfor %}
                                    </select>
                                </label>
                                {% endif %}
'''+needle
        s=trocar_unico(s,needle,trecho,p)
        # Static map viewer reuses the already-shipped Ankar image, no clickable overlay.
        search='                        <p class="inventario-nds-item-descricao">{{ item.descricao or \'Sem descrição cadastrada.\' }}</p>'
        map_card='''                        <p class="inventario-nds-item-descricao">{{ item.descricao or 'Sem descrição cadastrada.' }}</p>
                        {% if item.codigo == 'mapa-da-regiao-de-ankar' %}
                        <button type="button" class="inventario-nds-acao inventario-mapa-botao" onclick="document.getElementById('inventario-mapa-estatico').showModal()">Ver mapa da Região de Ankar</button>
                        {% endif %}'''
        s=trocar_unico(s,search,map_card,p)
        # insert dialog before script block, outside hidden article and inventory container
        needle='{% endblock %}\n{% block scripts %}'
        modal='''<dialog id="inventario-mapa-estatico" class="inventario-mapa-dialogo" aria-label="Mapa da Região de Ankar">
  <form method="dialog"><button type="submit" class="botao botao-secundario">Fechar mapa</button></form>
  <img src="{{ url_for('static', filename='img/ankar-mapa.jpg') }}" alt="Mapa completo da Região de Ankar" loading="lazy">
</dialog>
'''+needle
        s=trocar_unico(s,needle,modal,p)
        antigo='O botão Usar registra o consumo no inventário. Efeitos sobre PV são resolvidos pelas regras da campanha.'
        if antigo in s:
            s=s.replace(antigo,'O uso de itens configurados para cura recupera PV ou remove condições do Pokémon selecionado. O consumo e a cura acontecem juntos.',1)
    result[origem/p]=s
    return result


def instalar(raiz=RAIZ):
    raiz=Path(raiz)
    planos=preparar(raiz)  # preflight: no files written if an anchor is missing
    # Regressão antiga: Baga Laranja passou a exigir escolha de alvo no consumo.
    teste=raiz/'tests/test_itens_inventario.py'
    if teste.exists():
        velho=teste.read_text(encoding='utf-8')
        antigo='        data={"item_id": item_id, "quantidade": "1"},'
        novo='        data={"item_id": item_id, "pokemon_id": pokemon_id, "quantidade": "1"},'
        if antigo in velho and novo not in velho:
            assert velho.count(antigo)==1, 'Uso em teste com alvo ambíguo; revise testes/test_itens_inventario.py'
            planos[teste]=velho.replace(antigo,novo,1)
    mudados=[]
    for caminho,novo in planos.items():
        original=caminho.read_text(encoding='utf-8')
        if original==novo: continue
        backup=caminho.with_name(caminho.name+'.bak-10c3')
        if not backup.exists():backup.write_text(original,encoding='utf-8')
        caminho.write_text(novo,encoding='utf-8')
        mudados.append(caminho.relative_to(raiz).as_posix())
    return mudados

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raiz',default=str(RAIZ));args=p.parse_args()
    print('Atualizados:',instalar(Path(args.raiz)))
