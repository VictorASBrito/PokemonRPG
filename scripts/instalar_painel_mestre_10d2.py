"""Instalador incremental 10D.2 — baseado no commit 0a157b7.

Não executa migrations ou modifica PostgreSQL. Use --verificar antes de aplicar.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil

MARKER = "ANKAR_10D2_CENTRAL_MESTRE"
ARQUIVOS = [
    "app/routes/mestre.py",
    "app/services/painel_mestre_service.py",
    "templates/mestre/dashboard.html",
    "static/js/painel-mestre.js",
    "templates/base.html",
]


class InstalacaoIncompativel(RuntimeError):
    pass


def trocar(texto: str, antigo: str, novo: str, *, quantos: int = 1) -> str:
    encontrados = texto.count(antigo)
    if encontrados != quantos:
        raise InstalacaoIncompativel(
            f"Esperado(s) {quantos} trecho(s) compatíveis, encontrado(s) {encontrados}: {antigo[:100]!r}"
        )
    return texto.replace(antigo, novo)


def regex_uma(texto: str, padrao: str, transformar) -> str:
    conteudo, total = re.subn(padrao, transformar, texto, count=1, flags=re.S)
    if total != 1:
        raise InstalacaoIncompativel(f"Não foi encontrada a âncora: {padrao[:130]}")
    return conteudo


def alterar_servico(texto: str) -> str:
    return trocar(texto, '                "login": personagem.usuario.login,',
                 '                "login": personagem.usuario.login,\n'
                 '                "perfil": personagem.usuario.perfil,  # ' + MARKER)


def alterar_rotas(texto: str) -> str:
    texto = trocar(texto, 'mestre_bp = Blueprint("mestre", __name__, url_prefix="/mestre")',
                   'from app.services.cura_mestre_10d2 import curar_pokemons_mestre\n'
                   'from app.services.entrada_personagens_service import configuracao_login\n\n'
                   'mestre_bp = Blueprint("mestre", __name__, url_prefix="/mestre")  # ' + MARKER)
    texto = trocar(
        texto,
        '    return render_template(\n        "mestre/dashboard.html",\n        campanha=painel.campanha,',
        '''    # Sprites do seletor de personagens, com fallback neutro. Os caminhos
    # chegam validados pela configuração de entrada, sem controlar o acesso.
    sprites = {slot["login"]: slot["sprite"] for slot in configuracao_login()}
    for jogador in painel.jogadores:
        caminho = sprites.get(str(jogador.get("login", "")).lower())
        jogador["sprite_url"] = url_for(
            "static", filename=caminho or "img/pokebola.png"
        )

    return render_template(
        "mestre/dashboard.html",
        campanha=painel.campanha,''',
    )
    texto = regex_uma(
        texto,
        r'@mestre_bp\.get\("/jogadores"\)\s*@perfil_obrigatorio\("mestre"\)\s*def jogadores\(\):[\s\S]*?(?=def _validar_novo_jogador\()',
        lambda _: '''@mestre_bp.get("/jogadores")
@perfil_obrigatorio("mestre")
def jogadores():
    """A URL antiga continua válida, servindo a central unificada."""
    return dashboard()


''',
    )
    novas_rotas = '''

# ANKAR_10D2_CENTRAL_MESTRE: curas totais limitadas à campanha e ao perfil mestre.
def _curar_painel_10d2(personagem_id=None):
    token = session.get("perfil_csrf", "")
    recebido = request.form.get("csrf_token", "")
    if not token or not recebido or not hmac.compare_digest(token, recebido):
        return jsonify({"erro": "Formulário inválido. Atualize o painel."}), 400
    if request.form.get("confirmar") != "CURAR_POKEMONS":
        return jsonify({"erro": "Confirmação obrigatória para cura total."}), 400
    try:
        resultado = curar_pokemons_mestre(
            campanha_codigo=_campanha_codigo(),
            usuario_id=session.get("usuario_id"),
            personagem_id=personagem_id,
        )
    except ValueError as erro:
        db.session.rollback()
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"erro": str(erro)}), 400
        flash(str(erro), "erro")
        return redirect(url_for("mestre.dashboard"))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Falha ao curar Pokémon pela central do mestre.")
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"erro": "Não foi possível curar os Pokémon."}), 503
        flash("Não foi possível curar os Pokémon.", "erro")
        return redirect(url_for("mestre.dashboard"))

    flash(f"Cura concluída: {resultado['alterados']} Pokémon recuperados e "
          f"{resultado['condicoes_removidas']} condições removidas.", "sucesso")
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(resultado)
    return redirect(url_for("mestre.dashboard"))


@mestre_bp.post("/painel/treinadores/<personagem_id>/curar")
@perfil_obrigatorio("mestre")
def curar_treinador_painel(personagem_id: str):
    return _curar_painel_10d2(personagem_id)


@mestre_bp.post("/painel/curar-todos")
@perfil_obrigatorio("mestre")
def curar_todos_painel():
    return _curar_painel_10d2()
'''
    return texto.rstrip() + novas_rotas


FORM_PV = '''<input type="number" name="quantidade" value="10" min="1" max="9999" step="1" required
                           aria-label="Quantidade de PV a alterar" inputmode="numeric">
                    <button type="submit" data-operacao="menos" title="Reduzir PV" aria-label="Reduzir PV digitado">−</button>
                    <button type="submit" data-operacao="mais" title="Aumentar PV" aria-label="Aumentar PV digitado">+</button>'''


def alterar_template(texto: str) -> str:
    texto = trocar(texto, '{% block estilos %}\n<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/painel-mestre.css\') }}">',
                   '{% block estilos %}\n<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/painel-mestre.css\') }}">\n'
                   '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/painel-mestre-10d2.css\', v=\'10d2\') }}">')
    texto = trocar(texto, '{% block conteudo %}\n', '{% block conteudo %}\n<!-- ' + MARKER + ' -->\n<div class="painel-mestre-central">\n')
    texto = trocar(texto, '{% endblock %}\n\n{% block scripts %}', '</div>\n{% endblock %}\n\n{% block scripts %}')
    # Remove a grade de métricas, não os indicadores contextuais de cada jogador.
    texto = regex_uma(texto,
        r'<section class="painel-mestre-metricas" aria-label="Resumo da campanha">[\s\S]*?</section>\s*(?=<section class="cartao painel-mestre-filtros)',
        lambda _: '')
    texto = trocar(texto,
        '        <a class="botao botao-secundario botao-link" href="{{ url_for(\'catalogo_admin.dashboard\') }}">Catálogo</a>',
        '''        <form method="post" action="{{ url_for('mestre.curar_todos_painel') }}"
              data-cura-10d2 data-cura-global="true">
            <input type="hidden" name="csrf_token" value="{{ nivel_csrf_token }}">
            <input type="hidden" name="confirmar" value="CURAR_POKEMONS">
            <button class="botao botao-curar" type="submit" {% if not jogadores %}disabled{% endif %}>Curar todos os Pokémon</button>
        </form>
        <a class="botao botao-secundario botao-link" href="{{ url_for('catalogo_admin.dashboard') }}">Catálogo</a>''')
    texto = regex_uma(texto, r'\{% if jogador\.get\(\'foto_url\'\) %\}[\s\S]*?\{% endif %\}',
        lambda _: '''<img class="painel-jogador-avatar" src="{{ jogador.get('sprite_url') or url_for('static', filename='img/pokebola.png') }}"
                             alt="" loading="lazy">''')
    # Nível já era editável no cabeçalho: vamos preservá-lo no painel Gerenciar.
    controle = re.search(r'<form method="post" class="formulario-nivel-mestre"[\s\S]*?</form>', texto)
    if not controle or texto.count('class="formulario-nivel-mestre"') != 1:
        raise InstalacaoIncompativel('Controle de nível não encontrado ou ambíguo.')
    formulario_nivel = controle.group(0)
    texto = texto[:controle.start()] + texto[controle.end():]
    texto = trocar(texto,
        '            <div class="painel-jogador-links">\n',
        '''            <div class="painel-jogador-links">
                <form method="post" action="{{ url_for('mestre.curar_treinador_painel', personagem_id=jogador.get('id')) }}" data-cura-10d2>
                    <input type="hidden" name="csrf_token" value="{{ nivel_csrf_token }}">
                    <input type="hidden" name="confirmar" value="CURAR_POKEMONS">
                    <button type="submit" class="botao botao-curar">Curar Pokémon</button>
                </form>
''')
    texto = trocar(texto,
        'class="botao botao-primario botao-link" href="{{ url_for(\'boxes.boxes_mestre\', jogador_id=jogador.get(\'id\')) }}">Box</a>',
        'class="botao botao-secundario botao-link" href="{{ url_for(\'boxes.boxes_mestre\', jogador_id=jogador.get(\'id\')) }}">Box</a>')
    # Gestão restrita ao mestre. Formulário de perfil usa CSRF já existente.
    gerenciar = '''        <details class="painel-jogador-gestao">
            <summary>Gerenciar nível e acesso</summary>
            <div class="painel-jogador-gestao-conteudo">
''' + formulario_nivel + '''
                <form method="post" action="{{ url_for('mestre.alterar_perfil', usuario_id=jogador.get('usuario_id')) }}">
                    <input type="hidden" name="csrf_token" value="{{ nivel_csrf_token }}">
                    <label>Perfil
                        <select name="perfil" aria-label="Permissão de {{ jogador.get('nome') }}">
                            <option value="jogador" {% if jogador.get('perfil') != 'tester' %}selected{% endif %}>Jogador</option>
                            <option value="tester" {% if jogador.get('perfil') == 'tester' %}selected{% endif %}>Tester</option>
                        </select>
                    </label>
                    <button type="submit" class="botao botao-secundario">Salvar perfil</button>
                </form>
                <form method="post" action="{{ url_for('mestre.atividade_usuario', usuario_id=jogador.get('usuario_id')) }}">
                    <input type="hidden" name="ativo" value="{{ '0' if jogador.get('acesso_ativo') else '1' }}">
                    <button type="submit" class="botao botao-secundario">{{ 'Desativar acesso' if jogador.get('acesso_ativo') else 'Ativar acesso' }}</button>
                </form>
            </div>
        </details>
'''
    texto = trocar(texto, '''        </header>

        <div class="painel-jogador-resumo">''',
                   '''        </header>
''' + gerenciar + '''
        <div class="painel-jogador-resumo">''')
    resumo = '''<div class="painel-jogador-resumo">
            <section class="painel-recurso painel-recurso-treinador" data-pv-container>
                <div class="painel-recurso-cabecalho">
                    <div><span>PV do treinador</span><strong data-pv-valor>{{ jogador.get('pv_atual', 0) }}/{{ jogador.get('pv_maximo', 0) }}</strong></div>
                    <span class="painel-dinheiro">₽ {{ jogador.get('pokedolares', 0) }}</span>
                </div>
                <progress data-pv-progresso value="{{ [jogador.get('pv_atual', 0), 0]|max }}" max="{{ jogador.get('pv_maximo', 1) if jogador.get('pv_maximo', 0) > 0 else 1 }}"></progress>
                <form class="controle-pv-rapido" method="post" action="{{ url_for('mestre.ajustar_pv_personagem_painel', personagem_id=jogador.get('id')) }}" data-pv-form>
                    <input type="number" name="quantidade" value="10" min="1" max="9999" step="1" inputmode="numeric" aria-label="Quantidade de PV do treinador" required>
                    <button type="submit" data-operacao="menos" aria-label="Reduzir PV do treinador">−</button>
                    <button type="submit" data-operacao="mais" aria-label="Aumentar PV do treinador">+</button>
                </form>
            </section>
            <div class="painel-jogador-chips" aria-label="Resumo de {{ jogador.get('nome') }}">
                <span>Nv {{ jogador.get('nivel', 1) }}</span>
                <span>{{ jogador.get('equipe_total', 0) }}/{{ jogador.get('limite_equipe', 6) }} na equipe</span>
                <span>{{ jogador.get('box_total', 0) }} na Box</span>
                <span>{{ 'Tester' if jogador.get('perfil') == 'tester' else 'Jogador' }}</span>
                <span>{{ 'Acesso ativo' if jogador.get('acesso_ativo') else 'Acesso desativado' }}</span>
            </div>
            <details class="painel-jogador-atributos-expansivel">
                <summary>Ver atributos do treinador</summary>
                <div class="painel-jogador-atributos" aria-label="Atributos de {{ jogador.get('nome') }}">
                    {% for atributo in jogador.get('atributos', []) %}
                    <div class="painel-atributo-personagem"><span>{{ atributo.get('nome') }}</span><strong>{{ atributo.get('valor') }}</strong></div>
                    {% else %}<span class="texto-suave">Nenhum atributo configurado.</span>{% endfor %}
                </div>
            </details>
        </div>

        '''
    texto = regex_uma(texto,
        r'<div class="painel-jogador-resumo">[\s\S]*?(?=\{% if jogador\.get\(\'alertas\'\) %\})',
        lambda _: resumo)
    # Os nicknames são exibidos em duas linhas de altura estável em todos os cards.
    texto = trocar(texto,
        '''{% if pokemon.get('nome') != pokemon.get('especie') %}<small>{{ pokemon.get('especie') }}</small>{% endif %}''',
        '''<small class="painel-pokemon-especie">{{ pokemon.get('especie') if pokemon.get('nome') != pokemon.get('especie') else '' }}</small>''')
    texto = regex_uma(texto,
        r'<form class="controle-pv-rapido controle-pv-pokemon"([^>]*)>[\s\S]*?</form>',
        lambda m: '<form class="controle-pv-rapido controle-pv-pokemon"' + m.group(1) + '>\n'
        '                        <input type="number" name="quantidade" value="10" min="1" max="9999" step="1" inputmode="numeric" aria-label="Quantidade de PV do Pokémon" required>\n'
        '                        <button type="submit" data-operacao="menos" aria-label="Reduzir PV do Pokémon">−</button>\n'
        '                        <button type="submit" data-operacao="mais" aria-label="Aumentar PV do Pokémon">+</button>\n'
        '                    </form>')
    # Versão explícita evita servir JS antigo do cache após instalação.
    script_antigo = """<script src="{{ url_for('static', filename='js/painel-mestre.js') }}"></script>"""
    script_novo = """<script src="{{ url_for('static', filename='js/painel-mestre.js', v='10d2') }}"></script>"""
    if script_antigo in texto:
        texto = trocar(texto, script_antigo, script_novo)
    return texto


def alterar_js(texto: str) -> str:
    texto = regex_uma(texto,
        r'    const mostrarMensagem = \(texto, erro = false\) => \{[\s\S]*?\n    \};\n\n    (?=const atualizarNumerosOrdem)',
        lambda _: '''    const mostrarMensagem = (texto, erro = false) => {
        // ANKAR_10D2_CENTRAL_MESTRE — Toast de 1,5 segundo, como as demais páginas do sistema.
        if (window.PokemonRPGToast?.mostrar) {
            window.PokemonRPGToast.mostrar(texto, erro ? 'erro' : 'sucesso');
            if (mensagem) mensagem.textContent = '';
            return;
        }
        if (!mensagem) return;
        mensagem.textContent = texto;
        window.clearTimeout(mostrarMensagem.timer);
        mostrarMensagem.timer = window.setTimeout(() => { mensagem.textContent = ''; }, 1500);
    };

    ''')
    texto = trocar(texto,
        '''            const delta = botao?.dataset.delta;
            if (!delta) return;''',
        '''            const quantidade = Number(form.querySelector('[name="quantidade"]')?.value);
            const operacao = botao?.dataset.operacao;
            if (!Number.isInteger(quantidade) || quantidade < 1 || quantidade > 9999 ||
                !['mais', 'menos'].includes(operacao)) {
                mostrarMensagem('Informe uma quantidade válida entre 1 e 9999 PV.', true);
                return;
            }
            const delta = String(operacao === 'mais' ? quantidade : -quantidade);''')
    # Recarrega após cura para refletir PV, condições e alertas do servidor.
    bloco = '''
    document.querySelectorAll('[data-cura-10d2]').forEach((form) => {
        form.addEventListener('submit', async (evento) => {
            evento.preventDefault();
            const global = form.dataset.curaGlobal === 'true';
            const pergunta = global
                ? 'Curar todos os Pokémon (equipe e Box) de TODOS os jogadores ativos? A operação não poderá ser desfeita automaticamente.'
                : 'Curar todos os Pokémon (equipe e Box) deste jogador e remover suas condições?';
            if (!window.confirm(pergunta)) return;
            const botao = form.querySelector('[type="submit"]');
            if (botao) botao.disabled = true;
            try {
                const resposta = await fetch(form.action, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'fetch' },
                    body: new FormData(form),
                });
                const dados = await resposta.json();
                if (!resposta.ok) throw new Error(dados.erro || 'Não foi possível concluir a cura.');
                window.location.reload(); // re-renderiza todos os PV e condições.
            } catch (erro) {
                mostrarMensagem(erro.message || 'Falha ao curar Pokémon.', true);
                if (botao) botao.disabled = false;
            }
        });
    });
'''
    if '    atualizarNumerosOrdem();\n    aplicarPesquisa();' not in texto:
        raise InstalacaoIncompativel('Bloco de inicialização do JS não encontrado.')
    return trocar(texto, '    atualizarNumerosOrdem();\n    aplicarPesquisa();',
                 bloco + '\n    atualizarNumerosOrdem();\n    aplicarPesquisa();')


def alterar_base(texto: str) -> str:
    return trocar(
        texto,
        '                    <a href="{{ url_for(\'mestre.jogadores\') }}">Jogadores</a>',
        '                    {# ANKAR_10D2_CENTRAL_MESTRE: jogadores integrados ao Painel. #}',
    )


TRANSFORMADORES = {
    "app/routes/mestre.py": alterar_rotas,
    "app/services/painel_mestre_service.py": alterar_servico,
    "templates/mestre/dashboard.html": alterar_template,
    "static/js/painel-mestre.js": alterar_js,
    "templates/base.html": alterar_base,
}


def instalar(raiz: Path, *, verificar: bool = False) -> list[str]:
    raiz = Path(raiz)
    # Planejamento integral antes de escrever um único arquivo.
    plano: dict[str, str] = {}
    for rel, transformar in TRANSFORMADORES.items():
        caminho = raiz / rel
        if not caminho.is_file():
            raise InstalacaoIncompativel(f"Arquivo obrigatório ausente: {rel}")
        original = caminho.read_text(encoding="utf-8")
        if MARKER in original:
            continue  # já instalado
        plano[rel] = transformar(original)
    if verificar or not plano:
        return list(plano)
    backup = raiz / 'relatorios' / 'backups_ui_10d2' / datetime.now().strftime('%Y%m%d-%H%M%S')
    for rel in plano:
        destino_backup = backup / rel
        destino_backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raiz / rel, destino_backup)
    for rel, conteudo in plano.items():
        (raiz / rel).write_text(conteudo, encoding='utf-8')
    return list(plano)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verificar', action='store_true', help='Pré-validar sem escrever arquivos')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        alterados = instalar(root, verificar=args.verificar)
    except InstalacaoIncompativel as exc:
        parser.error(str(exc))
    if not alterados:
        print('10D.2 já instalada. Nenhuma alteração.')
    else:
        print(('Pré-validação OK' if args.verificar else 'Instalação aplicada') + ':')
        for arquivo in alterados:
            print(' - ' + arquivo.replace('\\', '/'))
        if not args.verificar:
            print('Backups em relatorios/backups_ui_10d2; reinicie o Flask e use Ctrl+F5.')


if __name__ == '__main__':
    main()
