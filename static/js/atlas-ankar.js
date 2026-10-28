/* Busca e filtros exclusivamente visuais; não altera dados de Ankar. */
(() => {
  'use strict';
  const input = document.getElementById('ankar-pesquisa');
  const container = document.getElementById('ankar-locais');
  if (!input || !container) return;
  const cards = [...container.querySelectorAll('.ankar-local')];
  const botoes = [...document.querySelectorAll('[data-tipo].ankar-opcao')];
  const contador = document.getElementById('ankar-contador');
  const vazio = document.getElementById('ankar-vazio');
  let tipoAtivo = 'todos';
  const normalizar = (valor) => String(valor || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const filtrar = () => {
    const termo = normalizar(input.value.trim());
    let visiveis = 0;
    for (const card of cards) {
      const categoriaOk = tipoAtivo === 'todos' || card.dataset.tipo === tipoAtivo;
      const textoOk = !termo || normalizar(card.dataset.busca).includes(termo);
      const mostra = categoriaOk && textoOk;
      card.hidden = !mostra;
      if (mostra) visiveis += 1;
    }
    if (contador) contador.textContent = `${visiveis} ${visiveis === 1 ? 'local' : 'locais'}`;
    if (vazio) vazio.hidden = visiveis !== 0;
  };
  input.addEventListener('input', filtrar);
  for (const botao of botoes) botao.addEventListener('click', () => {
    tipoAtivo = botao.dataset.tipo;
    for (const outro of botoes) {
      const selecionado = outro === botao;
      outro.classList.toggle('ativo', selecionado);
      outro.setAttribute('aria-pressed', String(selecionado));
    }
    filtrar();
  });
  filtrar();
})();

/* Mapa original de Ankar: visualização progressiva, sem chamadas à API ou escrita. */
(() => {
  'use strict';
  const viewport = document.getElementById('ankar-mapa-viewport');
  const plano = document.getElementById('ankar-mapa-plano');
  if (!viewport || !plano) return;

  const pontos = [...plano.querySelectorAll('[data-mapa-id]')];
  const botoes = [...document.querySelectorAll('[data-mapa-tipo]')];
  const nome = document.getElementById('ankar-mapa-info-nome');
  const detalhes = document.getElementById('ankar-mapa-info-detalhes');
  const link = document.getElementById('ankar-mapa-info-link');
  const visorZoom = document.getElementById('ankar-mapa-zoom-valor');
  let categoria = 'rota';
  let escala = 1;
  let selecionado = null;
  const ajustarLargura = () => {
    plano.style.setProperty('--ankar-mapa-base', `${Math.max(820, viewport.clientWidth)}px`);
  };
  ajustarLargura();
  window.addEventListener('resize', ajustarLargura);
  const clamp = (valor, minimo, maximo) => Math.min(maximo, Math.max(minimo, valor));

  function situar(ponto, suave = false) {
    if (!ponto || ponto.hidden) return;
    const x = parseFloat(ponto.style.getPropertyValue('--x')) / 100;
    const y = parseFloat(ponto.style.getPropertyValue('--y')) / 100;
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    viewport.scrollTo({
      left: clamp(plano.offsetWidth * x - viewport.clientWidth / 2, 0,
        Math.max(0, viewport.scrollWidth - viewport.clientWidth)),
      top: clamp(plano.offsetHeight * y - viewport.clientHeight / 2, 0,
        Math.max(0, viewport.scrollHeight - viewport.clientHeight)),
      behavior: suave && !window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'smooth' : 'auto',
    });
  }

  function selecionar(ponto, centralizar = false) {
    if (!ponto || ponto.hidden) return;
    if (selecionado) selecionado.removeAttribute('aria-current');
    selecionado = ponto;
    selecionado.setAttribute('aria-current', 'location');
    nome.textContent = ponto.dataset.mapaNome;
    const numero = ponto.dataset.mapaNumero;
    const tipo = ponto.dataset.mapaTipoPonto === 'rota' ? 'Rota' :
      (ponto.dataset.mapaTipoPonto === 'cidade' ? 'Cidade' : 'Ponto de interesse');
    const hab = ponto.dataset.mapaHabitat && ponto.dataset.mapaHabitat !== '-' ? ponto.dataset.mapaHabitat : 'Habitat não informado';
    detalhes.textContent = `${tipo} ${numero} no mapa · ${hab} · ${ponto.dataset.mapaPokemons} Pokémon distintos no catálogo.`;
    link.href = ponto.href;
    link.hidden = false;
    if (centralizar) situar(ponto, true);
  }

  function mostrarCategoria(tipo) {
    categoria = tipo;
    for (const ponto of pontos) ponto.hidden = ponto.dataset.mapaTipoPonto !== categoria;
    for (const botao of botoes) {
      const ativo = botao.dataset.mapaTipo === categoria;
      botao.classList.toggle('ativo', ativo);
      botao.setAttribute('aria-pressed', String(ativo));
    }
    if (selecionado && selecionado.hidden) {
      selecionado.removeAttribute('aria-current');
      selecionado = null;
      nome.textContent = 'Escolha um ponto no mapa';
      detalhes.textContent = 'Selecione um número para identificar o local correspondente.';
      link.hidden = true;
    }
  }

  for (const botao of botoes) botao.addEventListener('click', () => mostrarCategoria(botao.dataset.mapaTipo));

  for (const ponto of pontos) {
    ponto.addEventListener('click', event => {
      // Permite abrir normalmente com Ctrl, Cmd, Shift, botão do meio ou segundo clique.
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0 || ponto === selecionado) return;
      event.preventDefault();
      selecionar(ponto);
      if (window.matchMedia('(max-width: 700px)').matches) {
        document.getElementById('ankar-mapa-info')?.scrollIntoView({block: 'nearest', behavior: 'auto'});
      }
    });
  }

  function zoom(novaEscala) {
    const anterior = escala;
    escala = clamp(Number(novaEscala), 0.7, 2.5);
    if (escala === anterior) return;
    const centroX = (viewport.scrollLeft + viewport.clientWidth / 2) / plano.offsetWidth;
    const centroY = (viewport.scrollTop + viewport.clientHeight / 2) / plano.offsetHeight;
    plano.style.setProperty('--ankar-mapa-escala', String(escala));
    if (visorZoom) visorZoom.textContent = `${Math.round(escala * 100)}%`;
    viewport.scrollLeft = centroX * plano.offsetWidth - viewport.clientWidth / 2;
    viewport.scrollTop = centroY * plano.offsetHeight - viewport.clientHeight / 2;
  }

  for (const botao of document.querySelectorAll('[data-mapa-zoom]')) {
    botao.addEventListener('click', () => {
      const acao = botao.dataset.mapaZoom;
      if (acao === 'centralizar') { if (selecionado) situar(selecionado, true); else {viewport.scrollTop = 0; viewport.scrollLeft = 0;} return; }
      zoom(escala + (acao === 'mais' ? 0.25 : -0.25));
    });
  }

  // Acesso direto do detalhe: ?local=rota-1#ankar-mapa (valida against DOM ids).
  const preselecionado = new URLSearchParams(window.location.search).get('local');
  if (preselecionado) {
    const ponto = pontos.find(p => p.dataset.mapaId === preselecionado);
    if (ponto) {
      mostrarCategoria(ponto.dataset.mapaTipoPonto);
      selecionar(ponto);
      window.requestAnimationFrame(() => situar(ponto));
    }
  }
})();
