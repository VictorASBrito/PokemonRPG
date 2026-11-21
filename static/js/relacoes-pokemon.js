// Cadastro de relações do Catálogo: o destino determina a natureza do vínculo.
// O servidor continua validando tudo antes de salvar.
(() => {
    'use strict';
    const gatilhosPorTipo = {
        evolucao: ['nivel', 'item', 'troca', 'amizade', 'especial'],
        mega: ['especial', 'mega_pedra'],
        alternativa: ['condicao'],
        regional: ['linhagem'],
    };
    const sugeridoPorTipo = {
        evolucao: 'nivel', mega: 'especial',
        alternativa: 'condicao', regional: 'linhagem',
    };
    document.querySelectorAll('[data-relacao-editor]').forEach((formulario) => {
        const tipo = formulario.querySelector('select[name="tipo_relacao"]');
        const gatilho = formulario.querySelector('select[name="tipo_requisito"]');
        const destino = formulario.querySelector('select[name="destino_id"]');
        const ajuda = formulario.querySelector('[data-mega-relacao-ajuda]');
        if (!tipo || !gatilho) return;

        const sincronizar = (preferirPadrao = false) => {
            const permitidos = gatilhosPorTipo[tipo.value] || [];
            [...gatilho.options].forEach((opcao) => {
                const disponivel = permitidos.includes(opcao.value);
                opcao.disabled = !disponivel;
                opcao.hidden = !disponivel;
            });
            if (preferirPadrao || !permitidos.includes(gatilho.value)) {
                gatilho.value = sugeridoPorTipo[tipo.value] || permitidos[0] || '';
            }
            if (ajuda) ajuda.hidden = tipo.value !== 'mega';
        };

        if (formulario.hasAttribute('data-relacao-nova') && destino) {
            const sugerirDestino = () => {
                const categoria = destino.selectedOptions[0]?.dataset.categoria;
                const mapa = {mega: 'mega', alternativa: 'alternativa', regional: 'regional'};
                tipo.value = mapa[categoria] || 'evolucao';
                sincronizar(true);
            };
            destino.addEventListener('change', sugerirDestino);
            sugerirDestino();
        } else {
            sincronizar();
        }
        tipo.addEventListener('change', () => sincronizar(true));
    });
})();
