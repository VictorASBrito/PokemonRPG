(() => {
    const grade = document.querySelector('[data-dashboard-pokemon-grid]');
    if (!grade) return;

    const cards = Array.from(grade.querySelectorAll('[data-dashboard-pokemon-card]'));
    if (!cards.length) return;

    let foco = null;

    const definirAcessibilidade = (card, expandido) => {
        card.setAttribute('aria-expanded', expandido ? 'true' : 'false');
        card.classList.toggle('pokemon-dashboard-detalhes-abertos', expandido);

        const detalhes = card.querySelector('.pokemon-dashboard-detalhes-expandidos');
        if (detalhes) detalhes.setAttribute('aria-hidden', expandido ? 'false' : 'true');

        const nome = card.querySelector('.nome-pokemon-dashboard h3')?.textContent?.trim() || 'Pokémon';
        card.setAttribute(
            'aria-label',
            expandido ? `Detalhes expandidos de ${nome}` : `Expandir detalhes de ${nome}`,
        );
    };

    const voltarGrade = ({ manterFoco = true } = {}) => {
        const anterior = foco;
        grade.classList.remove('dashboard-pokemon-modo-foco');
        document.body.classList.remove('dashboard-foco-aberto');
        cards.forEach((card) => {
            card.classList.remove('pokemon-dashboard-em-foco', 'pokemon-dashboard-lateral');
            definirAcessibilidade(card, false);
        });
        foco = null;
        if (manterFoco && anterior) anterior.focus({ preventScroll: true });
    };

    const destacar = (card) => {
        // O cartão principal deixa de funcionar como botão depois de aberto.
        // Isso permite selecionar/copiar texto e analisar os dados sem recolher por acidente.
        if (foco === card) return;

        foco = card;
        grade.classList.add('dashboard-pokemon-modo-foco');
        document.body.classList.add('dashboard-foco-aberto');
        cards.forEach((item) => {
            const ativo = item === card;
            item.classList.toggle('pokemon-dashboard-em-foco', ativo);
            item.classList.toggle('pokemon-dashboard-lateral', !ativo);
            definirAcessibilidade(item, ativo);
        });

        requestAnimationFrame(() => {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        });
    };

    cards.forEach((card) => {
        // O próprio símbolo executa a ação ou abre o seletor no retrato.
        card.querySelectorAll('[data-pokemon-abrir]').forEach((controle) => {
            controle.addEventListener('click', (evento) => evento.stopPropagation());
        });
        card.querySelectorAll('[data-pokemon-painel]').forEach((painel) => {
            painel.addEventListener('toggle', () => {
                if (!painel.open) return;
                card.querySelectorAll('[data-pokemon-painel]').forEach((outro) => {
                    if (outro !== painel) outro.open = false;
                });
            });
        });
        card.addEventListener('click', (evento) => {
            if (evento.target.closest('a, button, summary, details, form, input, select, textarea, label')) return;
            if (foco === card) return;
            destacar(card);
        });

        card.addEventListener('keydown', (evento) => {
            if (evento.target.closest('a, button, summary, details, form, input, select, textarea')) return;
            if (foco === card) return;
            if (evento.key === 'Enter' || evento.key === ' ') {
                evento.preventDefault();
                destacar(card);
            }
        });

        const botaoRecolher = card.querySelector('[data-dashboard-pokemon-collapse]');
        if (botaoRecolher) {
            botaoRecolher.addEventListener('click', (evento) => {
                evento.preventDefault();
                evento.stopPropagation();
                if (foco === card) voltarGrade({ manterFoco: true });
            });
        }
    });

    // Ações submetidas dentro do expandido são confirmadas antes do POST.
    document.addEventListener('submit', (evento) => {
        const formulario = evento.target.closest('.pokemon-dashboard-indicadores form[data-confirmacao]');
        if (!formulario) return;
        const mensagem = formulario.dataset.confirmacao;
        if (mensagem && !window.confirm(mensagem)) {
            evento.preventDefault();
            return;
        }
        formulario.querySelectorAll('button[type="submit"]').forEach((b) => { b.disabled = true; });
    });

    // Após evolução/forma, manter o mesmo Pokémon expandido.
    const focoInicial = new URLSearchParams(window.location.search).get('foco');
    const inicial = cards.find((card) => card.dataset.pokemonId === focoInicial);
    if (inicial) destacar(inicial);

    const fecharMenus = () => {
        document.querySelectorAll('.pokemon-dashboard-seletor[open]').forEach((menu) => {
            menu.open = false;
        });
    };
    document.addEventListener('click', (evento) => {
        if (!evento.target.closest('.pokemon-dashboard-seletor')) fecharMenus();
    });
    document.addEventListener('keydown', (evento) => {
        if (evento.key !== 'Escape') return;
        const menusAbertos = document.querySelectorAll('.pokemon-dashboard-seletor[open]');
        if (menusAbertos.length) {
            fecharMenus();
            evento.stopPropagation();
        } else if (foco) {
            voltarGrade({ manterFoco: true });
        }
    });
})();
