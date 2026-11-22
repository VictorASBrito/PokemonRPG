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

    const modalExcluir = document.querySelector("#modal-excluir-pokemon");
    const abrirExcluir = document.querySelector("[data-abrir-exclusao]");
    const formularioExcluir = document.querySelector("#form-excluir-pokemon");
    if (modalExcluir && abrirExcluir && formularioExcluir) {
        const primeira = modalExcluir.querySelector('[data-exclusao-etapa="1"]');
        const campo = formularioExcluir.querySelector('[name="nome_confirmacao"]');
        const alvo = modalExcluir.querySelector("#exclusao-nome-alvo").textContent.trim();
        const confirmar = modalExcluir.querySelector("[data-confirmar-exclusao]");
        const feedback = modalExcluir.querySelector("[data-exclusao-feedback]");
        const avancar = modalExcluir.querySelector("[data-avancar-exclusao]");
        let enviando = false;
        const valido = () => Boolean(alvo) && campo.value.trim() === alvo;
        const atualizar = () => {
            confirmar.disabled = !valido() || enviando;
            feedback.textContent = valido() ? "Nome correto. Você pode confirmar a exclusão." :
                "O nome deve corresponder exatamente ao indicado.";
        };
        const reiniciar = () => {
            enviando = false;
            primeira.hidden = false;
            formularioExcluir.hidden = true;
            campo.value = "";
            atualizar();
        };
        abrirExcluir.addEventListener("click", () => {
            reiniciar();
            modalExcluir.showModal();
            primeira.querySelector("[data-cancelar-exclusao]").focus();
        });
        avancar.addEventListener("click", () => {
            primeira.hidden = true;
            formularioExcluir.hidden = false;
            campo.focus();
        });
        modalExcluir.querySelector("[data-voltar-exclusao]").addEventListener("click", () => {
            reiniciar();
            avancar.focus();
        });
        modalExcluir.querySelectorAll("[data-cancelar-exclusao]").forEach(botao => {
            botao.addEventListener("click", () => modalExcluir.close());
        });
        modalExcluir.addEventListener("close", () => {
            reiniciar();
            abrirExcluir.focus();
        });
        campo.addEventListener("input", atualizar);
        formularioExcluir.addEventListener("submit", (evento) => {
            if (!modalExcluir.open || formularioExcluir.hidden || !valido() || enviando) {
                evento.preventDefault();
                return;
            }
            enviando = true;
            confirmar.disabled = true;
        });
    }

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


/* 10E.3.3/4: confirmação explícita antes de evoluir; o servidor
   revalida autorização, nível, material e origem independentemente do JS. */
(() => {
    document.querySelectorAll("form.evolucao-form-confirmacao[data-confirmacao]")
        .forEach((formulario) => {
            formulario.addEventListener("submit", (evento) => {
                const mensagem = formulario.dataset.confirmacao
                    || "Confirmar a evolução deste Pokémon?";
                if (!window.confirm(mensagem)) {
                    evento.preventDefault();
                    return;
                }
                const botao = formulario.querySelector('button[type="submit"]');
                if (botao) botao.disabled = true;
            });
        });
})();
