/* 10D.4.5 — Confirmação de retirada de integrante (sem window.confirm). */
(() => {
  const modal = document.querySelector('[data-npc-confirm-dialog]');
  if (!modal) return;
  const texto = modal.querySelector('[data-npc-confirm-text]');
  const cancelar = modal.querySelector('[data-npc-cancelar]');
  const confirmar = modal.querySelector('[data-npc-confirmar]');
  let pendente = null;
  let confirmado = new WeakSet();

  document.addEventListener('submit', (evento) => {
    const form = evento.target.closest('form[data-npc-confirm]');
    if (!form) return;
    if (confirmado.has(form)) { confirmado.delete(form); return; }
    evento.preventDefault();
    if (modal.open) return;
    if (typeof modal.showModal !== 'function') return;
    pendente = form;
    texto.textContent = form.dataset.npcConfirm;
    modal.showModal();
    cancelar.focus();
  });
  cancelar.addEventListener('click', () => modal.close());
  modal.addEventListener('click', (evento) => { if (evento.target === modal) modal.close(); });
  modal.addEventListener('close', () => { pendente = null; });
  confirmar.addEventListener('click', () => {
    const form = pendente;
    if (!form) return;
    pendente = null;
    modal.close();
    confirmado.add(form);
    form.requestSubmit();
  });
})();
