/* Atualização compartilhada por polling leve. O backend renderiza Jinja escapado. */
(() => {
  'use strict';
  const container = document.querySelector('[data-campo-estado]');
  const status = document.querySelector('[data-campo-atualizacao]');
  if (!container || !container.dataset.estadoUrl) return;

  let pendente = false;
  let ultimoHTML = container.innerHTML;
  const atualizar = async () => {
    if (pendente || document.hidden || container.contains(document.activeElement)) return;
    pendente = true;
    try {
      const resposta = await fetch(container.dataset.estadoUrl, {
        credentials: 'same-origin', cache: 'no-store',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!resposta.ok) throw new Error('Estado indisponível');
      const html = await resposta.text();
      if (html !== ultimoHTML) {
        container.innerHTML = html;
        ultimoHTML = html;
        const grupos = container.querySelectorAll('.campo-time-ativo');
        const criaturas = container.querySelectorAll('.campo-pokemon');
        const total = document.querySelector('[data-campo-total]');
        const times = document.querySelector('[data-campo-times]');
        if (total) total.textContent = String(criaturas.length);
        if (times) times.textContent = String(grupos.length);
      }
      if (status) status.textContent = 'Campo sincronizado automaticamente a cada 6 segundos.';
    } catch (_erro) {
      if (status) status.textContent = 'Sem atualização automática no momento. Atualize a página para tentar novamente.';
    } finally { pendente = false; }
  };
  document.querySelector('[data-campo-limpar]')?.addEventListener('submit', (evento) => {
    if (!window.confirm('Retirar todos os Pokémon do campo?')) evento.preventDefault();
  });
  window.setInterval(atualizar, 6000);
})();
