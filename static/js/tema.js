(() => {
    const chave = 'pokemon-rpg-tema';
    const raiz = document.documentElement;
    const botao = document.getElementById('tema-toggle');
    if (!botao) return;

    const aplicar = (tema, persistir = true) => {
        const normalizado = tema === 'dark' ? 'dark' : 'light';
        raiz.dataset.theme = normalizado;
        raiz.style.colorScheme = normalizado;
        if (persistir) { try { localStorage.setItem(chave, normalizado); } catch (_erro) { /* preferência só nesta sessão */ } }
        botao.setAttribute('aria-pressed', normalizado === 'dark' ? 'true' : 'false');
        botao.setAttribute('aria-label', normalizado === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro');
        botao.title = normalizado === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro';
        const icone = botao.querySelector('.tema-toggle-icone');
        if (icone) icone.textContent = normalizado === 'dark' ? '☀' : '☾';
    };

    aplicar(raiz.dataset.theme || 'light', false);
    botao.addEventListener('click', () => aplicar(raiz.dataset.theme === 'dark' ? 'light' : 'dark'));
})();
