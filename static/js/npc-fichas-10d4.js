/* Fechamento acessível dos menus de NPC e confirmação de arquivamento. */
(() => {
  const menus = [...document.querySelectorAll('.npc-ficha-card details.painel-jogador-gestao')];
  document.addEventListener('pointerdown', event => {
    for (const menu of menus) {
      if (!menu.contains(event.target)) menu.open = false;
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      for (const menu of menus) menu.open = false;
    }
  });
  document.querySelectorAll('[data-npc-arquivar]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm('Arquivar este NPC? As instâncias já colocadas no Campo serão preservadas.')) event.preventDefault();
    });
  });
})();
