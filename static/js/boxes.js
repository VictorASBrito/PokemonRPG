(() => {
    const nome = document.querySelector('#filtro-box-nome');
    const tipo = document.querySelector('#filtro-box-tipo');
    const shiny = document.querySelector('#filtro-box-shiny');
    const limpar = document.querySelector('#limpar-filtros-box');
    const resultado = document.querySelector('#resultado-filtro-box');
    const grade = document.querySelector('#grade-box-unica');
    const cards = Array.from(document.querySelectorAll('[data-box-pokemon-card]'));
    const slotsVazios = Array.from(document.querySelectorAll('[data-box-slot-vazio]'));

    const normalizar = (valor) => (valor || '')
        .toLocaleLowerCase('pt-BR')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim();

    const pontuacaoNome = (card, termo) => {
        if (!termo) return 0;
        const texto = normalizar(card.dataset.nome);
        if (texto === termo) return 0;
        if (texto.startsWith(termo)) return 1;

        const palavras = texto.split(/\s+/);
        if (palavras.some((palavra) => palavra.startsWith(termo))) return 2;
        if (texto.includes(termo)) return 3;
        return 4;
    };

    const atualizar = () => {
        const termoNome = normalizar(nome?.value);
        const termoTipo = normalizar(tipo?.value);
        const somenteShiny = Boolean(shiny?.checked);
        let correspondenciasNome = 0;
        let visiveis = 0;

        const ordenados = [...cards].sort((a, b) => {
            const diferenca = pontuacaoNome(a, termoNome) - pontuacaoNome(b, termoNome);
            if (diferenca !== 0) return diferenca;
            return Number(a.dataset.ordem || 0) - Number(b.dataset.ordem || 0);
        });

        ordenados.forEach((card) => {
            const nomeCorresponde = !termoNome || pontuacaoNome(card, termoNome) < 4;
            const tipoCorresponde = !termoTipo || normalizar(card.dataset.tipos).includes(termoTipo);
            const shinyCorresponde = !somenteShiny || card.dataset.shiny === 'sim';

            // A pesquisa por nome prioriza correspondências, mas mantém os demais
            // Pokémon logo depois. Tipo e Shiny continuam funcionando como filtros.
            card.hidden = !(tipoCorresponde && shinyCorresponde);
            card.classList.toggle('pokemon-pesquisa-correspondente', Boolean(termoNome && nomeCorresponde));
            card.classList.toggle('pokemon-pesquisa-secundario', Boolean(termoNome && !nomeCorresponde));

            if (!card.hidden) {
                visiveis += 1;
                if (nomeCorresponde) correspondenciasNome += 1;
            }
            grade?.appendChild(card);
        });

        // Os espaços vazios permanecem sempre depois de todos os Pokémon.
        slotsVazios.forEach((slot) => grade?.appendChild(slot));

        if (resultado) {
            if (termoNome) {
                resultado.textContent = correspondenciasNome > 0
                    ? `${correspondenciasNome} correspondência${correspondenciasNome === 1 ? '' : 's'} priorizada${correspondenciasNome === 1 ? '' : 's'} no início da Box.`
                    : 'Nenhum nome correspondente. Os Pokémon permanecem na ordem atual.';
            } else if (termoTipo || somenteShiny) {
                resultado.textContent = `${visiveis} Pokémon ${visiveis === 1 ? 'visível' : 'visíveis'} com os filtros atuais.`;
            } else {
                resultado.textContent = '';
            }
        }
    };

    [nome, tipo, shiny].forEach((campo) => {
        campo?.addEventListener('input', atualizar);
        campo?.addEventListener('change', atualizar);
    });

    limpar?.addEventListener('click', () => {
        if (nome) nome.value = '';
        if (tipo) tipo.value = '';
        if (shiny) shiny.checked = false;
        atualizar();
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

    atualizar();
})();
