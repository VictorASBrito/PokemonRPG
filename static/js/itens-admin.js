(() => {
    const form = document.querySelector('#catalogo-item-form');
    if (!form) return;

    const lista = document.querySelector('#lista-efeitos-item');
    const vazio = document.querySelector('#efeitos-item-vazio');
    const template = document.querySelector('#efeito-item-card-template');
    const hidden = document.querySelector('#efeitos_json');
    const seletorNovo = document.querySelector('#novo-tipo-efeito-item');
    const botaoAdicionar = document.querySelector('#adicionar-efeito-item');

    const numeroOuTexto = (valor) => {
        if (valor === '' || valor === null || valor === undefined) return '';
        const numero = Number(valor);
        return Number.isFinite(numero) ? numero : valor;
    };

    const atualizarVazio = () => {
        vazio?.classList.toggle('bloco-condicional-oculto', Boolean(lista?.children.length));
    };

    const atualizarTipo = (card) => {
        const tipo = card.querySelector('[data-campo="tipo"]')?.value || 'texto';
        card.querySelectorAll('.efeito-campos-item').forEach((bloco) => {
            bloco.classList.toggle('bloco-condicional-oculto', bloco.dataset.para !== tipo);
        });
        if (tipo === 'recuperar_pv') {
            const operacao = card.querySelector('[data-para="recuperar_pv"] [data-campo="operacao"]')?.value;
            const valor = card.querySelector('[data-para="recuperar_pv"] [data-campo="valor"]')?.closest('.campo');
            const expressao = card.querySelector('[data-para="recuperar_pv"] [data-campo="expressao"]')?.closest('.campo');
            valor?.classList.toggle('bloco-condicional-oculto', operacao === 'dados');
            expressao?.classList.toggle('bloco-condicional-oculto', operacao !== 'dados');
        }
    };

    const obter = (card, tipo, nome) => card.querySelector(`[data-para="${tipo}"] [data-campo="${nome}"]`);

    const preencher = (card, dados = {}) => {
        const tipo = dados.tipo || 'texto';
        const tipoSelect = card.querySelector('[data-campo="tipo"]');
        if (tipoSelect) tipoSelect.value = tipo;
        const alvo = card.querySelector('.efeito-item-comum [data-campo="alvo"]');
        const observacao = card.querySelector('.efeito-item-comum [data-campo="observacao"]');
        if (alvo) alvo.value = dados.alvo || 'pokemon';
        if (observacao) observacao.value = dados.observacao || '';

        const campos = {
            texto: ['texto'],
            recuperar_pv: ['operacao', 'valor', 'expressao'],
            remover_status: ['status_id', 'todos'],
            alterar_atributo: ['atributo', 'operacao', 'valor'],
            causar_dano: ['expressao'],
            modificar_calculo: ['chave', 'operacao', 'valor', 'tipo_id'],
            evolucao: ['requisito'],
            mega_evolucao: ['requisito'],
        };
        (campos[tipo] || []).forEach((nome) => {
            const elemento = obter(card, tipo, nome);
            if (!elemento || dados[nome] === undefined || dados[nome] === null) return;
            if (elemento.type === 'checkbox') elemento.checked = Boolean(dados[nome]);
            else elemento.value = dados[nome];
        });
        atualizarTipo(card);
    };

    const ler = (card) => {
        const tipo = card.querySelector('[data-campo="tipo"]')?.value || 'texto';
        const resultado = {
            tipo,
            alvo: card.querySelector('.efeito-item-comum [data-campo="alvo"]')?.value || 'pokemon',
        };
        const observacao = card.querySelector('.efeito-item-comum [data-campo="observacao"]')?.value.trim();
        if (observacao) resultado.observacao = observacao;
        const valor = (nome) => obter(card, tipo, nome)?.value ?? '';

        if (tipo === 'texto') resultado.texto = valor('texto').trim();
        if (tipo === 'recuperar_pv') {
            resultado.operacao = valor('operacao');
            if (resultado.operacao === 'dados') resultado.expressao = valor('expressao').trim();
            else resultado.valor = numeroOuTexto(valor('valor'));
        }
        if (tipo === 'remover_status') {
            resultado.status_id = valor('status_id');
            resultado.todos = Boolean(obter(card, tipo, 'todos')?.checked);
        }
        if (tipo === 'alterar_atributo') {
            resultado.atributo = valor('atributo');
            resultado.operacao = valor('operacao');
            resultado.valor = numeroOuTexto(valor('valor'));
        }
        if (tipo === 'causar_dano') resultado.expressao = valor('expressao').trim();
        if (tipo === 'modificar_calculo') {
            resultado.chave = valor('chave').trim();
            resultado.operacao = valor('operacao');
            resultado.valor = numeroOuTexto(valor('valor'));
            resultado.tipo_id = valor('tipo_id');
        }
        if (tipo === 'evolucao' || tipo === 'mega_evolucao') {
            resultado.requisito = valor('requisito').trim();
        }
        return resultado;
    };

    function sincronizar() {
        if (!hidden || !lista) return;
        hidden.value = JSON.stringify({
            versao: 1,
            efeitos: [...lista.querySelectorAll('.efeito-card')].map(ler),
        });
    }

    const adicionar = (tipo = 'texto', dados = {}, rolar = true) => {
        if (!template?.content || !lista) return;
        const fragmento = template.content.cloneNode(true);
        const card = fragmento.querySelector('.efeito-card');
        lista.appendChild(fragmento);
        preencher(card, {...dados, tipo});
        card.querySelector('.efeito-item-tipo')?.addEventListener('change', () => {
            atualizarTipo(card);
            sincronizar();
        });
        card.querySelectorAll('input, select, textarea').forEach((campo) => {
            campo.addEventListener('input', sincronizar);
            campo.addEventListener('change', () => {
                atualizarTipo(card);
                sincronizar();
            });
        });
        card.querySelector('.efeito-item-remover')?.addEventListener('click', () => {
            card.remove();
            atualizarVazio();
            sincronizar();
        });
        atualizarVazio();
        sincronizar();
        if (rolar) card.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    };

    botaoAdicionar?.addEventListener('click', () => adicionar(seletorNovo?.value || 'texto'));
    form.addEventListener('submit', sincronizar);

    let iniciais = [];
    try {
        iniciais = JSON.parse(document.querySelector('#efeitos-item-iniciais')?.textContent || '[]');
    } catch (erro) {
        console.warn('Não foi possível carregar os efeitos do item.', erro);
    }
    if (Array.isArray(iniciais)) iniciais.forEach((efeito) => adicionar(efeito.tipo || 'texto', efeito, false));
    atualizarVazio();
    sincronizar();
})();
