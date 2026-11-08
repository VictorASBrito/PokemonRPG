/* 10C.4.1 — avisos flash em toasts de 1,5s, com pausa ao passar o mouse/focar. */
(() => {
  'use strict';
  const SAIDA_MS = 170;
  const avisos = document.querySelectorAll('[data-aviso-toast]');
  for (const aviso of avisos) {
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
})();
