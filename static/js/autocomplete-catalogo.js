(() => {
    const campos = [...document.querySelectorAll('[data-autocomplete-url][list]')];
    if (!campos.length) return;

    const cache = new Map();
    const timers = new WeakMap();
    const controladores = new WeakMap();

    const preencher = (campo, itens) => {
        const lista = document.getElementById(campo.getAttribute('list'));
        if (!lista) return;
        lista.replaceChildren(...itens.map((item) => {
            const option = document.createElement('option');
            option.value = item.valor || item.rotulo || '';
            if (item.detalhe) option.label = `${item.rotulo || item.valor} — ${item.detalhe}`;
            return option;
        }));
    };

    const pesquisar = async (campo) => {
        const termo = campo.value.trim();
        const endpoint = campo.dataset.autocompleteUrl;
        if (!endpoint) return;
        if (termo.length < 1) {
            preencher(campo, []);
            return;
        }
        const url = new URL(endpoint, window.location.origin);
        url.searchParams.set('q', termo);
        const chave = url.toString();
        if (cache.has(chave)) {
            preencher(campo, cache.get(chave));
            return;
        }
        controladores.get(campo)?.abort();
        const controlador = new AbortController();
        controladores.set(campo, controlador);
        try {
            const resposta = await fetch(chave, {
                signal: controlador.signal,
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'fetch' },
            });
            if (!resposta.ok) return;
            const dados = await resposta.json();
            const itens = Array.isArray(dados.itens) ? dados.itens : [];
            cache.set(chave, itens);
            preencher(campo, itens);
        } catch (erro) {
            if (erro.name !== 'AbortError') console.warn('Falha no autocomplete do catálogo.', erro);
        }
    };

    campos.forEach((campo) => {
        campo.addEventListener('input', () => {
            window.clearTimeout(timers.get(campo));
            timers.set(campo, window.setTimeout(() => pesquisar(campo), 220));
        });
        campo.addEventListener('focus', () => {
            if (campo.value.trim()) pesquisar(campo);
        });
    });
})();
