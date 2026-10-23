(() => {
    "use strict";

    const shiny = document.querySelector("#shiny");
    const imagem = document.querySelector("#imagem-pokemon");
    const atualizarImagem = () => {
        if (!shiny || !imagem) return;
        const destino = shiny.checked ? imagem.dataset.shiny : imagem.dataset.normal;
        if (destino) imagem.src = destino;
    };
    shiny?.addEventListener("change", atualizarImagem);

    const formularioExcluir = document.querySelector("#form-excluir-pokemon");
    formularioExcluir?.addEventListener("submit", (evento) => {
        const mensagem = formularioExcluir.dataset.confirmacao || "Confirmar remoção?";
        if (!window.confirm(mensagem)) evento.preventDefault();
    });

    const formulario = document.querySelector("#form-pokemon");
    const camposRecalculo = formulario?.querySelectorAll(
        "#especie_nome, #natureza, #status, #shiny, [name^='bonus_'], [name='golpe_nome']"
    );
    const avisoExistente = document.querySelector("#aviso-recalculo");

    camposRecalculo?.forEach((campo) => {
        campo.addEventListener("change", () => {
            if (avisoExistente || document.querySelector("#aviso-recalculo")) return;
            const aviso = document.createElement("span");
            aviso.id = "aviso-recalculo";
            aviso.className = "chip";
            aviso.textContent = "Salve para recalcular";
            document.querySelector(".barra-salvar-pokemon")?.prepend(aviso);
        });
    });

    // Prévia imediata: o seletor visual emite o registro escolhido e a ficha
    // atualiza os metadados localmente. A gravação continua exclusiva do submit.
    const slots = [...document.querySelectorAll('[data-golpe-slot]')];
    const contadorGolpes = document.querySelector('#contador-golpes');
    const codigosTipos = new Set([
        'normal','fire','water','electric','grass','ice','fighting','poison',
        'ground','flying','psychic','bug','rock','ghost','dragon','dark',
        'steel','fairy','personalizado',
    ]);
    const atualizarContador = () => {
        if (!contadorGolpes) return;
        const presentes = slots.filter((slot) => slot.querySelector('[data-golpe-input]')?.value.trim()).length;
        contadorGolpes.textContent = `${presentes}/${slots.length}`;
    };
    const etiquetaTipo = (tipo) => {
        const span = document.createElement('span');
        const dado = Array.isArray(tipo?.tipos) ? tipo.tipos[0] : null;
        if (!dado) {
            span.className = 'golpe-vazio-meta';
            span.textContent = 'Sem tipo';
            return span;
        }
        const codigo = codigosTipos.has(dado.codigo) ? dado.codigo : 'personalizado';
        span.className = `etiqueta-tipo etiqueta-tipo--${codigo}`;
        span.textContent = dado.nome || 'Sem tipo';
        return span;
    };
    const atualizarPrevia = (slot, item) => {
        slot.querySelector('[data-golpe-tipo]')?.replaceChildren(etiquetaTipo(item));
        slot.querySelector('[data-golpe-categoria]').textContent = item?.categoria || '—';
        slot.querySelector('[data-golpe-dano]').textContent = item?.dano || '—';
        slot.querySelector('[data-golpe-precisao]').textContent = item?.precisao_texto || '—';

        const card = document.querySelector(`[data-golpe-efeito-card][data-slot-index="${slot.dataset.slotIndex}"]`);
        if (!card) return;
        card.classList.toggle('efeito-golpe-card-vazio', !item);
        card.querySelector('[data-golpe-efeito-nome]').textContent = item?.rotulo || item?.valor || 'Sem golpe definido';
        card.querySelector('[data-golpe-efeito-precisao]').textContent = item
            ? `Precisão ${item.precisao_texto || '—'}`
            : `Slot ${Number(slot.dataset.slotIndex) + 1}`;
        card.querySelector('[data-golpe-efeito-texto]').textContent = item
            ? (item.efeito || 'Sem descrição cadastrada.')
            : 'Selecione um golpe para visualizar os detalhes.';
    };
    slots.forEach((slot) => {
        const input = slot.querySelector('[data-golpe-input]');
        input?.addEventListener('catalogo:selecionado', (evento) => {
            atualizarPrevia(slot, evento.detail?.item || null);
            atualizarContador();
        });
        input?.addEventListener('input', () => {
            // Nunca mostrar metadados antigos enquanto o usuário digita outro nome.
            atualizarPrevia(slot, null);
            atualizarContador();
        });
    });
})();
