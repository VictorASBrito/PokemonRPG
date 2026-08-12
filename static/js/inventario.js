(() => {
    const pesquisa = document.querySelector('#pesquisa-inventario');
    const cards = [...document.querySelectorAll('.inventario-item')];
    const vazio = document.querySelector('#inventario-sem-resultados');
    const filtros = [...document.querySelectorAll('.filtro-inventario')];
    let filtroAtual = 'todos';

    const normalizar = (texto) => (texto || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase();

    const aplicar = () => {
        const termo = normalizar(pesquisa?.value);
        let visiveis = 0;
        cards.forEach((card) => {
            const correspondeTexto = normalizar(card.dataset.nome).includes(termo);
            const correspondeFiltro = filtroAtual === 'todos'
                || (filtroAtual === 'consumivel' && card.dataset.consumivel === '1')
                || (filtroAtual === 'equipavel' && card.dataset.equipavel === '1');
            const mostrar = correspondeTexto && correspondeFiltro;
            card.hidden = !mostrar;
            if (mostrar) visiveis += 1;
        });
        if (vazio) vazio.hidden = visiveis > 0;
    };

    pesquisa?.addEventListener('input', aplicar);
    filtros.forEach((botao) => botao.addEventListener('click', () => {
        filtroAtual = botao.dataset.filtro || 'todos';
        filtros.forEach((item) => item.classList.toggle('ativo', item === botao));
        aplicar();
    }));
})();
