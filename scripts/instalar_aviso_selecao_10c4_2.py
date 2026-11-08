"""10C.4.2: mensagens de seleção da mochila no toast global (1,5s).

Requer 10C.4 e 10C.4.1 instaladas. Não acessa o PostgreSQL.
Executar: python scripts/instalar_aviso_selecao_10c4_2.py
"""
from __future__ import annotations

from pathlib import Path
import argparse

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVOS = {
    "template": "templates/jogador/inventario.html",
    "inventario_js": "static/js/inventario-uso-10c4.js",
    "toast_js": "static/js/avisos-toast-10c4-1.js",
    "css": "static/css/inventario-uso-10c4.css",
    "base": "templates/base.html",
}
MARCADOR = "ANKAR_10C4_2_SELECAO_TOAST"


def substituir_um(texto: str, antigo: str, novo: str, caminho: str) -> str:
    ocorrencias = texto.count(antigo)
    if ocorrencias != 1:
        raise RuntimeError(f"{caminho}: âncora esperada 1 vez, encontrada {ocorrencias}: {antigo[:90]!r}")
    return texto.replace(antigo, novo, 1)


def alterar_template(s: str) -> str:
    p = ARQUIVOS["template"]
    original = '''        <div class="inventario-uso-aviso" data-uso-aviso role="status" aria-live="polite" hidden>
            <span data-uso-mensagem></span>
            <button type="button" data-uso-cancelar>Cancelar</button>
        </div>
'''
    s = substituir_um(s, original, "", p)
    logo = '''            <div class="inventario-nds-logo-copy">
                <strong>BAG</strong>
                <small>{{ personagem.nome }}</small>
            </div>
        </div>'''
    novo_logo = '''            <div class="inventario-nds-logo-copy">
                <strong>BAG</strong>
                <small>{{ personagem.nome }}</small>
            </div>
            {# ANKAR_10C4_2_SELECAO_TOAST: cancelar permanece disponível; aviso é temporário. #}
            <div class="inventario-uso-cancelamento" data-uso-aviso hidden>
                <button type="button" data-uso-cancelar aria-label="Cancelar seleção de Pokémon">Cancelar</button>
            </div>
        </div>'''
    s = substituir_um(s, logo, novo_logo, p)
    s = substituir_um(s, "filename='js/inventario-uso-10c4.js', v='10c4'", "filename='js/inventario-uso-10c4.js', v='10c4-2'", p)
    s = substituir_um(s, "filename='css/inventario-uso-10c4.css', v='10c4'", "filename='css/inventario-uso-10c4.css', v='10c4-2'", p)
    return s


def alterar_inventario_js(s: str) -> str:
    p = ARQUIVOS["inventario_js"]
    s = substituir_um(s, "  const msg = root.querySelector('[data-uso-mensagem]');\n", "", p)
    velho = '''  function informar(texto) {
    if (msg) msg.textContent = texto;
    if (msgWrap) msgWrap.hidden = false;
  }
'''
    novo = '''  // ANKAR_10C4_2_SELECAO_TOAST: usa a mesma notificação global de 1,5s.
  function informar(texto, tipo = 'info') {
    window.PokemonRPGToast?.mostrar(texto, tipo);
  }
'''
    s = substituir_um(s, velho, novo, p)
    s = substituir_um(s, '''    if (msgWrap) msgWrap.hidden = true;
    for (const card of cards) {''', '''    if (msgWrap) msgWrap.hidden = true;
    window.PokemonRPGToast?.fecharDinamico();
    for (const card of cards) {''', p)
    s = substituir_um(s, '''      if (aguardando) {
        botao.setAttribute('aria-pressed', 'true');
        informar('Selecione um Pokémon destacado para usar o item.');
      } else {
        informar('Nenhum Pokémon da equipe pode receber o efeito agora.');
      }''', '''      if (aguardando) {
        botao.setAttribute('aria-pressed', 'true');
        if (msgWrap) msgWrap.hidden = false; // apenas Cancelar, sem banner de aviso
        informar('Selecione um Pokémon destacado para usar o item.', 'info');
      } else {
        informar('Nenhum Pokémon da equipe pode receber o efeito agora.', 'aviso');
      }''', p)
    return s


def alterar_toast_js(s: str) -> str:
    p = ARQUIVOS["toast_js"]
    s = substituir_um(s, "  for (const aviso of avisos) {", "  function iniciarAviso(aviso) {", p)
    final = '''    continuar();
  }
})();'''
    novo = '''    continuar();
  }
  avisos.forEach(iniciarAviso);

  // ANKAR_10C4_2_SELECAO_TOAST: API para alertas de interface sem redirecionamento.
  function fecharDinamico() {
    document.querySelectorAll('[data-aviso-toast-dinamico]').forEach(aviso => aviso.remove());
  }

  function mostrar(texto, tipo = 'info') {
    const area = document.querySelector('[data-avisos-toast]');
    if (!area || !texto) return;
    fecharDinamico(); // trocar um aviso contextual, não empilhar mensagens vencidas
    const tipos = new Set(['sucesso', 'erro', 'aviso', 'info']);
    const categoria = tipos.has(tipo) ? tipo : 'info';
    const aviso = document.createElement('div');
    aviso.className = `aviso-toast aviso-toast--${categoria}`;
    aviso.setAttribute('role', categoria === 'erro' ? 'alert' : 'status');
    aviso.dataset.avisoToast = '';
    aviso.dataset.avisoToastDinamico = '';
    aviso.dataset.tempoMs = '1500';

    const icone = document.createElement('span');
    icone.className = 'aviso-toast-icone';
    icone.setAttribute('aria-hidden', 'true');
    const mensagem = document.createElement('span');
    mensagem.className = 'aviso-toast-mensagem';
    mensagem.textContent = String(texto); // nunca inserir HTML de avisos
    const fechar = document.createElement('button');
    fechar.type = 'button';
    fechar.className = 'aviso-toast-fechar';
    fechar.dataset.avisoToastFechar = '';
    fechar.setAttribute('aria-label', 'Fechar aviso');
    fechar.textContent = '×';
    aviso.append(icone, mensagem, fechar);
    area.appendChild(aviso);
    iniciarAviso(aviso); // mesmo tempo, animação, pausa e fechamento do flash
  }

  window.PokemonRPGToast = Object.freeze({ mostrar, fecharDinamico });
})();'''
    return substituir_um(s, final, novo, p)


