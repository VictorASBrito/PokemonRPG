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

/* Mapa de Ankar: pontos clicáveis sobre a arte, sem zoom ou scroll interno. */
(() => {
  'use strict';
  const plano = document.getElementById('ankar-mapa-plano');
  if (!plano) return;

  const pontos = [...plano.querySelectorAll('[data-mapa-id]')];
  const botoes = [...document.querySelectorAll('[data-mapa-tipo]')];
  const nome = document.getElementById('ankar-mapa-info-nome');
  const detalhes = document.getElementById('ankar-mapa-info-detalhes');
  const link = document.getElementById('ankar-mapa-info-link');
  let selecionado = null;

  function selecionar(ponto) {
    if (!ponto || ponto.hidden) return;
    if (selecionado) selecionado.removeAttribute('aria-current');
    selecionado = ponto;
    ponto.setAttribute('aria-current', 'location');
    nome.textContent = ponto.dataset.mapaNome;
    const tipo = ponto.dataset.mapaTipoPonto === 'rota' ? 'Rota' :
      (ponto.dataset.mapaTipoPonto === 'cidade' ? 'Cidade' : 'Ponto de interesse');
    const habitat = ponto.dataset.mapaHabitat && ponto.dataset.mapaHabitat !== '-'
      ? ponto.dataset.mapaHabitat : 'Habitat não informado';
    detalhes.textContent = `${tipo} ${ponto.dataset.mapaNumero} · ${habitat} · ${ponto.dataset.mapaPokemons} Pokémon distintos no catálogo.`;
    link.href = ponto.href;
    link.hidden = false;
  }

  function mostrarCategoria(tipo) {
    for (const ponto of pontos) ponto.hidden = tipo !== 'todos' && ponto.dataset.mapaTipoPonto !== tipo;
    for (const botao of botoes) {
      const ativo = botao.dataset.mapaTipo === tipo;
      botao.classList.toggle('ativo', ativo);
      botao.setAttribute('aria-pressed', String(ativo));
    }
    if (selecionado && selecionado.hidden) {
      selecionado.removeAttribute('aria-current');
      selecionado = null;
      nome.textContent = 'Escolha um ponto no mapa';
      detalhes.textContent = 'Selecione um número ou símbolo para identificar o local correspondente.';
      link.hidden = true;
    }
  }

  for (const botao of botoes) botao.addEventListener('click', () => mostrarCategoria(botao.dataset.mapaTipo));
  for (const ponto of pontos) {
    ponto.addEventListener('click', (event) => {
      // O primeiro clique mostra a ficha resumida; o segundo abre o detalhe.
      // Teclas modificadoras e outros botões mantêm o comportamento do link.
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0 || selecionado === ponto) return;
      event.preventDefault();
      selecionar(ponto);
    });
  }

  mostrarCategoria('todos');
  // Retorno das fichas: mantém seleção sem forçar zoom ou rolagem do mapa.
  const preselecionado = new URLSearchParams(window.location.search).get('local');
  if (preselecionado) {
    const ponto = pontos.find(p => p.dataset.mapaId === preselecionado);
    if (ponto) selecionar(ponto);
  }
})();

/* Etapa 10A.4 — geração com confirmação explícita e escolha de treinador. */
(() => {
  'use strict';
  const dialog = document.getElementById('ankar-gerar-dialog');
  if (!dialog) return;
  const etapaConfirmar = dialog.querySelector('[data-ankar-etapa="confirmar"]');
  const etapaJogador = dialog.querySelector('[data-ankar-etapa="jogador"]');
  const nome = document.getElementById('ankar-dialog-pokemon');
  const arte = document.getElementById('ankar-dialog-arte');
  const jogador = document.getElementById('ankar-encontrado-por');
  const abrir = botao => {
    nome.textContent = botao.dataset.pokemon;
    arte.replaceChildren();
    if (botao.dataset.imagem) {
      const img = document.createElement('img');
      img.src = botao.dataset.imagem;
      img.alt = '';
      img.onerror = () => img.remove();
      arte.append(img);
    } else arte.textContent = '◇';
    for (const campo of ['zona', 'tabela', 'indice']) {
      document.getElementById(`ankar-post-${campo}`).value = botao.dataset[campo];
    }
    jogador.value = '';
    etapaConfirmar.hidden = false;
    etapaJogador.hidden = true;
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  };
  document.querySelectorAll('[data-ankar-gerar]').forEach(botao => {
    botao.addEventListener('click', () => abrir(botao));
  });
  dialog.querySelectorAll('[data-ankar-fechar]').forEach(botao => {
    botao.addEventListener('click', () => dialog.close ? dialog.close() : dialog.removeAttribute('open'));
  });
  document.getElementById('ankar-confirmar-geracao').addEventListener('click', () => {
    etapaConfirmar.hidden = true;
    etapaJogador.hidden = false;
    jogador.focus();
  });
  document.getElementById('ankar-voltar-confirmacao').addEventListener('click', () => {
    etapaConfirmar.hidden = false;
    etapaJogador.hidden = true;
  });
  dialog.addEventListener('close', () => {
    etapaConfirmar.hidden = false;
    etapaJogador.hidden = true;
  });
})();
