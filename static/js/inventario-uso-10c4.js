/* Etapa 10C.4 — interação visual da mochila; o servidor decide e valida o efeito. */
(() => {
  'use strict';

  // Isolada para poder ser validada sem DOM e sem servidor.
  function elegivel(efeitos, pokemon) {
    if (!pokemon || !Array.isArray(efeitos)) return false;
    return efeitos.some((efeito) => {
      if (!efeito || efeito.alvo && efeito.alvo !== 'pokemon') return false;
      if (efeito.tipo === 'recuperar_pv') {
        return Number.isFinite(pokemon.maximo) && pokemon.maximo > 0 &&
               Number.isFinite(pokemon.atual) && pokemon.atual < pokemon.maximo;
      }
      if (efeito.tipo === 'remover_status') {
        return efeito.todos ? pokemon.status.size > 0 :
               Boolean(efeito.status_id) && pokemon.status.has(String(efeito.status_id));
      }
      return false;
    });
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { elegivel };
  }

  const root = typeof document === 'undefined' ? null : document.querySelector('[data-inventario]');
  if (!root) return;
  const form = root.querySelector('[data-formulario-uso]');
  const msgWrap = root.querySelector('[data-uso-aviso]');
  const cards = [...root.querySelectorAll('[data-pokemon-alvo]')];
  const botoes = [...root.querySelectorAll('[data-ativar-uso]')];
  const usarItem = form?.querySelector('[name="item_id"]');
  const usarPokemon = form?.querySelector('[name="pokemon_id"]');
  const mapa = document.getElementById('inventario-mapa-estatico');
  const equipar = document.getElementById('inventario-equipar-10c4');
  let aguardando = null;
  let enviando = false;

  function limpar() {
    aguardando = null;
    if (msgWrap) msgWrap.hidden = true;
    window.PokemonRPGToast?.fecharDinamico();
    for (const card of cards) {
      card.classList.remove('inventario-uso-elegivel');
      const botao = card.querySelector('[data-selecionar-pokemon]');
      if (botao) {
        botao.hidden = true;
        botao.disabled = true;
      }
    }
    for (const botao of botoes) {
      botao.setAttribute('aria-pressed', 'false');
    }
    if (usarPokemon) usarPokemon.value = '';
  }

  // ANKAR_10C4_2_SELECAO_TOAST: usa a mesma notificação global de 1,5s.
  function informar(texto, tipo = 'info') {
    window.PokemonRPGToast?.mostrar(texto, tipo);
  }

  function enviar(itemId, pokemonId) {
    if (!form || !usarItem || !usarPokemon || enviando) return;
    usarItem.value = itemId;
    usarPokemon.value = pokemonId || '';
    enviando = true;
    // action aponta à rota POST existente, com validação de propriedade e quantidade.
    form.requestSubmit();
  }

  function efeitos(itemId) {
    const alvo = [...root.querySelectorAll('[data-uso-efeitos]')]
      .find(el => el.dataset.usoEfeitos === itemId);
    if (!alvo) return [];
    try {
      const documento = JSON.parse(alvo.textContent || 'null');
      return Array.isArray(documento?.efeitos) ? documento.efeitos : [];
    } catch (_) {
      return [];
    }
  }

  function atributos(card) {
    return {
      atual: Number(card.dataset.pvAtual),
      maximo: card.dataset.pvMaximo ? Number(card.dataset.pvMaximo) : NaN,
      status: new Set((card.dataset.statusIds || '').split(',').filter(Boolean)),
    };
  }

  for (const botao of botoes) {
    botao.setAttribute('aria-pressed', 'false');
    botao.addEventListener('click', () => {
      if (enviando) return;
      limpar();
      const tipo = botao.dataset.tipoUso;
      const id = botao.dataset.ativarUso;
      if (tipo === 'mapa') {
        mapa?.showModal(); // nunca consome o mapa
        return;
      }
      if (tipo === 'registro') {
        // Itens sem efeito automático conservam a operação narrativa anterior.
        if (window.confirm('Este item não possui efeito automático. Registrar o consumo de 1 unidade?')) {
          enviar(id, '');
        }
        return;
      }
      if (tipo !== 'terapia') return;
      const ativos = efeitos(id);
      let disponiveis = 0;
      for (const card of cards) {
        const botaoAlvo = card.querySelector('[data-selecionar-pokemon]');
        const pode = elegivel(ativos, atributos(card));
        card.classList.toggle('inventario-uso-elegivel', pode);
        if (botaoAlvo) {
          botaoAlvo.hidden = !pode;
          botaoAlvo.disabled = !pode;
        }
        if (pode) disponiveis++;
      }
      aguardando = disponiveis ? id : null;
      if (aguardando) {
        botao.setAttribute('aria-pressed', 'true');
        if (msgWrap) msgWrap.hidden = false; // apenas Cancelar, sem banner de aviso
        informar('Selecione um Pokémon destacado para usar o item.', 'info');
      } else {
        informar('Nenhum Pokémon da equipe pode receber o efeito agora.', 'aviso');
      }
    });
  }

  for (const card of cards) {
    card.querySelector('[data-selecionar-pokemon]')?.addEventListener('click', () => {
      if (!aguardando || !card.classList.contains('inventario-uso-elegivel') || enviando) return;
      enviar(aguardando, card.dataset.pokemonAlvo);
    });
  }

  root.querySelector('[data-uso-cancelar]')?.addEventListener('click', limpar);
  root.querySelectorAll('[data-aba-botao], [data-escolher-item]').forEach(botao => {
    botao.addEventListener('click', limpar);
  });
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && aguardando) limpar();
  });

  root.querySelectorAll('[data-equipar-item]').forEach(botao => {
    botao.addEventListener('click', () => {
      limpar();
      if (!equipar) return;
      const campo = equipar.querySelector('[name="item_id"]');
      if (campo) campo.value = botao.dataset.equiparItem;
      const alvo = equipar.querySelector('[name="pokemon_id"]');
      if (alvo) alvo.value = '';
      equipar.showModal();
    });
  });
  equipar?.querySelector('[data-equipar-cancelar]')?.addEventListener('click', () => equipar.close());
})();
