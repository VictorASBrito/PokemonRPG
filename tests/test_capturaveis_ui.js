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
        elemento({ id: '1', encontrador: 'jogador-b' }),
        elemento({ id: '2', encontrador: temProprios ? jogador : 'jogador-b' }),
        elemento({ id: '3', encontrador: 'jogador-b' }),
    ];
    const miniaturas = slides.map(s => elemento({ id: s.dataset.id, encontrador: s.dataset.encontrador }));
    const filtro = elemento(); filtro.value = 'meus'; // Simula seleção antiga restaurada pelo navegador.
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

test('abre todos os Pokémon, mas inicia o foco no primeiro encontro próprio', () => {
    const v = montar();
    assert.equal(v.filtro.value, 'todos');
    assert.equal(v.slides[0].hidden, true);
    assert.equal(v.slides[1].hidden, false);
    assert.equal(v.slides[2].hidden, true);
    assert.equal(v.status.textContent, '2 de 3 Pokémon');
    assert.equal(v.escolher.value, '2');
    assert.equal(v.proximo.disabled, false);
    assert.deepEqual(v.miniaturas.map((mini) => mini.hidden), [false, false, false]);
    assert.equal(v.miniaturas[1].atributos['aria-current'], 'true');
    v.proximo.disparar('click');
    assert.equal(v.slides[2].hidden, false);
    v.anterior.disparar('click');
    assert.equal(v.slides[1].hidden, false);
});

test('o filtro Meus encontrados continua funcionando e permite retornar a Todos', () => {
    const v = montar();
    v.filtro.value = 'meus';
    v.filtro.disparar('change');
    assert.equal(v.status.textContent, '1 de 1 Pokémon');
    assert.equal(v.miniaturas[0].hidden, true);
    assert.equal(v.miniaturas[1].hidden, false);
    assert.equal(v.proximo.disabled, true);
    v.filtro.value = 'todos';
    v.filtro.disparar('change');
    assert.equal(v.status.textContent, '1 de 3 Pokémon');
    assert.deepEqual(v.miniaturas.map((mini) => mini.hidden), [false, false, false]);
});

test('ir direto para Pokémon de outro treinador desbloqueia filtro Meus', () => {
    const v = montar();
    v.filtro.value = 'meus';
    v.filtro.disparar('change');
    v.escolher.value = '3';
    v.escolher.disparar('change');
    assert.equal(v.filtro.value, 'todos');
    assert.equal(v.slides[2].hidden, false);
    assert.equal(v.status.textContent, '3 de 3 Pokémon');
});

test('sem Pokémon próprios abre todos e começa pelo primeiro encontro', () => {
    const v = montar({ temProprios: false });
    assert.equal(v.filtro.value, 'todos');
    assert.equal(v.status.textContent, '1 de 3 Pokémon');
    assert.equal(v.escolher.value, '1');
    v.escolher.value = '3';
    v.escolher.disparar('change');
    assert.equal(v.slides[2].hidden, false);
});
