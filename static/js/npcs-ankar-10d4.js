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
  const modo = document.getElementById('npc-modo');
  const quantidade = document.getElementById('npc-quantidade');
  const blocoManual = document.querySelector('[data-modo-manual]');
  const blocoAleatorio = document.querySelector('[data-modo-aleatorio]');
  const vagas = [...document.querySelectorAll('[data-npc-manual-vaga]')];
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
    const z = zona.value !== '' ? l?.zonas?.[Number(zona.value)] : null;
    popular(terreno, z?.tabelas || [], 'terreno', 'Todos os terrenos');
  };
  const atualizarZonas = () => {
    const l = locais.find(x => x.id === local.value);
    popular(zona, l?.zonas || [], 'nome', 'Todas as zonas');
    popular(terreno, [], 'terreno', 'Todos os terrenos');
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
  const atualizarModo = () => {
    const manual = modo.value === 'manual';
    blocoManual.hidden = !manual;
    blocoAleatorio.hidden = manual;
    for (let i = 0; i < vagas.length; i++) {
      const ativa = manual && i < Number(quantidade.value);
      vagas[i].hidden = !ativa;
      const campo = vagas[i].querySelector('input[type=search]');
      const id = vagas[i].querySelector('input[type=hidden]');
      campo.disabled = !ativa;
      campo.required = ativa;
      id.disabled = !ativa;
    }
  };
  modo.addEventListener('change', atualizarModo);
  quantidade.addEventListener('input', atualizarModo);
  atualizarModo();
  document.querySelectorAll('[data-npc-arquivar]').forEach(form => {
    form.addEventListener('submit', ev => {
      if (!window.confirm('Arquivar este NPC fixo? O modelo deixará o catálogo, mas instâncias no Campo serão mantidas.')) {
        ev.preventDefault();
      }
    });
  });
})();
