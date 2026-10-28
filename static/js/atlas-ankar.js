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
