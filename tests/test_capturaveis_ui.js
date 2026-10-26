/* Testes de carrossel sem navegador externo (Node.js, VM e DOM mínimo). */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function elemento(dataset = {}) {
    const eventos = {};
    const atributos = {};
    return {
        dataset,
        eventos,
        atributos,
        hidden: false,
        disabled: false,
        value: '',
        textContent: '',
        addEventListener(tipo, funcao) { eventos[tipo] = funcao; },
        setAttribute(nome, valor) { atributos[nome] = valor; },
        disparar(tipo) { if (eventos[tipo]) eventos[tipo](); },
    };
}

function montar({ temProprios = true } = {}) {
    const jogador = 'jogador-a';
    const slides = [
        elemento({ id: '1', encontrador: temProprios ? jogador : 'jogador-b' }),
        elemento({ id: '2', encontrador: 'jogador-b' }),
        elemento({ id: '3', encontrador: jogador }),
    ];
    // No cenário sem encontros próprios, nenhum slide pertence ao jogador.
    if (!temProprios) slides[2].dataset.encontrador = 'jogador-b';
    const miniaturas = slides.map(s => elemento({ id: s.dataset.id, encontrador: s.dataset.encontrador }));
    const filtro = elemento(); filtro.value = 'meus';
    const escolher = elemento();
    const anterior = elemento();
    const proximo = elemento();
    const status = elemento();
    const refs = {
        '[data-carousel-filtro]': filtro,
        '[data-carousel-selecionar]': escolher,
        '[data-carousel-anterior]': anterior,
        '[data-carousel-proximo]': proximo,
        '[data-carousel-status]': status,
    };
    const carrossel = elemento({ meuPersonagem: jogador });
    carrossel.querySelectorAll = (seletor) => seletor === '[data-carousel-slide]' ? slides : miniaturas;
    carrossel.querySelector = (seletor) => refs[seletor] || null;
    const document = {
        querySelector: (seletor) => seletor === '[data-captura-carrossel]' ? carrossel : null,
        activeElement: { tagName: 'BODY' },
    };
    const source = fs.readFileSync(path.join(__dirname, '..', 'static', 'js', 'capturaveis.js'), 'utf8');
    vm.runInNewContext(source, { document, URL, location: { origin: 'http://localhost' } });
    return { carrossel, slides, miniaturas, filtro, escolher, anterior, proximo, status };
}

test('inicia pelos próprios encontros e navega pelas miniaturas', () => {
    const v = montar();
    assert.equal(v.filtro.value, 'meus');
    assert.equal(v.slides[0].hidden, false);
    assert.equal(v.slides[1].hidden, true);
    assert.equal(v.status.textContent, '1 de 2 Pokémon');
    v.proximo.disparar('click');
    assert.equal(v.slides[2].hidden, false);
    assert.equal(v.miniaturas[2].atributos['aria-current'], 'true');
    v.filtro.value = 'todos';
    v.filtro.disparar('change');
    assert.equal(v.status.textContent, '1 de 3 Pokémon');
    v.escolher.value = '2';
    v.escolher.disparar('change');
    assert.equal(v.slides[1].hidden, false);
    assert.equal(v.miniaturas[1].atributos['aria-current'], 'true');
});

test('sem Pokémon próprios abre todos e permite escolher Pokémon de outro', () => {
    const v = montar({ temProprios: false });
    assert.equal(v.filtro.value, 'todos');
    assert.equal(v.status.textContent, '1 de 3 Pokémon');
    v.escolher.value = '3';
    v.escolher.disparar('change');
    assert.equal(v.slides[2].hidden, false);
});
