(() => {
    "use strict";

    const formulario = document.querySelector("#form-ficha");
    if (!formulario) return;

    const pvPorSaude = Number(formulario.dataset.pvPorSaude || 10);
    const campoSaude = document.querySelector("#atributo_saude");
    const campoPvAtual = document.querySelector("#pv_atual");
    const previewPvAtual = document.querySelector("#pv-atual-preview");
    const previewPvMaximo = document.querySelector("#pv-maximo-preview");
    const campoPvMaximo = document.querySelector("#pv-maximo-campo");

    const atualizarPv = () => {
        const saude = Math.max(0, Number(campoSaude?.value || 0));
        const maximo = saude * pvPorSaude;
        if (previewPvMaximo) previewPvMaximo.textContent = String(maximo);
        if (campoPvMaximo) campoPvMaximo.textContent = String(maximo);
        if (campoPvAtual) {
            campoPvAtual.max = String(maximo);
            campoPvAtual.min = String(-maximo);
        }
    };

    campoSaude?.addEventListener("input", atualizarPv);
    campoPvAtual?.addEventListener("input", () => {
        if (previewPvAtual) previewPvAtual.textContent = campoPvAtual.value || "0";
    });
    atualizarPv();

    const vincularRemocao = (raiz) => {
        raiz.querySelectorAll(".botao-remover").forEach((botao) => {
            if (botao.dataset.vinculado === "1") return;
            botao.dataset.vinculado = "1";
            botao.addEventListener("click", () => {
                const linha = botao.closest(".linha-item, .insignea-editavel");
                linha?.remove();
            });
        });
    };

    const listaInventario = document.querySelector("#lista-inventario");
    const modeloItem = document.querySelector("#modelo-item");
    document.querySelector("#adicionar-item")?.addEventListener("click", () => {
        if (!listaInventario || !modeloItem) return;
        listaInventario.appendChild(modeloItem.content.cloneNode(true));
        vincularRemocao(listaInventario);
        listaInventario.querySelector(".linha-item:last-child input")?.focus();
    });

    const listaInsigneas = document.querySelector("#lista-insigneas");
    const modeloInsignea = document.querySelector("#modelo-insignea");
    document.querySelector("#adicionar-insignea")?.addEventListener("click", () => {
        if (!listaInsigneas || !modeloInsignea) return;
        document.querySelector("#mensagem-sem-insigneas")?.remove();
        listaInsigneas.appendChild(modeloInsignea.content.cloneNode(true));
        vincularRemocao(listaInsigneas);
        listaInsigneas.querySelector(".insignea-editavel:last-child input")?.focus();
    });

    vincularRemocao(document);
})();
