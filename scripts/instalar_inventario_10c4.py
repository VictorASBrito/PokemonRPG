"""Etapa 10C.4: uso pela linha do item e seleção visual de Pokémon.

Instalador local idempotente. NÃO altera banco, migrations, inventários ou imagens.
Preflight de todos os arquivos; backups .bak-10c4 são preservados.
Execute na raiz do PokemonRPG: python scripts/instalar_inventario_10c4.py
"""
from __future__ import annotations

from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
MARCADOR = "ANKAR_10C4_USO_LINHA"
CAMINHOS = (
    'templates/jogador/inventario.html',
    'app/services/inventario_service.py',
)


def unico(texto: str, antigo: str, novo: str, caminho: str) -> str:
    if texto.count(antigo) != 1:
        raise RuntimeError(f'{caminho}: âncora esperada 1 vez, encontrada {texto.count(antigo)}: {antigo[:90]!r}')
    return texto.replace(antigo, novo, 1)


def alterar_template(s: str) -> str:
    p = CAMINHOS[0]
    if MARCADOR in s:
        return s

    ancora = '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/inventario.css\', v=versao_inventario) }}">'
    s = unico(s, ancora, ancora + '\n{# ' + MARCADOR + ' #}\n<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/inventario-uso-10c4.css\', v=\'10c4\') }}">', p)

    abertura = '<div id="inventario-nds" class="inventario-nds" data-inventario-versao="{{ versao_inventario }}" data-inventario>'
    formulario = '''
    {# 10C4: POST único, acionado por interação real na lista e na equipe. #}
    <form id="inventario-uso-10c4" data-formulario-uso method="post"
          action="{{ url_for('inventario.usar_mestre', personagem_id=personagem.id) if modo_mestre else url_for('inventario.usar_jogador') }}" hidden>
        <input type="hidden" name="item_id" value="">
        <input type="hidden" name="pokemon_id" value="">
        <input type="hidden" name="quantidade" value="1">
    </form>'''
    s = unico(s, abertura, abertura + formulario, p)

    equipe_inicio = '''        <div class="inventario-nds-equipe-lista">
            {% for registro in equipe_visual %}
            {% set p = registro.pokemon %}
            <article class="inventario-nds-treinador-pokemon">'''
    equipe_novo = '''        <div class="inventario-uso-aviso" data-uso-aviso role="status" aria-live="polite" hidden>
            <span data-uso-mensagem></span>
            <button type="button" data-uso-cancelar>Cancelar</button>
        </div>
        <div class="inventario-nds-equipe-lista">
            {% for registro in equipe_visual %}
            {% set p = registro.pokemon %}
            <article class="inventario-nds-treinador-pokemon"
                     data-pokemon-alvo="{{ p.id }}"
                     data-pv-atual="{{ registro.pv_atual }}"
                     data-pv-maximo="{{ registro.pv_maximo if registro.pv_maximo is not none else '' }}"
                     data-status-ids="{{ p.status_ativos|map(attribute='status_id')|join(',') }}">'''
    s = unico(s, equipe_inicio, equipe_novo, p)

    equipe_fim = '''                    <span class="inventario-nds-treinador-barra"><span style="width:{{ registro.percentual if registro.percentual is not none else 0 }}%"></span></span>
                </span>
            </article>'''
    equipe_fim_novo = '''                    <span class="inventario-nds-treinador-barra"><span style="width:{{ registro.percentual if registro.percentual is not none else 0 }}%"></span></span>
                </span>
                <button class="inventario-uso-alvo" data-selecionar-pokemon="{{ p.id }}" type="button"
                        aria-label="Usar item em {{ p.apelido or p.forma_pokemon.nome }}" hidden disabled>
                    <span>Selecionar</span>
                </button>
            </article>'''
    s = unico(s, equipe_fim, equipe_fim_novo, p)

    item_fim = '''                                <span class="inventario-nds-linha-quantidade">× {{ linha.registro.quantidade }}</span>
                            </button>
                        </div>'''
    item_novo = '''                                <span class="inventario-nds-linha-quantidade">× {{ linha.registro.quantidade }}</span>
                            </button>
                            {% if item.consumivel or item.codigo == 'mapa-da-regiao-de-ankar' or (item.equipavel and contexto.pokemons) %}
                            <span class="inventario-uso-acoes">
                                {% if item.consumivel or item.codigo == 'mapa-da-regiao-de-ankar' %}
                                <button type="button" class="inventario-uso-acao" data-ativar-uso="{{ item.id }}"
                                        data-tipo-uso="{{ 'mapa' if item.codigo == 'mapa-da-regiao-de-ankar' else ('terapia' if item_exige_pokemon(item) else 'registro') }}"
                                        aria-label="Usar {{ item.nome }}">Usar</button>
                                {% endif %}
                                {% if item.equipavel and contexto.pokemons %}
                                <button type="button" class="inventario-uso-acao inventario-uso-acao-equipar" data-equipar-item="{{ item.id }}"
                                        aria-label="Equipar {{ item.nome }}">Equipar</button>
                                {% endif %}
                            </span>
                            {% endif %}
                            <script type="application/json" data-uso-efeitos="{{ item.id }}">{{ item.efeitos|tojson }}</script>
                        </div>'''
    s = unico(s, item_fim, item_novo, p)

    # Painel direito: manter somente informações e transferência.
    do = "                        {% if item.codigo == 'mapa-da-regiao-de-ankar' %}"
    ate = "                            {% if contexto.destinatarios %}"
    if s.count(do) != 1 or s.count(ate) != 1:
        raise RuntimeError('Template: não foi possível localizar início/fim do grupo de efeitos, uso e equipamento.')
    start = s.index(do)
    end = s.index(ate, start)
    s = s[:start] + '''
                        <div class="inventario-nds-operacoes">
''' + s[end:]

    mestre_inicio = '''                            {% if modo_mestre %}
                            <form method="post" action="{{ url_for('inventario.ajustar_mestre', personagem_id=personagem.id) }}" class="inventario-nds-form">'''
    end_master = '''                            {% endif %}
                        </div>

                        {% if item.consumivel %}
                        <p class="inventario-nds-observacao">O uso de itens configurados para cura recupera PV ou remove condições do Pokémon selecionado. O consumo e a cura acontecem juntos.</p>
                        {% endif %}'''
    if s.count(mestre_inicio) != 1 or s.count(end_master) != 1:
        raise RuntimeError('Template: painel de ajuste do mestre ou aviso legado divergente.')
    a = s.index(mestre_inicio)
    b = s.index(end_master, a) + len(end_master)
    s = s[:a] + '''                        </div>''' + s[b:]
    s = unico(s, 'Selecione um item na lista para ver sua descrição, quantidade e ações disponíveis.',
              'Selecione um item para consultar a descrição e, se disponível, transferi-lo.',p)

    area_mestre_fim = '''                </form>
            </details>
        </section>
        {% endif %}
    </section>
</div>'''
    area_mestre_novo = '''                </form>
            </details>
            <details>
                <summary>Gerenciamento do mestre · Ajustar quantidade</summary>
                <form method="post" action="{{ url_for('inventario.ajustar_mestre', personagem_id=personagem.id) }}">
                    <label>Item do inventário
                        <select name="item_id" required>
                            <option value="">Selecione um item</option>
                            {% for registro in contexto.inventario %}
                            <option value="{{ registro.item.id }}">{{ registro.item.nome }} (×{{ registro.quantidade }})</option>
                            {% endfor %}
                        </select>
                    </label>
                    <label>Nova quantidade
                        <input type="number" name="quantidade" min="0" max="999999" value="1" required>
                    </label>
                    <button type="submit" class="inventario-nds-acao">Ajustar</button>
                </form>
            </details>
        </section>
        {% endif %}
    </section>
</div>'''
    s = unico(s, area_mestre_fim, area_mestre_novo, p)

    # Preservar a visualização do mapa anterior; modal adicional para equipar
    # inclusive Pokémon da Box, sem sacrificar essa função ao limpar o painel direito.
    novo_modal = '''{% if contexto.pokemons %}
<dialog id="inventario-equipar-10c4" class="inventario-mapa-dialogo inventario-equipar-dialogo" aria-label="Equipar item em Pokémon">
    <form method="post" action="{{ url_for('inventario.equipar_mestre', personagem_id=personagem.id) if modo_mestre else url_for('inventario.equipar_jogador') }}">
        <h2>Equipar item em Pokémon</h2>
        <input type="hidden" name="item_id" value="">
        <label>Escolha um Pokémon
            <select name="pokemon_id" required>
                <option value="">Selecionar Pokémon</option>
                {% for p in contexto.pokemons %}
                <option value="{{ p.id }}">{{ p.apelido or p.forma_pokemon.nome }}{% if p.item_equipado %} — troca {{ p.item_equipado.nome }}{% endif %}</option>
                {% endfor %}
            </select>
        </label>
        <div class="inventario-equipar-acoes">
            <button type="submit" class="inventario-nds-acao">Equipar</button>
            <button type="button" class="inventario-nds-acao inventario-nds-acao-sec" data-equipar-cancelar>Cancelar</button>
        </div>
    </form>
</dialog>
{% endif %}
'''
    ancora_script = '{% endblock %}\n{% block scripts %}'
    s = unico(s, ancora_script, novo_modal + ancora_script, p)
    js = '<script src="{{ url_for(\'static\', filename=\'js/inventario.js\', v=versao_inventario) }}" defer></script>'
    s = unico(s, js, js + '\n<script src="{{ url_for(\'static\', filename=\'js/inventario-uso-10c4.js\', v=\'10c4\') }}" defer></script>', p)
    return s


