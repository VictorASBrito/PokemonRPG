/* Capturáveis · UI progressiva; nenhum dado de captura é alterado no navegador. */
(() => {
    'use strict';
    const mestre = document.querySelector('[data-capturas-mestre]');
    const carrossel = document.querySelector('[data-captura-carrossel]');

    if (mestre) {
        const cards = [...mestre.querySelectorAll('[data-captura-card]')];
        const nome = mestre.querySelector('[data-filtro-nome]');
        const treinador = mestre.querySelector('[data-filtro-treinador]');
        const shiny = mestre.querySelector('[data-filtro-shiny]');
        const contador = mestre.querySelector('[data-captura-contador]');
        const vazio = mestre.querySelector('[data-filtro-vazio]');
        const atualizar = () => {
            const busca = (nome?.value || '').trim().toLocaleLowerCase('pt-BR');
            let visiveis = 0;
            cards.forEach((card) => {
                const corresponde = (!busca || card.dataset.nome.includes(busca)) &&
                    (!treinador?.value || card.dataset.encontrador === treinador.value) &&
                    (!shiny?.checked || card.dataset.shiny === '1');
                card.hidden = !corresponde;
                if (corresponde) visiveis += 1;
            });
            if (contador) contador.textContent = `${visiveis} de ${cards.length} exibidos`;
            if (vazio) vazio.hidden = visiveis !== 0;
        };
        nome?.addEventListener('input', atualizar);
        treinador?.addEventListener('change', atualizar);
        shiny?.addEventListener('change', atualizar);

        const campo = mestre.querySelector('#forma_nome');
        const previa = mestre.querySelector('[data-captura-previa]');
        const sprite = mestre.querySelector('[data-previa-sprite]');
        const texto = mestre.querySelector('[data-previa-nome]');
        const tipos = mestre.querySelector('[data-previa-tipos]');
        campo?.addEventListener('catalogo:selecionado', (evento) => {
            const item = evento.detail?.item;
            if (!item || !previa || !sprite || !texto || !tipos) return;
            texto.textContent = item.rotulo || item.valor || '';
            sprite.replaceChildren();
            tipos.replaceChildren();
            if (typeof item.imagem === 'string' && item.imagem) {
                try {
                    const url = new URL(item.imagem, location.origin);
                    if (url.protocol === 'http:' || url.protocol === 'https:') {
                        const imagem = document.createElement('img');
                        imagem.src = url.href;
                        imagem.alt = '';
                        sprite.append(imagem);
                    }
                } catch (_erro) { /* Imagem opcional. */ }
            }
            for (const tipo of Array.isArray(item.tipos) ? item.tipos : []) {
                const selo = document.createElement('span');
                selo.className = 'etiqueta-tipo';
                selo.textContent = tipo.nome || '';
                tipos.append(selo);
            }
            previa.hidden = false;
        });
        campo?.addEventListener('input', () => { if (previa) previa.hidden = true; });
        atualizar();
    }

    if (!carrossel) return;
    const slides = [...carrossel.querySelectorAll('[data-carousel-slide]')];
    if (!slides.length) return;
    const miniaturas = [...carrossel.querySelectorAll('[data-carousel-miniatura]')];
    const filtro = carrossel.querySelector('[data-carousel-filtro]');
    const escolher = carrossel.querySelector('[data-carousel-selecionar]');
    const anterior = carrossel.querySelector('[data-carousel-anterior]');
    const proximo = carrossel.querySelector('[data-carousel-proximo]');
    const status = carrossel.querySelector('[data-carousel-status]');
    const meuId = carrossel.dataset.meuPersonagem || '';
    let filtrados = [];
    let indice = 0;

    const visiveisDoFiltro = () => {
        const valor = filtro?.value || 'todos';
        return slides.filter((slide) =>
            valor === 'todos' ||
            (valor === 'meus' && !!meuId && slide.dataset.encontrador === meuId) ||
            slide.dataset.encontrador === valor
        );
    };
    const mostrar = (novoIndice) => {
        if (!filtrados.length) return;
        indice = (novoIndice + filtrados.length) % filtrados.length;
        const atual = filtrados[indice];
        slides.forEach((slide) => { slide.hidden = slide !== atual; });
        miniaturas.forEach((mini) => {
            mini.hidden = !filtrados.some((slide) => slide.dataset.id === mini.dataset.id);
            mini.setAttribute('aria-current', mini.dataset.id === atual.dataset.id ? 'true' : 'false');
        });
        if (status) status.textContent = `${indice + 1} de ${filtrados.length} Pokémon`;
        if (escolher) escolher.value = atual.dataset.id;
        if (anterior) anterior.disabled = filtrados.length <= 1;
        if (proximo) proximo.disabled = filtrados.length <= 1;
    };
    const aplicarFiltro = (preferidoId = '') => {
        filtrados = visiveisDoFiltro();
        if (!filtrados.length) {
            if (filtro) filtro.value = 'todos';
            filtrados = visiveisDoFiltro();
        }
        const preferido = filtrados.findIndex((slide) => slide.dataset.id === preferidoId);
        mostrar(preferido >= 0 ? preferido : 0);
    };
    if (!meuId || !slides.some((slide) => slide.dataset.encontrador === meuId)) {
        if (filtro) filtro.value = 'todos';
    }
    anterior?.addEventListener('click', () => mostrar(indice - 1));
    proximo?.addEventListener('click', () => mostrar(indice + 1));
    filtro?.addEventListener('change', () => aplicarFiltro());
    escolher?.addEventListener('change', () => {
        const destino = slides.find((slide) => slide.dataset.id === escolher.value);
        if (!destino) return;
        if (!filtrados.includes(destino) && filtro) filtro.value = 'todos';
        aplicarFiltro(destino.dataset.id);
    });
    miniaturas.forEach((mini) => mini.addEventListener('click', () => {
        const posicao = filtrados.findIndex((slide) => slide.dataset.id === mini.dataset.id);
        if (posicao >= 0) mostrar(posicao);
    }));
    carrossel.addEventListener('keydown', (evento) => {
        if (!['ArrowLeft','ArrowRight'].includes(evento.key) ||
            ['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName)) return;
        evento.preventDefault();
        mostrar(indice + (evento.key === 'ArrowRight' ? 1 : -1));
    });
    aplicarFiltro();
    carrossel.dataset.carouselReady = 'true';
})();
