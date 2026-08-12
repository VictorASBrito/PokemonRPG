(() => {
    const formularios = [...document.querySelectorAll('[data-pesquisa-dinamica]')];
    if (!formularios.length) return;

    const esperar = (funcao, atraso = 260) => {
        let timer;
        return (...args) => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => funcao(...args), atraso);
        };
    };

    const carregar = async (form, url, { atualizarFormulario = false } = {}) => {
        const seletor = form.dataset.resultados || '[data-pesquisa-resultados]';
        const atual = document.querySelector(seletor);
        if (!atual) return;
        atual.setAttribute('aria-busy', 'true');
        atual.classList.add('pesquisa-dinamica-carregando');
        try {
            const resposta = await fetch(url, {
                headers: { 'X-Requested-With': 'fetch' },
                credentials: 'same-origin',
            });
            if (!resposta.ok) throw new Error('Não foi possível atualizar a pesquisa.');
            const html = await resposta.text();
            const documento = new DOMParser().parseFromString(html, 'text/html');
            const novo = documento.querySelector(seletor);
            if (!novo) throw new Error('A resposta da pesquisa não contém resultados.');
            atual.innerHTML = novo.innerHTML;
            atual.removeAttribute('aria-busy');
            atual.classList.remove('pesquisa-dinamica-carregando');
            history.replaceState(null, '', url);

            if (atualizarFormulario) {
                const novoForm = documento.querySelector(`[data-pesquisa-dinamica][data-resultados="${seletor.replace(/"/g, '\\"')}"]`);
                if (novoForm) {
                    [...form.elements].forEach((campo) => {
                        if (!campo.name) return;
                        const correspondente = novoForm.elements.namedItem(campo.name);
                        if (!correspondente) return;
                        if (campo instanceof HTMLInputElement && ['checkbox', 'radio'].includes(campo.type)) {
                            campo.checked = correspondente.checked;
                        } else {
                            campo.value = correspondente.value;
                        }
                    });
                }
            }
        } catch (erro) {
            atual.removeAttribute('aria-busy');
            atual.classList.remove('pesquisa-dinamica-carregando');
            const aviso = atual.querySelector('[data-pesquisa-erro]') || document.createElement('p');
            aviso.dataset.pesquisaErro = '1';
            aviso.className = 'alerta alerta-erro pesquisa-dinamica-erro';
            aviso.textContent = erro.message || 'Não foi possível atualizar a pesquisa.';
            atual.prepend(aviso);
        }
    };

    formularios.forEach((form) => {
        const seletor = form.dataset.resultados || '[data-pesquisa-resultados]';
        const urlDoFormulario = () => {
            const dados = new FormData(form);
            dados.delete('pagina');
            const parametros = new URLSearchParams();
            dados.forEach((valor, chave) => {
                const texto = String(valor).trim();
                if (texto) parametros.append(chave, texto);
            });
            const base = form.action || window.location.pathname;
            const url = new URL(base, window.location.origin);
            url.search = parametros.toString();
            return url.toString();
        };

        const atualizar = esperar(() => carregar(form, urlDoFormulario()));
        form.addEventListener('submit', (evento) => {
            evento.preventDefault();
            carregar(form, urlDoFormulario());
        });
        form.querySelectorAll('input[type="search"], input[type="text"], input:not([type]), textarea').forEach((campo) => {
            campo.addEventListener('input', atualizar);
        });
        form.querySelectorAll('select, input[type="checkbox"], input[type="radio"]').forEach((campo) => {
            campo.addEventListener('change', () => carregar(form, urlDoFormulario()));
        });
        form.querySelectorAll('[data-pesquisa-limpar]').forEach((link) => {
            link.addEventListener('click', (evento) => {
                evento.preventDefault();
                const url = new URL(link.href, window.location.origin);
                carregar(form, url.toString(), { atualizarFormulario: true });
            });
        });

        document.addEventListener('click', (evento) => {
            const link = evento.target.closest(`${seletor} .paginacao a`);
            if (!link) return;
            evento.preventDefault();
            carregar(form, link.href);
        });
    });
})();
