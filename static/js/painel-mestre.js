(() => {
    const pesquisa = document.querySelector('#pesquisa-painel-mestre');
    const containerJogadores = document.querySelector('#painel-mestre-jogadores');
    const filtros = [...document.querySelectorAll('.filtro-painel-mestre')];
    const resultado = document.querySelector('#resultado-pesquisa-painel');
    const vazio = document.querySelector('#painel-mestre-sem-resultados');
    const mensagem = document.querySelector('#mensagem-painel-mestre');
    const alternarOrdem = document.querySelector('#alternar-ordem-painel');
    const concluirOrdem = document.querySelector('#concluir-ordem-painel');
    const ajudaOrdem = document.querySelector('#painel-mestre-ordem-ajuda');
    let filtroAtual = 'todos';
    let modoOrdenacao = false;
    let cardArrastado = null;
    let ordemAlteradaNoArraste = false;
    let filaSalvamento = Promise.resolve();

    const cards = () => [...document.querySelectorAll('[data-painel-jogador]')];

    const normalizar = (valor) => (valor || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLocaleLowerCase('pt-BR')
        .trim();

    const aplicarPesquisa = () => {
        const itens = cards();
        const termo = normalizar(pesquisa?.value);
        let visiveis = 0;
        itens.forEach((card) => {
            const busca = normalizar(card.dataset.busca);
            const textoOk = !termo || busca.includes(termo);
            const filtroOk = filtroAtual === 'todos' || card.dataset.temAlertas === '1';
            const mostrar = textoOk && filtroOk;
            card.hidden = !mostrar;
            if (mostrar) visiveis += 1;
        });
        if (resultado) {
            resultado.textContent = itens.length
                ? `${visiveis} de ${itens.length} jogador${itens.length === 1 ? '' : 'es'} visível${visiveis === 1 ? '' : 'is'}.`
                : '';
        }
        if (vazio) vazio.hidden = visiveis > 0;
    };

    pesquisa?.addEventListener('input', aplicarPesquisa);
    filtros.forEach((botao) => botao.addEventListener('click', () => {
        if (modoOrdenacao) return;
        filtroAtual = botao.dataset.filtro || 'todos';
        filtros.forEach((item) => item.classList.toggle('ativo', item === botao));
        aplicarPesquisa();
    }));

    const mostrarMensagem = (texto, erro = false) => {
        if (!mensagem) return;
        mensagem.textContent = texto;
        mensagem.classList.toggle('painel-mestre-mensagem-erro', erro);
        window.clearTimeout(mostrarMensagem.timer);
        mostrarMensagem.timer = window.setTimeout(() => {
            mensagem.textContent = '';
            mensagem.classList.remove('painel-mestre-mensagem-erro');
        }, 3500);
    };

    const atualizarNumerosOrdem = () => {
        cards().forEach((card, indice) => {
            const numero = card.querySelector('[data-ordem-numero]');
            if (numero) numero.textContent = `#${indice + 1}`;
            const cima = card.querySelector('[data-mover-ordem="cima"]');
            const baixo = card.querySelector('[data-mover-ordem="baixo"]');
            if (cima) cima.disabled = indice === 0;
            if (baixo) baixo.disabled = indice === cards().length - 1;
        });
    };

    const obterOrdem = () => cards().map((card) => card.dataset.personagemId).filter(Boolean);

    const salvarOrdem = () => {
        if (!containerJogadores?.dataset.ordemUrl) return;
        const ordem = obterOrdem();
        filaSalvamento = filaSalvamento.then(async () => {
            const resposta = await fetch(containerJogadores.dataset.ordemUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'fetch',
                },
                body: JSON.stringify({ ordem }),
                credentials: 'same-origin',
            });
            const dados = await resposta.json();
            if (!resposta.ok) throw new Error(dados.erro || 'Não foi possível salvar a ordem.');
            mostrarMensagem('Ordem dos jogadores salva.');
        }).catch((erro) => {
            mostrarMensagem(erro.message || 'Não foi possível salvar a ordem.', true);
        });
    };

    const entrarModoOrdenacao = () => {
        if (!containerJogadores) return;
        modoOrdenacao = true;
        filtroAtual = 'todos';
        if (pesquisa) {
            pesquisa.value = '';
            pesquisa.disabled = true;
        }
        filtros.forEach((item) => {
            item.disabled = true;
            item.classList.toggle('ativo', item.dataset.filtro === 'todos');
        });
        cards().forEach((card) => {
            card.hidden = false;
            card.draggable = true;
        });
        containerJogadores.classList.add('modo-ordenacao');
        if (ajudaOrdem) ajudaOrdem.hidden = false;
        if (alternarOrdem) {
            alternarOrdem.textContent = 'Ordenando jogadores…';
            alternarOrdem.disabled = true;
        }
        if (vazio) vazio.hidden = true;
        atualizarNumerosOrdem();
        if (resultado) resultado.textContent = 'Ordem de exibição ativa. Arraste os cartões ou use as setas.';
    };

    const sairModoOrdenacao = () => {
        modoOrdenacao = false;
        if (pesquisa) pesquisa.disabled = false;
        filtros.forEach((item) => { item.disabled = false; });
        cards().forEach((card) => { card.draggable = false; });
        containerJogadores?.classList.remove('modo-ordenacao');
        if (ajudaOrdem) ajudaOrdem.hidden = true;
        if (alternarOrdem) {
            alternarOrdem.textContent = 'Definir ordem';
            alternarOrdem.disabled = false;
        }
        aplicarPesquisa();
    };

    alternarOrdem?.addEventListener('click', entrarModoOrdenacao);
    concluirOrdem?.addEventListener('click', sairModoOrdenacao);

    containerJogadores?.addEventListener('click', (evento) => {
        if (!modoOrdenacao) return;
        const link = evento.target.closest('a');
        if (link) {
            evento.preventDefault();
            return;
        }
        const botao = evento.target.closest('[data-mover-ordem]');
        if (!botao) return;
        const card = botao.closest('[data-painel-jogador]');
        if (!card) return;
        if (botao.dataset.moverOrdem === 'cima') {
            const anterior = card.previousElementSibling;
            if (anterior) containerJogadores.insertBefore(card, anterior);
        } else {
            const proximo = card.nextElementSibling;
            if (proximo) containerJogadores.insertBefore(proximo, card);
        }
        atualizarNumerosOrdem();
        salvarOrdem();
    });

    containerJogadores?.addEventListener('dragstart', (evento) => {
        if (!modoOrdenacao) {
            evento.preventDefault();
            return;
        }
        const card = evento.target.closest('[data-painel-jogador]');
        if (!card) return;
        cardArrastado = card;
        ordemAlteradaNoArraste = false;
        card.classList.add('arrastando');
        evento.dataTransfer.effectAllowed = 'move';
        evento.dataTransfer.setData('text/plain', card.dataset.personagemId || '');
    });

    containerJogadores?.addEventListener('dragover', (evento) => {
        if (!modoOrdenacao || !cardArrastado) return;
        evento.preventDefault();
        const alvo = evento.target.closest('[data-painel-jogador]');
        if (!alvo || alvo === cardArrastado) return;
        const caixa = alvo.getBoundingClientRect();
        const inserirDepois = evento.clientY > caixa.top + (caixa.height / 2);
        const referencia = inserirDepois ? alvo.nextElementSibling : alvo;
        if (referencia !== cardArrastado) {
            containerJogadores.insertBefore(cardArrastado, referencia);
            ordemAlteradaNoArraste = true;
            atualizarNumerosOrdem();
        }
    });

    containerJogadores?.addEventListener('dragend', () => {
        if (!cardArrastado) return;
        cardArrastado.classList.remove('arrastando');
        cardArrastado = null;
        if (ordemAlteradaNoArraste) salvarOrdem();
        ordemAlteradaNoArraste = false;
    });

    document.querySelectorAll('[data-pv-form]').forEach((form) => {
        form.addEventListener('submit', async (evento) => {
            evento.preventDefault();
            const botao = evento.submitter;
            const delta = botao?.dataset.delta;
            if (!delta) return;
            const botoes = [...form.querySelectorAll('button')];
            botoes.forEach((item) => { item.disabled = true; });
            try {
                const resposta = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'X-Requested-With': 'fetch',
                    },
                    body: new URLSearchParams({ delta }),
                    credentials: 'same-origin',
                });
                const dados = await resposta.json();
                if (!resposta.ok) throw new Error(dados.erro || 'Não foi possível atualizar os PV.');
                const container = form.closest('[data-pv-container]');
                const valor = container?.querySelector('[data-pv-valor]');
                const progresso = container?.querySelector('[data-pv-progresso]');
                if (valor) valor.textContent = `${dados.pv_atual}/${dados.pv_maximo}`;
                if (progresso) {
                    progresso.max = dados.pv_maximo > 0 ? dados.pv_maximo : 1;
                    progresso.value = Math.max(0, dados.pv_atual);
                }
                mostrarMensagem(`PV atualizado: ${dados.pv_atual}/${dados.pv_maximo}.`);
            } catch (erro) {
                mostrarMensagem(erro.message || 'Não foi possível atualizar os PV.', true);
            } finally {
                botoes.forEach((item) => { item.disabled = false; });
            }
        });
    });

    atualizarNumerosOrdem();
    aplicarPesquisa();
})();
