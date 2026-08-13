(() => {
    const grade = document.querySelector('[data-dashboard-pokemon-grid]');
    if (!grade) return;

    const cards = Array.from(grade.querySelectorAll('[data-dashboard-pokemon-card]'));
    if (!cards.length) return;

    let foco = null;

    const definirAcessibilidade = (card, expandido) => {
        card.setAttribute('aria-expanded', expandido ? 'true' : 'false');
        const detalhes = card.querySelector('.pokemon-dashboard-detalhes-expandidos');
        if (detalhes) detalhes.setAttribute('aria-hidden', expandido ? 'false' : 'true');
    };

    const voltarGrade = ({ manterFoco = true } = {}) => {
        const anterior = foco;
        grade.classList.remove('dashboard-pokemon-modo-foco');
        cards.forEach((card) => {
            card.classList.remove('pokemon-dashboard-em-foco', 'pokemon-dashboard-lateral');
            definirAcessibilidade(card, false);
        });
        foco = null;
        if (manterFoco && anterior) anterior.focus({ preventScroll: true });
    };

    const destacar = (card) => {
        if (foco === card) {
            voltarGrade();
            return;
        }

        foco = card;
        grade.classList.add('dashboard-pokemon-modo-foco');
        cards.forEach((item) => {
            const ativo = item === card;
            item.classList.toggle('pokemon-dashboard-em-foco', ativo);
            item.classList.toggle('pokemon-dashboard-lateral', !ativo);
            definirAcessibilidade(item, ativo);
        });

        // Mantém o início do cartão principal visível sem deslocar toda a página.
        requestAnimationFrame(() => {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        });
    };

    cards.forEach((card) => {
        card.addEventListener('click', (evento) => {
            if (evento.target.closest('a, button, input, select, textarea, label')) return;
            destacar(card);
        });

        card.addEventListener('keydown', (evento) => {
            if (evento.target.closest('a, button, input, select, textarea')) return;
            if (evento.key === 'Enter' || evento.key === ' ') {
                evento.preventDefault();
                destacar(card);
            }
        });
    });

    document.addEventListener('keydown', (evento) => {
        if (evento.key === 'Escape' && foco) voltarGrade({ manterFoco: true });
    });
})();
