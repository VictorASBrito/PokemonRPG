/* 12A — aparência independente por ficha, prévia reversível. */
(() => {
    'use strict';
    const raiz = document.documentElement;
    const config = JSON.parse(document.getElementById('aparencia-config').textContent);
    const botao = document.getElementById('tema-toggle');
    const dialog = document.querySelector('#aparencia-dialogo');
    const media = matchMedia('(prefers-color-scheme: dark)');
    let legado = null;
    try { legado = localStorage.getItem('pokemon-rpg-tema'); } catch (_) {}
    let salvo = {modo: config.modo || (['light','dark'].includes(legado) ? legado : 'auto'),
                 paleta: config.paleta || 'classico'};
    let atual = {...salvo};
    let enviando = false;
    function aplicar(pref) {
        atual = {...pref};
        const modo = pref.modo === 'auto' ? (media.matches ? 'dark' : 'light') : pref.modo;
        raiz.dataset.theme = modo;
        raiz.dataset.palette = pref.paleta;
        raiz.style.colorScheme = modo;
        const cores = config.opcoes?.[pref.paleta]?.[modo];
        if (cores) config.tokens.forEach((token,i) => raiz.style.setProperty('--' + token, cores[i]));
        if (botao) {
            const icone = botao.querySelector('.tema-toggle-icone');
            if (icone) icone.textContent = modo === 'dark' ? '☾' : '☀';
        }
        for (const amostra of document.querySelectorAll('[data-amostras]')) {
            const p = config.opcoes?.[amostra.dataset.amostras]?.[modo];
            if (!p) continue;
            amostra.replaceChildren(...[p[0],p[2],p[6],p[3]].map(c => {
                const span = document.createElement('span');
                span.style.backgroundColor = c;
                return span;
            }));
        }
    }
    aplicar(salvo);
    media.addEventListener('change', () => { if (atual.modo === 'auto') aplicar(atual); });
    if (!botao || !dialog) return;
    const form = dialog.querySelector('form');
    const status = dialog.querySelector('[data-aparencia-status]');
    function ler() {
        return {modo: form.elements.modo.value, paleta: form.elements.paleta.value};
    }
    botao.addEventListener('click', () => {
        form.elements.modo.value = salvo.modo;
        form.elements.paleta.value = salvo.paleta;
        status.textContent = '';
        aplicar(salvo);
        dialog.showModal();
    });
    form.addEventListener('change', () => { if (!enviando) aplicar(ler()); });
    dialog.querySelector('[data-aparencia-cancelar]').addEventListener('click', () => {
        if (!enviando) dialog.close();
    });
    dialog.addEventListener('cancel', event => { if (enviando) event.preventDefault(); });
    dialog.addEventListener('close', () => aplicar(salvo));
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (enviando) return;
        const escolha = ler();
        enviando = true;
        const controles = [...form.querySelectorAll('input,button')];
        controles.forEach(el => el.disabled = true);
        status.textContent = 'Salvando aparência...';
        try {
            const response = await fetch(dialog.dataset.aparenciaUrl, {
                method: 'POST', credentials: 'same-origin',
                headers: {'Content-Type':'application/json','Accept':'application/json',
                          'X-Aparencia-CSRF':config.csrf},
                body: JSON.stringify(escolha),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || !data.ok) throw new Error(data.erro || 'Não foi possível salvar.');
            salvo = {...escolha};
            aplicar(salvo);
            dialog.close();
        } catch (error) {
            status.textContent = error.message + ' Tente novamente ou cancele.';
        } finally {
            enviando = false;
            controles.forEach(el => el.disabled = false);
        }
    });
})();
