(() => {
    const pesquisa = document.querySelector('#pesquisa-painel-mestre');
    const cards = [...document.querySelectorAll('[data-painel-jogador]')];
    const filtros = [...document.querySelectorAll('.filtro-painel-mestre')];
    const resultado = document.querySelector('#resultado-pesquisa-painel');
    const vazio = document.querySelector('#painel-mestre-sem-resultados');
    const mensagem = document.querySelector('#mensagem-painel-mestre');
    let filtroAtual = 'todos';

    const normalizar = (valor) => (valor || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLocaleLowerCase('pt-BR')
        .trim();

    const aplicarPesquisa = () => {
        const termo = normalizar(pesquisa?.value);
        let visiveis = 0;
        cards.forEach((card) => {
            const busca = normalizar(card.dataset.busca);
            const textoOk = !termo || busca.includes(termo);
            const filtroOk = filtroAtual === 'todos' || card.dataset.temAlertas === '1';
            const mostrar = textoOk && filtroOk;
            card.hidden = !mostrar;
            if (mostrar) visiveis += 1;
        });
        if (resultado) {
            resultado.textContent = cards.length
                ? `${visiveis} de ${cards.length} jogador${cards.length === 1 ? '' : 'es'} visível${visiveis === 1 ? '' : 'is'}.`
                : '';
        }
        if (vazio) vazio.hidden = visiveis > 0;
    };

    pesquisa?.addEventListener('input', aplicarPesquisa);
    filtros.forEach((botao) => botao.addEventListener('click', () => {
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

    aplicarPesquisa();
})();
