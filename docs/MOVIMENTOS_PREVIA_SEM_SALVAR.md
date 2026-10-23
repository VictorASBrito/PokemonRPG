# Movimentos — apresentação e prévia sem salvar

- A ficha de Pokémon mostra quatro posições de golpes com estilo do tema (claro/escuro).
- O autocomplete visual **existente** foi mantido. Ao selecionar um golpe, ele emite o evento `catalogo:selecionado` com os dados públicos do catálogo.
- O formulário atualiza imediatamente tipo traduzido, categoria, dano, precisão e descrição da prévia, **sem nenhuma escrita no PostgreSQL**.
- Digitar outro nome limpa os detalhes anteriores para não exibir dados de um golpe que já não está selecionado.
- Os quatro cartões de descrição substituem as antigas caixas claras dos efeitos e ficam coerentes com os dois temas.
- Somente **Salvar Pokémon** persiste os golpes equipados. As permissões de Jogador, Tester e Admin permanecem iguais.

## Atualização

Preserve `.env`, `data/` e `static/uploads/`, substitua os arquivos do projeto e reinicie `python servidor_teste.py`.
Não há migration nova. Se necessário, recarregue a página com `Ctrl + F5`.

## Verificação

1. Abra a ficha de um Pokémon e entre na seção Golpes.
2. Selecione um golpe no menu visual e confira a alteração imediata da categoria, tipo, dano, precisão e descrição.
3. Selecione outro golpe; confira que a prévia é substituída.
4. Apague um golpe; confirme o retorno ao estado vazio.
5. Atualize a página **sem salvar**; confira que a alteração não foi persistida.
6. Repita salvando; confirme que a alteração ficou registrada.
7. Repita em modo claro e escuro.
