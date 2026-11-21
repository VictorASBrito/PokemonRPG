/* Proteção de usabilidade; o servidor continua impondo o limite. */
(() => {
    const form = document.querySelector('[data-troca-oferta]');
    if (!form) return;
    const checks = [...form.querySelectorAll('input[name="pokemon_id"]')];
    const inicial = checks.map(c => c.checked);
    const confirmar = document.querySelector('[data-troca-confirmar]');
    const inicialmenteBloqueado = confirmar?.disabled;
    const status = form.querySelector('[data-troca-contagem]');
    function atualizar() {
        const n = checks.filter(c => c.checked).length;
        const mudou = checks.some((c, i) => c.checked !== inicial[i]);
        for (const c of checks) c.disabled = n >= 3 && !c.checked;
        if (confirmar) confirmar.disabled = inicialmenteBloqueado || mudou;
        status.textContent = n + '/3 selecionados' + (mudou ? ' — salve a oferta antes de confirmar.' : '');
    }
    form.addEventListener('change', atualizar);
    atualizar();
})();
