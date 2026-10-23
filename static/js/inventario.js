/* Inventário estilo BW, adaptado ao layout do site. */
(() => {
  'use strict';
  const root = document.querySelector('[data-inventario]');
  if (!root) return;

  const panel = root.querySelector('.inventario-nds-bag');
  const tabs = [...root.querySelectorAll('[data-aba-botao]')];
  const rows = [...root.querySelectorAll('[data-item-id]')];
  const details = [...root.querySelectorAll('[data-detalhe-item]')];
  const bagArt = [...root.querySelectorAll('[data-arte-bolsa]')];
  const logoArt = [...root.querySelectorAll('[data-logo-bolsa]')];
  const filter = root.querySelector('[data-busca-inventario]');
  const noItems = root.querySelector('[data-nenhum-item]');
  const count = root.querySelector('[data-contador-itens]');
  const currentBag = root.querySelector('[data-nome-bolsa]');
  const bagText = root.querySelector('[data-texto-bolsa]');
  const placeholder = root.querySelector('[data-placeholder-detalhe]');

  const metadata = {
    cura: ['Cura', 'Poções, remédios e itens de recuperação para a equipe.'],
    pokebolas: ['Pokébolas', 'Esferas, acessórios de captura e recursos ligados ao armazenamento de Pokémon.'],
    frutas: ['Frutinhas', 'Bagas, frutas e alimentos especiais que podem ajudar seus Pokémon.'],
    avulsos: ['Avulsos', 'Materiais gerais, acessórios e outros objetos utilitários.'],
    chave: ['Item-chave', 'Objetos importantes da campanha que normalmente não são consumidos.'],
  };

  const normalize = (value) => String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

  let activeBag = null;
  let activeItem = null;

  function selectItem(id) {
    activeItem = id || null;
    for (const row of rows) {
      const selected = row.dataset.itemId === activeItem;
      row.classList.toggle('selecionado', selected);
      row.querySelector('button')?.setAttribute('aria-pressed', selected ? 'true' : 'false');
    }
    for (const detail of details) {
      detail.hidden = detail.dataset.detalheItem !== activeItem;
    }
    if (placeholder) placeholder.hidden = !!activeItem;
  }

  function refresh() {
    const term = normalize(filter?.value);
    const visible = [];
    for (const row of rows) {
      const matchesBag = row.dataset.bolsa === activeBag;
      const matchesSearch = normalize(row.dataset.busca).includes(term);
      row.hidden = !(matchesBag && matchesSearch);
      if (!row.hidden) visible.push(row);
    }
    if (count) count.textContent = String(visible.length);
    if (noItems) noItems.hidden = visible.length !== 0;

    const selectedStillVisible = visible.some((row) => row.dataset.itemId === activeItem);
    if (selectedStillVisible) {
      selectItem(activeItem);
    } else {
      selectItem(visible[0]?.dataset.itemId || null);
    }
  }

  function applyBagVisual(key) {
    for (const image of bagArt) image.hidden = image.dataset.arteBolsa !== key;
    for (const image of logoArt) image.hidden = image.dataset.logoBolsa !== key;
    if (currentBag) currentBag.textContent = metadata[key][0];
    if (bagText) bagText.textContent = metadata[key][1];
    panel.dataset.aba = key;
  }

  function selectBag(key) {
    if (!metadata[key]) return;
    activeBag = key;
    applyBagVisual(key);
    for (const tab of tabs) {
      tab.setAttribute('aria-pressed', tab.dataset.abaBotao === key ? 'true' : 'false');
    }
    if (filter) filter.value = '';
    refresh();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectBag(tab.dataset.abaBotao));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      const direction = event.key === 'ArrowRight' ? 1 : -1;
      const next = tabs[(index + direction + tabs.length) % tabs.length];
      next.focus();
      selectBag(next.dataset.abaBotao);
    });
  });

  rows.forEach((row) => {
    row.querySelector('button')?.addEventListener('click', () => selectItem(row.dataset.itemId));
  });

  filter?.addEventListener('input', refresh);

  const firstNonEmpty = tabs.find((tab) => rows.some((row) => row.dataset.bolsa === tab.dataset.abaBotao));
  selectBag(firstNonEmpty?.dataset.abaBotao || 'cura');
})();
