/* Seletor visual compartilhado por espécies, golpes e itens.
   Mantém o campo original e seu name, para não alterar o contrato do backend.
   Não usa innerHTML para dados recebidos do catálogo. */
(() => {
    'use strict';
    const campos = [...document.querySelectorAll('[data-autocomplete-url][data-seletor-visual]')];
    if (!campos.length) return;

    const cache = new Map();
    const tiposPermitidos = new Set([
        'normal','fire','water','electric','grass','ice','fighting','poison','ground',
        'flying','psychic','bug','rock','ghost','dragon','dark','steel','fairy',
    ]);

    const criar = (tag, classe, texto) => {
        const elemento = document.createElement(tag);
        if (classe) elemento.className = classe;
        if (texto !== undefined) elemento.textContent = String(texto);
        return elemento;
    };

    const urlSegura = (valor) => {
        if (typeof valor !== 'string' || !valor || valor.length > 1024) return null;
        try {
            const url = new URL(valor, window.location.origin);
            return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
        } catch (_erro) { return null; }
    };

    campos.forEach((campo, indice) => {
        const alvo = campo.dataset.seletorAlvo
            ? document.getElementById(campo.dataset.seletorAlvo)
            : null;
        const tipo = campo.dataset.seletorVisual;
        const listaNativa = campo.getAttribute('list');
        const wrapper = criar('div', 'seletor-visual');
        campo.parentNode.insertBefore(wrapper, campo);
        wrapper.append(campo);
        // Mantém a marcação antiga para compatibilidade; o JS substitui sua UI.
        if (listaNativa) campo.removeAttribute('list');
        campo.setAttribute('role', 'combobox');
        campo.setAttribute('aria-autocomplete', 'list');
        campo.setAttribute('aria-expanded', 'false');
        campo.setAttribute('aria-haspopup', 'listbox');
        const painel = criar('div', 'seletor-visual-resultados');
        painel.id = `seletor-visual-${indice}`;
        painel.setAttribute('role', 'listbox');
        painel.hidden = true;
        campo.setAttribute('aria-controls', painel.id);
        wrapper.append(painel);
        let resultados = [];
        let atual = -1;
        let timer;
        let controlador;
        let requisicao = 0;
        let nomeSelecionado = '';

        const fechar = () => {
            painel.hidden = true;
            wrapper.classList.remove('seletor-visual-aberto');
            campo.setAttribute('aria-expanded', 'false');
            campo.removeAttribute('aria-activedescendant');
            atual = -1;
        };
        const abrir = () => {
            const retangulo = campo.getBoundingClientRect();
            painel.classList.toggle('seletor-visual-acima',
                window.innerHeight - retangulo.bottom < 240 && retangulo.top > 270);
            painel.hidden = false;
            wrapper.classList.add('seletor-visual-aberto');
            campo.setAttribute('aria-expanded', 'true');
        };
        const indicar = (i) => {
            const opcoes = [...painel.querySelectorAll('[role="option"]')];
            if (!opcoes.length) return;
            atual = (i + opcoes.length) % opcoes.length;
            opcoes.forEach((opcao, numero) => {
                opcao.setAttribute('aria-selected', numero === atual ? 'true' : 'false');
            });
            campo.setAttribute('aria-activedescendant', opcoes[atual].id);
            opcoes[atual].scrollIntoView({ block: 'nearest' });
        };
        const selecionar = (item) => {
            nomeSelecionado = String(item.rotulo || item.valor || '');
            campo.value = tipo === 'item' ? nomeSelecionado : String(item.valor || item.rotulo || '');
            if (alvo) alvo.value = String(item.valor || '');
            campo.setCustomValidity('');
            fechar();
            campo.dispatchEvent(new Event('change', { bubbles: true }));
            campo.focus({ preventScroll: true });
        };
        const linhaResultado = (item, i) => {
            const linha = criar('div', 'seletor-visual-opcao');
            linha.setAttribute('role', 'option');
            linha.id = `${painel.id}-opcao-${i}`;
            linha.setAttribute('aria-selected', 'false');
            const moldura = criar('span', 'seletor-visual-imagem');
            const src = urlSegura(item.imagem);
            if (src) {
                const imagem = criar('img');
                imagem.src = src;
                imagem.alt = '';
                imagem.loading = 'lazy';
                imagem.addEventListener('error', () => {
                    imagem.remove();
                    moldura.append(criar('span', 'seletor-visual-placeholder', tipo === 'item' ? '◆' : '◈'));
                }, { once: true });
                moldura.append(imagem);
            } else {
                const cor = item.tipos?.[0]?.codigo;
                if (tiposPermitidos.has(cor)) moldura.classList.add(`etiqueta-tipo--${cor}`);
                moldura.append(criar('span', 'seletor-visual-placeholder', tipo === 'pokemon' ? '◈' : tipo === 'golpe' ? '✦' : '◆'));
            }
            const bloco = criar('span', 'seletor-visual-textos');
            bloco.append(criar('strong', 'seletor-visual-titulo', item.rotulo || item.valor || ''));
            if (item.detalhe) bloco.append(criar('small', 'seletor-visual-detalhe', item.detalhe));
            if ((Array.isArray(item.tipos) && item.tipos.length) || (Array.isArray(item.tags) && item.tags.length)) {
                const chips = criar('span', 'seletor-visual-etiquetas');
                (item.tipos || []).forEach((t) => {
                    const codigo = tiposPermitidos.has(t.codigo) ? t.codigo : 'personalizado';
                    chips.append(criar('span', `etiqueta-tipo etiqueta-tipo--${codigo}`, t.nome || 'Sem tipo'));
                });
                (item.tags || []).forEach((texto) => {
                    chips.append(criar('span', 'seletor-visual-chip', texto));
                });
                bloco.append(chips);
            }
            linha.append(moldura, bloco);
            linha.addEventListener('pointerdown', (evento) => evento.preventDefault());
            linha.addEventListener('click', () => selecionar(item));
            linha.addEventListener('mouseenter', () => indicar(i));
            return linha;
        };
        const exibir = (itens, mensagem) => {
            resultados = itens;
            atual = -1;
            painel.replaceChildren();
            if (!itens.length) {
                painel.append(criar('div', 'seletor-visual-vazio', mensagem || 'Nenhuma correspondência encontrada.'));
            } else {
                itens.forEach((item, i) => painel.append(linhaResultado(item, i)));
            }
            abrir();
        };
        const pesquisar = async () => {
            const termo = campo.value.trim();
            const numero = ++requisicao;
            controlador?.abort();
            controlador = new AbortController();
            if (!termo && tipo !== 'item') {
                // Ajuda a descobrir Pokémon mesmo antes de informar o nome.
                exibir([], 'Digite para buscar no catálogo.');
                return;
            }
            const url = new URL(campo.dataset.autocompleteUrl, window.location.origin);
            url.searchParams.set('q', termo);
            const chave = url.toString();
            if (cache.has(chave)) {
                exibir(cache.get(chave));
                return;
            }
            exibir([], 'Pesquisando…');
            try {
                const resposta = await fetch(chave, {
                    signal: controlador.signal,
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'fetch' },
                });
                if (numero !== requisicao) return;
                if (!resposta.ok) throw new Error('Resposta indisponível');
                const dados = await resposta.json();
                if (numero !== requisicao) return;
                const itens = Array.isArray(dados.itens) ? dados.itens.slice(0, 50) : [];
                cache.set(chave, itens);
                if (cache.size > 100) cache.delete(cache.keys().next().value);
                exibir(itens);
            } catch (erro) {
                if (erro.name !== 'AbortError' && numero === requisicao)
                    exibir([], 'Não foi possível carregar o catálogo. Tente novamente.');
            }
        };
        campo.addEventListener('input', () => {
            ++requisicao;
            controlador?.abort();
            if (alvo) alvo.value = '';
            nomeSelecionado = '';
            campo.setCustomValidity('');
            clearTimeout(timer);
            timer = setTimeout(pesquisar, 200);
        });
        campo.addEventListener('focus', () => {
            clearTimeout(timer);
            timer = setTimeout(pesquisar, 100);
        });
        campo.addEventListener('keydown', (evento) => {
            if (evento.key === 'Escape') { requisicao++; controlador?.abort(); fechar(); return; }
            if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
                evento.preventDefault();
                if (painel.hidden) { pesquisar(); return; }
                indicar(atual + (evento.key === 'ArrowDown' ? 1 : -1));
            }
            if (evento.key === 'Enter' && !painel.hidden && atual >= 0 && resultados[atual]) {
                evento.preventDefault();
                selecionar(resultados[atual]);
            }
            if (evento.key === 'Tab') fechar();
        });
        document.addEventListener('pointerdown', (evento) => {
            if (!wrapper.contains(evento.target)) fechar();
        });
        if (alvo) {
            campo.closest('form')?.addEventListener('submit', (evento) => {
                if (!alvo.value || campo.value !== nomeSelecionado) {
                    evento.preventDefault();
                    campo.setCustomValidity('Selecione um item na lista de resultados.');
                    campo.reportValidity();
                }
            });
        }
    });
})();