def alterar_css(s: str) -> str:
    p = ARQUIVOS["css"]
    # Retira a aparência de banner dos controles; preserva o botão Cancelar no topo.
    inicio = '.inventario-uso-aviso {'
    fim = '.inventario-equipar-dialogo {'
    if s.count(inicio) != 1 or s.count(fim) != 1:
        raise RuntimeError(f"{p}: regras do antigo aviso não encontradas ou ambíguas")
    a, b = s.index(inicio), s.index(fim, s.index(inicio))
    s = s[:a] + '''/* ANKAR_10C4_2_SELECAO_TOAST: nenhum aviso fixo sobre a lista de Pokémon. */
.inventario-uso-cancelamento { margin-left: auto; flex: 0 0 auto; }
.inventario-uso-cancelamento[hidden] { display: none !important; }
.inventario-uso-cancelamento button {
  font: inherit;
  font-weight: 750;
  font-size: .75rem;
  cursor: pointer;
  padding: 7px 9px;
  border-radius: 10px;
  border: 1px solid rgba(111, 201, 160, .55);
  background: rgba(34, 82, 64, .35);
  color: var(--inv-text, #fff);
}
.inventario-uso-cancelamento button:hover,
.inventario-uso-cancelamento button:focus-visible {
  outline: 2px solid rgba(109, 234, 161, .7);
  outline-offset: 1px;
}
''' + s[b:]
    return s


def alterar_base(s: str) -> str:
    p = ARQUIVOS["base"]
    if "AVISOS_TOAST_10C4_1" not in s:
        raise RuntimeError(f"{p}: instale a Etapa 10C.4.1 antes da 10C.4.2")
    return substituir_um(s, "filename='js/avisos-toast-10c4-1.js', v='10c4-1'", "filename='js/avisos-toast-10c4-1.js', v='10c4-2'", p)


def preparar(raiz: Path) -> dict[Path, str]:
    raiz = Path(raiz)
    fontes = {nome: (raiz / caminho).read_text(encoding="utf-8") for nome, caminho in ARQUIVOS.items()}
    marcados = {nome: MARCADOR in texto for nome, texto in fontes.items() if nome != "base"}
    if all(marcados.values()):
        if "filename='js/avisos-toast-10c4-1.js', v='10c4-2'" not in fontes["base"]:
            raise RuntimeError("Atualização parcial: versão do JS global no base.html divergente")
        return {}
    if any(marcados.values()):
        raise RuntimeError(f"Atualização parcial: marcadores encontrados em {marcados}. Revise os backups.")
    if "ANKAR_10C4_USO_LINHA" not in fontes["template"]:
        raise RuntimeError("Instale antes a Etapa 10C.4 (uso visual na lista).")
    planos = {
        raiz / ARQUIVOS["template"]: alterar_template(fontes["template"]),
        raiz / ARQUIVOS["inventario_js"]: alterar_inventario_js(fontes["inventario_js"]),
        raiz / ARQUIVOS["toast_js"]: alterar_toast_js(fontes["toast_js"]),
        raiz / ARQUIVOS["css"]: alterar_css(fontes["css"]),
        raiz / ARQUIVOS["base"]: alterar_base(fontes["base"]),
    }
    return planos


def instalar(raiz: Path = RAIZ) -> list[str]:
    raiz = Path(raiz)
    planos = preparar(raiz)  # valida todos antes de qualquer gravação
    if not planos:
        return []
    for caminho in planos:
        backup = caminho.with_name(caminho.name + ".bak-10c4-2")
        if backup.exists():
            raise RuntimeError(f"Backup existente sem instalação concluída: {backup}")
    antigos = {}
    alterados = []
    try:
        for caminho, novo in planos.items():
            antigos[caminho] = caminho.read_text(encoding="utf-8")
            backup = caminho.with_name(caminho.name + ".bak-10c4-2")
            backup.write_text(antigos[caminho], encoding="utf-8")
            caminho.write_text(novo, encoding="utf-8")
            alterados.append(caminho)
    except Exception:
        for caminho in reversed(alterados):
            caminho.write_text(antigos[caminho], encoding="utf-8")
        raise
    return [str(p.relative_to(raiz)) for p in alterados]


def main():
    p = argparse.ArgumentParser(description="Torna os avisos da seleção Pokémon temporários (10C.4.2)")
    p.add_argument("--raiz", type=Path, default=RAIZ)
    args = p.parse_args()
    modificados = instalar(args.raiz)
    print("Etapa 10C.4.2 aplicada:" if modificados else "Etapa 10C.4.2 já instalada; nenhuma mudança.")
    for caminho in modificados:
        print(" -", caminho)
    print("Sem alterações no banco, inventários, regras de cura ou histórico.")


if __name__ == "__main__":
    main()
