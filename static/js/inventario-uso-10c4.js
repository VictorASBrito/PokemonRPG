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

  // 11B: todas as mutações iniciadas na Bag exigem confirmação explícita.
  const root = typeof document === 'undefined' ? null : document.querySelector('[data-inventario]');
  if (!root) return;
  const form = root.querySelector('[data-formulario-uso]');
  const modal = document.getElementById('inventario-confirmacao-11b');
  const confirmar = modal?.querySelector('[data-confirmar-operacao]');
  const alvoWrap = modal?.querySelector('[data-confirmacao-alvo]');
  const alvo = modal?.querySelector('[data-confirmacao-pokemon]');
  const cards = [...root.querySelectorAll('[data-pokemon-alvo]')];
  const mapa = document.getElementById('inventario-mapa-estatico');
  const equipar = document.getElementById('inventario-equipar-10c4');
  const equipForm = equipar?.querySelector('form');
  let pendente = null;
  let autorizado = null;
  let enviando = false;

  function informar(texto, tipo = 'info') {
    window.PokemonRPGToast?.mostrar(texto, tipo);
  }

  function campo(f, nome) {
    return f?.elements.namedItem(nome);
  }

  function textoSelecionado(f, nome) {
    const el = campo(f, nome);
    return el?.selectedOptions?.[0]?.textContent.trim() || '';
  }

  function nomeItem(id) {
    const detalhe = [...root.querySelectorAll('[data-detalhe-item]')]
      .find(el => el.dataset.detalheItem === id);
    return detalhe?.querySelector('h2')?.textContent.trim() || 'item';
  }

  function efeitos(id) {
    const el = [...root.querySelectorAll('[data-uso-efeitos]')]
      .find(el => el.dataset.usoEfeitos === id);
    try {
      const documento = JSON.parse(el?.textContent || 'null');
      return Array.isArray(documento?.efeitos) ? documento.efeitos : [];
    } catch (_) { return []; }
  }

  function atributos(card) {
    return {
      atual: Number(card.dataset.pvAtual),
      maximo: card.dataset.pvMaximo ? Number(card.dataset.pvMaximo) : NaN,
      status: new Set((card.dataset.statusIds || '').split(',').filter(Boolean)),
    };
  }

  function abrir(titulo, resumo, acao, candidatos = []) {
    if (!modal || modal.open || enviando || equipar?.open || mapa?.open) return;
    pendente = acao;
    modal.querySelector('[data-confirmacao-titulo]').textContent = titulo;
    modal.querySelector('[data-confirmacao-resumo]').textContent = resumo;
    alvoWrap.hidden = candidatos.length === 0;
    alvo.replaceChildren(new Option('Selecionar Pokémon', ''));
    for (const card of candidatos) {
      alvo.add(new Option(card.dataset.pokemonNome, card.dataset.pokemonAlvo));
    }
    confirmar.disabled = candidatos.length > 0;
    confirmar.textContent = 'Confirmar';
    modal.showModal();
  }

  alvo?.addEventListener('change', () => {
    confirmar.disabled = !alvo.value;
  });
  confirmar?.addEventListener('click', () => {
    if (!pendente || enviando || confirmar.disabled) return;
    const acao = pendente;
    const pokemonId = alvoWrap.hidden ? '' : alvo.value;
    pendente = null;
    modal.close();
    acao(pokemonId);
  });
  modal?.querySelector('[data-uso-cancelar]')?.addEventListener('click', () => modal.close());
  modal?.addEventListener('close', () => { pendente = null; });

  // Apenas o clique de confirmação autoriza o requestSubmit seguinte.
  function enviarConfirmado(f) {
    if (!f || enviando) return;
    autorizado = f;
    f.requestSubmit();
    autorizado = null;
  }

  function resumoFormulario(f) {
    const item = f.dataset.itemNome || textoSelecionado(f, 'item_id')
      || f.querySelector('input[type="search"]')?.value || 'item';
    const qtd = campo(f, 'quantidade')?.value;
    switch (f.dataset.confirmacao) {
      case 'transferir':
        return ['Confirmar transferência', `Enviar ${qtd} × ${item} para ${textoSelecionado(f, 'personagem_destino_id')}?`];
      case 'devolver':
        return ['Confirmar devolução', `Devolver ${item} de ${f.dataset.pokemonNome} à mochila?`];
      case 'adicionar':
        return ['Confirmar adição', `Adicionar ${qtd} × ${item} ao inventário?`];
      case 'ajustar':
        return ['Confirmar quantidade', `Definir a quantidade de ${item} como ${qtd}?${qtd === '0' ? ' O item será removido da mochila.' : ''}`];
      default: return null;
    }
  }

  for (const f of [form, ...root.querySelectorAll('form[data-confirmacao]')].filter(Boolean)) {
    f.addEventListener('submit', (ev) => {
      if (enviando) { ev.preventDefault(); return; }
      if (autorizado === f) { enviando = true; return; }
      ev.preventDefault();
      if (f === form) return;
      if (f.dataset.confirmacao === 'adicionar' && !campo(f, 'item_id')?.value) {
        informar('Escolha um item do catálogo antes de adicionar.', 'aviso');
        return;
      }
      const dados = resumoFormulario(f);
      if (dados) abrir(dados[0], dados[1], () => enviarConfirmado(f));
    });
  }

  for (const botao of root.querySelectorAll('[data-ativar-uso]')) {
    botao.addEventListener('click', () => {
      if (enviando) return;
      const tipo = botao.dataset.tipoUso;
      const id = botao.dataset.ativarUso;
      const nome = nomeItem(id);
      if (tipo === 'mapa') { mapa?.showModal(); return; } // somente leitura
      const usar = (pokemonId) => {
        campo(form, 'item_id').value = id;
        campo(form, 'pokemon_id').value = pokemonId;
        enviarConfirmado(form);
      };
      if (tipo === 'registro') {
        abrir('Confirmar uso', `Consumir 1 × ${nome}? Este item não possui efeito automático; o uso será registrado.`, usar);
      } else if (tipo === 'terapia') {
        const candidatos = cards.filter(card => elegivel(efeitos(id), atributos(card)));
        if (!candidatos.length) {
          abrir('Uso indisponível', `Nenhum Pokémon da equipe pode receber o efeito de ${nome} agora.`, null);
          confirmar.disabled = true;
          return;
        }
        abrir('Confirmar uso', `Consumir 1 × ${nome} no Pokémon escolhido?`, usar, candidatos);
      }
    });
  }

  // O próprio modal de equipamento é a confirmação; a escolha continua
  // obrigatória, incluindo indicação de troca quando há item equipado.
  for (const botao of root.querySelectorAll('[data-equipar-item]')) {
    botao.addEventListener('click', () => {
      if (enviando || !equipar || equipar.open) return;
      campo(equipForm, 'item_id').value = botao.dataset.equiparItem;
      campo(equipForm, 'pokemon_id').value = '';
      equipar.querySelector('[data-equipar-resumo]').textContent =
        `Equipar 1 × ${nomeItem(botao.dataset.equiparItem)} no Pokémon escolhido? Se já houver um item equipado, ele voltará à mochila.`;
      equipar.showModal();
    });
  }
  equipForm?.addEventListener('submit', (ev) => {
    if (enviando || !equipar.open) { ev.preventDefault(); return; }
    enviando = true;
  });
  equipar?.querySelector('[data-equipar-cancelar]')?.addEventListener('click', () => equipar.close());
  // Navegação de volta pelo cache do navegador não deve bloquear novas ações.
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) { enviando = false; autorizado = null; }
  });
})();
