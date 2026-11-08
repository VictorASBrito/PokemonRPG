/* 10C.5 — navegação responsiva; usa os links existentes, sem alterar sessões. */
(() => {
  'use strict';
  const header = document.querySelector('.topo');
  const toggle = header?.querySelector('[data-ui-nav-toggle]');
  const nav = header?.querySelector('[data-ui-navegacao]');
  if (!header || !toggle || !nav) return;

  function abrir(valor) {
    const ativo = Boolean(valor);
    header.dataset.uiNavOpen = ativo ? 'true' : 'false';
    toggle.setAttribute('aria-expanded', String(ativo));
    toggle.setAttribute('aria-label', ativo ? 'Fechar menu de navegação' : 'Abrir menu de navegação');
    toggle.querySelector('.ui-menu-icone').textContent = ativo ? '×' : '☰';
  }

  // Página atual, incluindo URLs de ficha isolada /p/<login>/...
  for (const link of nav.querySelectorAll('a[href]')) {
    try {
      const destino = new URL(link.href, window.location.href);
      if (destino.pathname === window.location.pathname) {
        link.setAttribute('aria-current', 'page');
      }
    } catch (_) {
      // Links externos ou inválidos não devem interromper o menu.
    }
    link.addEventListener('click', () => abrir(false));
  }
  toggle.addEventListener('click', () => abrir(toggle.getAttribute('aria-expanded') !== 'true'));
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || toggle.getAttribute('aria-expanded') !== 'true') return;
    abrir(false);
    toggle.focus();
  });
  document.addEventListener('pointerdown', (event) => {
    if (toggle.getAttribute('aria-expanded') !== 'true') return;
    if (!header.contains(event.target)) abrir(false);
  });
  const mobile = window.matchMedia('(max-width: 1100px)');
  mobile.addEventListener?.('change', () => abrir(false));
  abrir(false);
})();
