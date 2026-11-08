/* ANKAR_10D3_CARDS_VERTICAIS — opções acessíveis dos treinadores.
   Não interfere com ajustes de PV, curas ou navegação do painel. */
(() => {
  'use strict';
  const menus = [...document.querySelectorAll('[data-menu-opcoes]')];
  if (!menus.length) return;
  function fechar(exceto = null) {
    menus.forEach((menu) => { if (menu !== exceto) menu.open = false; });
  }
  menus.forEach((menu) => {
    menu.addEventListener('toggle', () => { if (menu.open) fechar(menu); });
  });
  document.addEventListener('pointerdown', (evento) => {
    if (!menus.some((menu) => menu.open)) return;
    const atual = menus.find((menu) => menu.contains(evento.target));
    fechar(atual || null);
  });
  document.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Escape') return;
    const ativo = menus.find((menu) => menu.open);
    if (!ativo) return;
    fechar();
    ativo.querySelector('summary')?.focus();
  });
})();
