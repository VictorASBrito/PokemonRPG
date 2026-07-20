(() => {
    const form = document.querySelector('#catalogo-forma-form');
    if (!form) return;

    const novaEspecie = document.querySelector('#nova_especie');
    const existente = document.querySelector('#especie-existente');
    const dadosEspecie = document.querySelector('#dados-especie');
    const atualizarModoEspecie = () => {
        if (!novaEspecie) return;
        const nova = novaEspecie.checked;
        existente?.classList.toggle('bloco-condicional-oculto', nova);
        dadosEspecie?.classList.toggle('bloco-condicional-oculto', !nova);
    };
    novaEspecie?.addEventListener('change', atualizarModoEspecie);
    atualizarModoEspecie();

    const sincronizarImagem = (inputId, imgId) => {
        const input = document.querySelector(inputId);
        const imagem = document.querySelector(imgId);
        const atualizar = () => {
            if (!input || !imagem) return;
            const url = input.value.trim();
            imagem.src = url;
            imagem.style.display = url ? 'block' : 'none';
        };
        input?.addEventListener('input', atualizar);
        imagem?.addEventListener('error', () => { imagem.style.display = 'none'; });
        atualizar();
    };
    sincronizarImagem('#imagem_url', '#preview-normal');
    sincronizarImagem('#imagem_shiny_url', '#preview-shiny');

    const botaoSimular = document.querySelector('#botao-simular');
    const resultado = document.querySelector('#resultado-simulacao');
    botaoSimular?.addEventListener('click', async () => {
        const atributos = {};
        document.querySelectorAll('.campo-atributo-base').forEach((campo) => {
            atributos[campo.dataset.codigo] = campo.value || 0;
        });
        botaoSimular.disabled = true;
        resultado.innerHTML = '<p class="texto-suave">Calculando…</p>';
        try {
            const resposta = await fetch(form.dataset.simulacaoUrl, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    atributos,
                    nivel: Number(document.querySelector('#simulacao-nivel')?.value || 1),
                    shiny: Boolean(document.querySelector('#simulacao-shiny')?.checked),
                    natureza_id: document.querySelector('#simulacao-natureza')?.value || '',
                    estilo: document.querySelector('#simulacao-estilo')?.value || '',
                }),
            });
            const corpo = await resposta.json();
            if (!resposta.ok) throw new Error(corpo.erro || 'Falha na simulação.');
            const nomes = {};
            document.querySelectorAll('.campo-atributo-base').forEach((campo) => {
                nomes[campo.dataset.codigo] = campo.closest('.campo')?.querySelector('label')?.textContent || campo.dataset.codigo;
            });
            resultado.innerHTML = Object.entries(corpo.atributos).map(([codigo, valor]) =>
                `<div class="atributo-simulado"><strong>${valor}</strong><span>${nomes[codigo] || codigo}</span></div>`
            ).join('');
        } catch (erro) {
            resultado.innerHTML = `<p class="alerta alerta-erro">${erro.message}</p>`;
        } finally {
            botaoSimular.disabled = false;
        }
    });
})();
