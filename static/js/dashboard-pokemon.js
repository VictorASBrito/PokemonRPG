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
        card.addEventListener('click', (evento) => {
            if (evento.target.closest('a, button, input, select, textarea, label')) return;
            if (foco === card) return;
            destacar(card);
        });

        card.addEventListener('keydown', (evento) => {
            if (evento.target.closest('a, button, input, select, textarea')) return;
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

    document.addEventListener('keydown', (evento) => {
        if (evento.key === 'Escape' && foco) voltarGrade({ manterFoco: true });
    });
})();
