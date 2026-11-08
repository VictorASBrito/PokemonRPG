ETAPA 10C.4.2 — AVISOS TEMPORÁRIOS AO USAR ITENS

Requisitos: Etapas 10C.4 e 10C.4.1 já instaladas no PokemonRPG.

1. Extraia o ZIP na raiz do projeto, preservando as pastas.
2. python scripts/instalar_aviso_selecao_10c4_2.py
3. python -m pytest -q tests/test_aviso_selecao_10c4_2.py
4. Reinicie o Flask e use Ctrl+F5.

Alteração: as mensagens do botão Usar que antes apareciam acima dos
Pokémon agora usam os mesmos toasts de 1,5 segundo das mensagens globais.
O botão Cancelar permanece discreto no cabeçalho BAG durante a seleção.

Não modifica o banco, quantidades, regras de cura, outras páginas ou imagens.
Não execute scripts de reconstrução do catálogo por causa deste pacote.

Documentação: docs/ETAPA_10C4_2_AVISOS_SELECAO_POKEMON.md
