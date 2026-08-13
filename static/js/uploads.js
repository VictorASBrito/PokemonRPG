(() => {
    const configuracoes = [
        {url: '#imagem_url', arquivo: '#imagem_arquivo', preview: '#preview-normal', remover: 'input[name="remover_imagem"]'},
        {url: '#imagem_shiny_url', arquivo: '#imagem_shiny_arquivo', preview: '#preview-shiny', remover: 'input[name="remover_imagem_shiny"]'},
        {url: '#imagem_url', arquivo: '#imagem_arquivo', preview: '#preview-item', remover: 'input[name="remover_imagem"]'},
        {url: '#foto_url', arquivo: '#foto_arquivo', preview: '#preview-perfil', remover: 'input[name="remover_foto"]', placeholder: '#preview-perfil-placeholder'},
    ];

    const previewsConfigurados = new Set();
    configuracoes.forEach((configuracao) => {
        const imagem = document.querySelector(configuracao.preview);
        if (!imagem || previewsConfigurados.has(imagem)) return;
        previewsConfigurados.add(imagem);

        const inputUrl = document.querySelector(configuracao.url);
        const inputArquivo = document.querySelector(configuracao.arquivo);
        const inputRemover = document.querySelector(configuracao.remover);
        let urlObjeto = null;

        const liberarObjeto = () => {
            if (urlObjeto) {
                URL.revokeObjectURL(urlObjeto);
                urlObjeto = null;
            }
        };

        const atualizar = () => {
            liberarObjeto();
            const arquivo = inputArquivo?.files?.[0];
            let origem = '';
            if (arquivo) {
                urlObjeto = URL.createObjectURL(arquivo);
                origem = urlObjeto;
            } else if (!inputRemover?.checked) {
                origem = inputUrl?.value?.trim() || '';
            }
            imagem.src = origem;
            imagem.hidden = !origem;
            imagem.style.display = origem ? 'block' : 'none';
            const placeholder = configuracao.placeholder ? document.querySelector(configuracao.placeholder) : null;
            if (placeholder) placeholder.hidden = Boolean(origem);
        };

        inputUrl?.addEventListener('input', atualizar);
        inputArquivo?.addEventListener('change', atualizar);
        inputRemover?.addEventListener('change', atualizar);
        imagem.addEventListener('error', () => {
            if (!inputArquivo?.files?.[0]) {
                imagem.style.display = 'none';
                imagem.hidden = true;
                const placeholder = configuracao.placeholder ? document.querySelector(configuracao.placeholder) : null;
                if (placeholder) placeholder.hidden = false;
            }
        });
        window.addEventListener('beforeunload', liberarObjeto, {once: true});
        atualizar();
    });
})();
