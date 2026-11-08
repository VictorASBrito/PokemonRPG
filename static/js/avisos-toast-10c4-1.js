/* 10C.4.1 — avisos flash em toasts de 1,5s, com pausa ao passar o mouse/focar. */
(() => {
  'use strict';
  const SAIDA_MS = 170;
  const avisos = document.querySelectorAll('[data-aviso-toast]');
  function iniciarAviso(aviso) {
    const total = Number.parseInt(aviso.dataset.tempoMs, 10) || 1500;
    let restante = Math.max(0, total - SAIDA_MS);
    let inicio = 0;
    let temporizador = null;
    let saindo = false;
    let sobMouse = false;
    let comFoco = false;

    function fechar() {
      if (saindo) return;
      saindo = true;
      clearTimeout(temporizador);
      aviso.classList.add('aviso-toast--saindo');
      // Limpa o DOM mesmo quando a animacao esta desativada no sistema.
      window.setTimeout(() => aviso.remove(), SAIDA_MS);
    }

    function pausar() {
      if (temporizador !== null) {
        clearTimeout(temporizador);
        restante = Math.max(0, restante - (Date.now() - inicio));
        temporizador = null;
      }
    }

    function continuar() {
      if (saindo || sobMouse || comFoco || temporizador !== null) return;
      if (restante <= 0) { fechar(); return; }
      inicio = Date.now();
      temporizador = window.setTimeout(() => { temporizador = null; fechar(); }, restante);
    }

    aviso.addEventListener('pointerenter', () => { sobMouse = true; pausar(); });
    aviso.addEventListener('pointerleave', () => { sobMouse = false; continuar(); });
    aviso.addEventListener('focusin', () => { comFoco = true; pausar(); });
    aviso.addEventListener('focusout', (event) => {
      if (aviso.contains(event.relatedTarget)) return;
      comFoco = false;
      continuar();
    });
    aviso.querySelector('[data-aviso-toast-fechar]')?.addEventListener('click', fechar);
    continuar();
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
})();
