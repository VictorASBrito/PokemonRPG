(() => {
    const nome = document.querySelector('#filtro-box-nome');
    const tipo = document.querySelector('#filtro-box-tipo');
    const nivel = document.querySelector('#filtro-box-nivel');
    const shiny = document.querySelector('#filtro-box-shiny');
    const limpar = document.querySelector('#limpar-filtros-box');
    const resultado = document.querySelector('#resultado-filtro-box');
    const cards = Array.from(document.querySelectorAll('[data-pokemon-card]'));

    const normalizar = (valor) => (valor || '')
        .toLocaleLowerCase('pt-BR')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');

    const filtrar = () => {
        const termoNome = normalizar(nome?.value);
        const termoTipo = normalizar(tipo?.value);
        const nivelMinimo = Number.parseInt(nivel?.value || '0', 10) || 0;
        const somenteShiny = Boolean(shiny?.checked);
        let visiveis = 0;

        cards.forEach((card) => {
            const corresponde = normalizar(card.dataset.nome).includes(termoNome)
                && normalizar(card.dataset.tipos).includes(termoTipo)
                && Number.parseInt(card.dataset.nivel || '0', 10) >= nivelMinimo
                && (!somenteShiny || card.dataset.shiny === 'sim');
            card.hidden = !corresponde;
            if (corresponde) visiveis += 1;
        });

        if (resultado) {
            const filtroAtivo = termoNome || termoTipo || nivelMinimo || somenteShiny;
            resultado.textContent = filtroAtivo
                ? `${visiveis} Pokémon encontrado${visiveis === 1 ? '' : 's'}.`
                : '';
        }
    };

    [nome, tipo, nivel, shiny].forEach((campo) => {
        campo?.addEventListener('input', filtrar);
        campo?.addEventListener('change', filtrar);
    });

    limpar?.addEventListener('click', () => {
        if (nome) nome.value = '';
        if (tipo) tipo.value = '';
        if (nivel) nivel.value = '';
        if (shiny) shiny.checked = false;
        filtrar();
        nome?.focus();
    });

    document.querySelectorAll('[data-abrir-renomear]').forEach((botao) => {
        botao.addEventListener('click', () => {
            const id = botao.dataset.abrirRenomear;
            const formulario = document.querySelector(`#renomear-${CSS.escape(id)}`);
            if (formulario) {
                formulario.hidden = false;
                formulario.querySelector('input')?.focus();
            }
        });
    });

    document.querySelectorAll('[data-fechar-renomear]').forEach((botao) => {
        botao.addEventListener('click', () => {
            const id = botao.dataset.fecharRenomear;
            const formulario = document.querySelector(`#renomear-${CSS.escape(id)}`);
            if (formulario) formulario.hidden = true;
        });
    });

    document.querySelectorAll('[data-confirmacao]').forEach((formulario) => {
        formulario.addEventListener('submit', (evento) => {
            const mensagem = formulario.dataset.confirmacao;
            if (mensagem && !window.confirm(mensagem)) evento.preventDefault();
        });
    });
})();
