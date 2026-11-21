/* 11C — Ordenação por personagem: mouse, toque (alça) e teclado. */
(() => {
  'use strict';
  const root = document.querySelector('[data-inventario][data-ordem-url]');
  if (!root) return;
  const list = root.querySelector('[data-lista-inventario]');
  const toggle = root.querySelector('[data-ordem-toggle]');
  const help = root.querySelector('[data-ordem-ajuda]');
  const status = root.querySelector('[data-ordem-status]');
  const search = root.querySelector('[data-busca-inventario]');
  const tabs = [...root.querySelectorAll('[data-aba-botao]')];
  const handles = [...list.querySelectorAll('[data-ordem-alca]')];
  let editing = false;
  let saving = false;
  let drag = null;
  let frame = 0;

  const rows = () => [...list.querySelectorAll(':scope > [data-item-id]')];
  const bag = () => root.querySelector('[data-aba-botao][aria-pressed="true"]')?.dataset.abaBotao;
  const bagRows = (key) => rows().filter(row => row.dataset.bolsa === key);
  const report = message => { status.textContent = message; };

  function mode(value) {
    if (saving) return;
    clearDrag();
    editing = value;
    root.dataset.organizando = String(value);
    toggle.setAttribute('aria-pressed', String(value));
    toggle.textContent = value ? 'Concluir organização' : 'Organizar itens';
    help.hidden = !value;
    for (const handle of handles) handle.hidden = !value;
    if (search) {
      if (value && search.value) {
        search.value = '';
        search.dispatchEvent(new Event('input', { bubbles: true }));
      }
      search.disabled = value;
    }
  }

  function clearDrag() {
    cancelAnimationFrame(frame);
    frame = 0;
    if (!drag) return;
    drag.row.classList.remove('inventario-ordem-arrastando');
    if (drag.target) drag.target.classList.remove('inventario-ordem-antes', 'inventario-ordem-depois');
    const old = drag;
    drag = null;
    if (old.handle.hasPointerCapture(old.pointer)) old.handle.releasePointerCapture(old.pointer);
  }

  function getTarget(x, y, current) {
    const bounds = list.getBoundingClientRect();
    if (x < bounds.left || x > bounds.right || y < bounds.top || y > bounds.bottom) return null;
    return bagRows(current.key).find(row => {
      const rect = row.getBoundingClientRect();
      return row !== current.row && !row.hidden && y >= rect.top && y <= rect.bottom;
    }) || null;
  }

  function markTarget() {
    if (!drag) return;
    drag.target?.classList.remove('inventario-ordem-antes', 'inventario-ordem-depois');
    drag.target = getTarget(drag.x, drag.y, drag);
    if (drag.target) {
      const rect = drag.target.getBoundingClientRect();
      drag.after = drag.y >= rect.top + rect.height / 2;
      drag.target.classList.add(drag.after ? 'inventario-ordem-depois' : 'inventario-ordem-antes');
    }
  }

  function autoScroll() {
    if (!drag || !drag.moved) { frame = 0; return; }
    const bounds = list.getBoundingClientRect();
    if (drag.x >= bounds.left && drag.x <= bounds.right && drag.y >= bounds.top && drag.y <= bounds.bottom) {
      if (drag.y < bounds.top + 36) list.scrollTop -= 8;
      else if (drag.y > bounds.bottom - 36) list.scrollTop += 8;
    }
    markTarget();
    frame = requestAnimationFrame(autoScroll);
  }

  async function save(original, key, movedHandle) {
    const ordered = bagRows(key);
    const ids = ordered.map(row => row.dataset.itemId);
    const before = original.filter(row => row.dataset.bolsa === key).map(row => row.dataset.itemId);
    if (ids.every((id, i) => id === before[i])) {
      movedHandle.focus({preventScroll: true});
      return;
    }
    saving = true;
    toggle.disabled = true;
    for (const tab of tabs) tab.disabled = true;
    for (const handle of handles) handle.disabled = true;
    report('Salvando ordem...');
    try {
      const response = await fetch(root.dataset.ordemUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
        body: JSON.stringify({bolsa: key, itens: ids}),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.ok !== true) throw new Error(result.erro || 'Não foi possível salvar a ordem.');
      report('Ordem salva.');
    } catch (error) {
      for (const row of original) list.append(row);
      report(error.message + ' A ordem anterior foi restaurada.');
    } finally {
      saving = false;
      toggle.disabled = false;
      for (const tab of tabs) tab.disabled = false;
      for (const handle of handles) handle.disabled = false;
      movedHandle.focus({preventScroll: true});
    }
  }

  toggle.addEventListener('click', () => mode(!editing));
  for (const tab of tabs) tab.addEventListener('click', () => {
    if (editing && !saving) mode(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !editing || saving) return;
    if (drag) clearDrag();
    else if (!document.querySelector('dialog[open]')) mode(false);
  });

  for (const handle of handles) {
    const row = handle.closest('[data-item-id]');
    handle.addEventListener('pointerdown', event => {
      if (!editing || saving || drag || !event.isPrimary || event.button !== 0) return;
      event.preventDefault();
      handle.focus({preventScroll: true});
      drag = {row, handle, pointer: event.pointerId, key: bag(),
              x: event.clientX, y: event.clientY,
              startX: event.clientX, startY: event.clientY, moved: false, target: null};
      handle.setPointerCapture(event.pointerId);
    });
    handle.addEventListener('pointermove', event => {
      if (drag?.pointer !== event.pointerId || drag.handle !== handle) return;
      drag.x = event.clientX;
      drag.y = event.clientY;
      if (!drag.moved && Math.hypot(drag.x - drag.startX, drag.y - drag.startY) >= 5) {
        drag.moved = true;
        row.classList.add('inventario-ordem-arrastando');
        frame = requestAnimationFrame(autoScroll);
      }
      if (drag.moved) markTarget();
    });
    handle.addEventListener('pointerup', event => {
      if (drag?.pointer !== event.pointerId || drag.handle !== handle) return;
      drag.x = event.clientX;
      drag.y = event.clientY;
      markTarget();
      const {target, after, key, moved} = drag;
      clearDrag();
      if (!moved || !target || bag() !== key) return;
      const original = rows();
      if (after) target.after(row); else target.before(row);
      save(original, key, handle);
    });
    handle.addEventListener('pointercancel', clearDrag);
    handle.addEventListener('lostpointercapture', () => {
      if (drag?.handle === handle) clearDrag();
    });
    handle.addEventListener('keydown', event => {
      if (!editing || saving || !['ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const key = bag();
      const items = bagRows(key);
      const index = items.indexOf(row);
      const direction = event.key === 'ArrowUp' ? -1 : 1;
      const target = items[index + direction];
      if (!target) return;
      const original = rows();
      if (direction < 0) target.before(row); else target.after(row);
      save(original, key, handle);
    });
  }
})();
