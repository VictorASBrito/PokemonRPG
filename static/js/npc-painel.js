/* 10D.4.6 — Ações do mestre em diálogos, sem disputar a grade do jogador. */
(() => {
  'use strict';

  const confirmacao = document.querySelector('[data-npc-confirm-dialog]');
  const texto = confirmacao?.querySelector('[data-npc-confirm-text]');
  const cancelar = confirmacao?.querySelector('[data-npc-cancelar]');
  const confirmar = confirmacao?.querySelector('[data-npc-confirmar]');
  const confirmado = new WeakSet();
  const disparadores = new WeakMap();
  let pendente = null;

  // Os diálogos abertos têm precedência sobre o "Esc para recolher" do painel.
  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape' && document.querySelector('dialog[open]')) {
      evento.stopPropagation();
    }
  }, true);

  document.querySelectorAll('dialog.npc-painel-dialog').forEach((dialogo) => {
    dialogo.addEventListener('click', (evento) => {
      if (evento.target === dialogo || evento.target.closest('[data-npc-dialog-close]')) {
        dialogo.close();
      }
    });
    dialogo.addEventListener('close', () => {
      const disparador = disparadores.get(dialogo);
      if (disparador?.isConnected) disparador.focus({ preventScroll: true });
      disparadores.delete(dialogo);
    });
  });

  document.querySelectorAll('[data-npc-dialog-open]').forEach((botao) => {
    botao.addEventListener('click', (evento) => {
      evento.stopPropagation();
      const dialogo = document.getElementById(botao.dataset.npcDialogOpen);
      if (!dialogo || dialogo.open || typeof dialogo.showModal !== 'function') return;
      disparadores.set(dialogo, botao);
      dialogo.showModal();
      const foco = dialogo.querySelector('input:not([type="hidden"]), select, [data-npc-dialog-close]');
      foco?.focus({ preventScroll: true });
    });
  });

  if (!confirmacao) return;

  document.addEventListener('submit', (evento) => {
    const form = evento.target.closest('form[data-npc-confirm]');
    if (!form) return;
    if (confirmado.has(form)) {
      confirmado.delete(form);
      return;
    }
    evento.preventDefault();
    if (confirmacao.open || typeof confirmacao.showModal !== 'function') return;
    pendente = form;
    texto.textContent = form.dataset.npcConfirm;
    confirmacao.showModal();
    cancelar.focus();
  });

  cancelar?.addEventListener('click', () => confirmacao.close());
  confirmacao.addEventListener('close', () => { pendente = null; });
  confirmar?.addEventListener('click', () => {
    const form = pendente;
    if (!form) return;
    pendente = null;
    confirmado.add(form);
    confirmacao.close();
    form.requestSubmit();
  });
})();
