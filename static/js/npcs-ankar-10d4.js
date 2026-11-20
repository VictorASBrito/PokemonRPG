/* Formulário de NPCs: selects dependentes do Atlas versionado. */
(() => {
  'use strict';
  const json = document.getElementById('npcs-dados-ankar');
  const pagina = document.querySelector('[data-npcs-ankar]');
  if (!json || !pagina) return;
  const locais = JSON.parse(json.textContent || '[]');
  const local = document.getElementById('npc-local');
  const zona = document.getElementById('npc-zona');
  const terreno = document.getElementById('npc-tabela');
  const tipo = document.getElementById('npc-tipo');
  const encontrador = document.getElementById('npc-encontrador');
  const blocoEncontrador = document.querySelector('[data-npc-encontrador]');
  const popular = (select, itens, chave, inicio) => {
    select.replaceChildren();
    select.add(new Option(inicio, ''));
    itens.forEach((item, indice) => select.add(new Option(item[chave], String(indice))));
    select.disabled = !itens.length;
  };
  const atualizarTerrenos = () => {
    const l = locais.find(x => x.id === local.value);
    const z = l?.zonas?.[Number(zona.value)];
    popular(terreno, z?.tabelas || [], 'terreno', 'Selecione o terreno');
  };
  const atualizarZonas = () => {
    const l = locais.find(x => x.id === local.value);
    popular(zona, l?.zonas || [], 'nome', 'Selecione a zona');
    popular(terreno, [], 'terreno', 'Selecione a zona primeiro');
  };
  local?.addEventListener('change', atualizarZonas);
  zona?.addEventListener('change', atualizarTerrenos);
  const atualizarTipo = () => {
    const horda = tipo.value === 'horda';
    blocoEncontrador.hidden = !horda;
    encontrador.required = horda;
  };
  tipo?.addEventListener('change', atualizarTipo);
  atualizarTipo();
  document.querySelectorAll('[data-npc-arquivar]').forEach(form => {
    form.addEventListener('submit', ev => {
      if (!window.confirm('Arquivar este NPC fixo? O modelo deixará o catálogo, mas instâncias no Campo serão mantidas.')) {
        ev.preventDefault();
      }
    });
  });
})();