def alterar_servico(s: str) -> str:
    p=CAMINHOS[1]
    if '# ANKAR_10C4_STATUS_ALVOS' in s:
        return s
    antiga='''                selectinload(Pokemon.item_equipado).selectinload(Item.categoria),
            )'''
    nova='''                selectinload(Pokemon.item_equipado).selectinload(Item.categoria),
                selectinload(Pokemon.status_ativos),  # ANKAR_10C4_STATUS_ALVOS
            )'''
    return unico(s, antiga, nova, p)


def preparar(raiz: Path) -> dict[Path, str]:
    origem={p:(raiz/p).read_text(encoding='utf-8') for p in CAMINHOS}
    return {
        raiz/CAMINHOS[0]:alterar_template(origem[CAMINHOS[0]]),
        raiz/CAMINHOS[1]:alterar_servico(origem[CAMINHOS[1]]),
    }


def instalar(raiz: Path = RAIZ) -> list[str]:
    raiz=Path(raiz)
    planos=preparar(raiz) # todas as transformações validadas antes de escrever
    mudados=[]
    for path,novo in planos.items():
        antigo=path.read_text(encoding='utf-8')
        if antigo==novo:continue
        bak=path.with_name(path.name+'.bak-10c4')
        if not bak.exists():bak.write_text(antigo,encoding='utf-8')
        path.write_text(novo,encoding='utf-8')
        mudados.append(str(path.relative_to(raiz)))
    return mudados

if __name__=='__main__':
    try:
        mudados=instalar()
    except (RuntimeError,ValueError,FileNotFoundError) as erro:
        print(f'BLOQUEADO (nenhum arquivo original alterado): {erro}',file=sys.stderr)
        raise SystemExit(2)
    print('Etapa 10C.4 instalada. Arquivos modificados:',mudados or '(já instalada)')
    print('Não foi realizada nenhuma alteração no PostgreSQL.')
