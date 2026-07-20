(() => {
    const form = document.querySelector('#catalogo-golpe-form');
    if (!form) return;

    const lista = document.querySelector('#lista-efeitos');
    const vazio = document.querySelector('#efeitos-vazio');
    const template = document.querySelector('#efeito-card-template');
    const hidden = document.querySelector('#efeitos_json');
    const seletorNovo = document.querySelector('#novo-tipo-efeito');
    const botaoAdicionar = document.querySelector('#adicionar-efeito');

    const numeroOuTexto = (valor) => {
        if (valor === '' || valor === null || valor === undefined) return '';
        const numero = Number(valor);
        return Number.isFinite(numero) ? numero : valor;
    };

    const atualizarVazio = () => {
        vazio?.classList.toggle('bloco-condicional-oculto', Boolean(lista?.children.length));
    };

    const atualizarCura = (card) => {
        const modo = card.querySelector('[data-para="cura"] [data-campo="modo"]')?.value;
        card.querySelector('.cura-valor')?.classList.toggle('bloco-condicional-oculto', modo === 'dados');
        card.querySelector('.cura-expressao')?.classList.toggle('bloco-condicional-oculto', modo !== 'dados');
    };

    const atualizarTipo = (card) => {
        const tipo = card.querySelector('[data-campo="tipo"]')?.value || 'texto';
        card.querySelectorAll('.efeito-campos').forEach((bloco) => {
            bloco.classList.toggle('bloco-condicional-oculto', bloco.dataset.para !== tipo);
        });
        atualizarCura(card);
    };

    const campo = (card, seletor, nome) => card.querySelector(`${seletor} [data-campo="${nome}"]`);

    const preencherCard = (card, dados = {}) => {
        const tipo = dados.tipo || 'texto';
        const tipoSelect = card.querySelector('[data-campo="tipo"]');
        if (tipoSelect) tipoSelect.value = tipo;
        const alvo = card.querySelector('.efeito-comum [data-campo="alvo"]');
        const chance = card.querySelector('.efeito-comum [data-campo="chance"]');
        const observacao = card.querySelector('.efeito-comum [data-campo="observacao"]');
        if (alvo) alvo.value = dados.alvo || 'oponente';
        if (chance) chance.value = dados.chance ?? 100;
        if (observacao) observacao.value = dados.observacao || '';

        const preenchimentos = {
            texto: ['texto'],
            aplicar_status: ['status_id', 'duracao'],
            alterar_atributo: ['atributo', 'operacao', 'valor'],
            dano_adicional: ['expressao'],
            cura: ['modo', 'valor', 'expressao'],
            multiplos_ataques: ['minimo', 'maximo'],
            condicao: ['descricao'],
        };
        (preenchimentos[tipo] || []).forEach((nome) => {
            const elemento = campo(card, `[data-para="${tipo}"]`, nome);
            if (elemento && dados[nome] !== undefined && dados[nome] !== null) {
                elemento.value = dados[nome];
            }
        });
        atualizarTipo(card);
    };

    const adicionarEfeito = (tipo = 'texto', dados = {}, rolar = true) => {
        if (!template?.content || !lista) return;
        const fragmento = template.content.cloneNode(true);
        const card = fragmento.querySelector('.efeito-card');
        lista.appendChild(fragmento);
        preencherCard(card, {...dados, tipo});
        card.querySelector('.efeito-tipo')?.addEventListener('change', () => atualizarTipo(card));
        card.querySelector('.cura-modo')?.addEventListener('change', () => atualizarCura(card));
        card.querySelector('.efeito-remover')?.addEventListener('click', () => {
            card.remove();
            atualizarVazio();
            sincronizarHidden();
        });
        card.querySelectorAll('input, select, textarea').forEach((elemento) => {
            elemento.addEventListener('input', sincronizarHidden);
            elemento.addEventListener('change', sincronizarHidden);
        });
        atualizarVazio();
        sincronizarHidden();
        if (rolar) card.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    };

    const lerCard = (card) => {
        const tipo = card.querySelector('[data-campo="tipo"]')?.value || 'texto';
        const resultado = {
            tipo,
            alvo: card.querySelector('.efeito-comum [data-campo="alvo"]')?.value || 'oponente',
            chance: numeroOuTexto(card.querySelector('.efeito-comum [data-campo="chance"]')?.value || 100),
        };
        const observacao = card.querySelector('.efeito-comum [data-campo="observacao"]')?.value.trim();
        if (observacao) resultado.observacao = observacao;

        const obter = (nome) => campo(card, `[data-para="${tipo}"]`, nome)?.value ?? '';
        if (tipo === 'texto') resultado.texto = obter('texto').trim();
        if (tipo === 'aplicar_status') {
            resultado.status_id = obter('status_id');
            const duracao = obter('duracao').trim();
            if (duracao) resultado.duracao = duracao;
        }
        if (tipo === 'alterar_atributo') {
            resultado.atributo = obter('atributo');
            resultado.operacao = obter('operacao');
            resultado.valor = numeroOuTexto(obter('valor'));
        }
        if (tipo === 'dano_adicional') resultado.expressao = obter('expressao').trim();
        if (tipo === 'cura') {
            resultado.modo = obter('modo');
            if (resultado.modo === 'dados') resultado.expressao = obter('expressao').trim();
            else resultado.valor = numeroOuTexto(obter('valor'));
        }
        if (tipo === 'multiplos_ataques') {
            resultado.minimo = numeroOuTexto(obter('minimo'));
            resultado.maximo = numeroOuTexto(obter('maximo'));
        }
        if (tipo === 'condicao') resultado.descricao = obter('descricao').trim();
        return resultado;
    };

    function sincronizarHidden() {
        if (!hidden || !lista) return;
        const efeitos = [...lista.querySelectorAll('.efeito-card')].map(lerCard);
        hidden.value = JSON.stringify({versao: 1, efeitos});
    }

    botaoAdicionar?.addEventListener('click', () => adicionarEfeito(seletorNovo?.value || 'texto'));
    form.addEventListener('submit', sincronizarHidden);

    let iniciais = [];
    try {
        iniciais = JSON.parse(document.querySelector('#efeitos-iniciais')?.textContent || '[]');
    } catch (erro) {
        console.warn('Não foi possível carregar os efeitos existentes.', erro);
    }
    if (Array.isArray(iniciais)) {
        iniciais.forEach((efeito) => adicionarEfeito(efeito.tipo || 'texto', efeito, false));
    }
    atualizarVazio();
    sincronizarHidden();
})();
