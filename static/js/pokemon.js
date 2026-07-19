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
})();
