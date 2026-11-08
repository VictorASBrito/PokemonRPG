# Etapa 10C.4.2 — Avisos temporários na seleção dos Pokémon

## Motivação

Na tela de inventário da Etapa 10C.4, o pequeno painel verde acima da equipe mostrava mensagens persistentes como:

- “Selecione um Pokémon destacado para usar o item.”
- “Nenhum Pokémon da equipe pode receber o efeito agora.”

A Etapa 10C.4.1 já converteu as mensagens globais `flash()` em notificações flutuantes (*toasts*) por 1,5 segundo, mas essas duas mensagens da mochila eram geradas pelo JavaScript local, sem passar pelo Flask.

## Comportamento novo

1. **Usar Poção com Pokémon feridos:** aparece um toast informativo por **1,5 segundo** no canto superior direito. Os Pokémon elegíveis **continuam destacados** após o desaparecimento do toast, até o jogador escolher um alvo ou cancelar.
2. **Nenhum Pokémon elegível:** aparece um toast de aviso por **1,5 segundo**; nenhum cartão de Pokémon permanece ativo, não se envia formulário e não se consome nenhum item.
3. **Cancelar:** enquanto houver escolha pendente, um pequeno botão **Cancelar** aparece ao lado do nome da BAG. Ele não é uma notificação: permanece acessível até encerrar a seleção.
4. **Trocar de aba ou item:** cancela o modo de seleção e fecha o aviso contextual ainda exibido.
5. **Cura aplicada:** o servidor continua validando Pokémon, PV/status e quantidade; a mensagem de sucesso gerada por `flash()` utiliza a notificação global já existente.

## Arquivos alterados pelo instalador

- `templates/jogador/inventario.html`: remove o banner acima da equipe e posiciona um botão discreto de cancelamento no cabeçalho BAG.
- `static/js/inventario-uso-10c4.js`: utiliza a API de toast global para as mensagens de seleção, sem mudar as regras de elegibilidade.
- `static/js/avisos-toast-10c4-1.js`: expõe `window.PokemonRPGToast.mostrar(texto, tipo)` e `.fecharDinamico()` para mensagens criadas sem recarregamento de página. Reutiliza o mesmo temporizador, estilos, fechamento e pausa por foco/mouse das notificações Flask.
- `static/css/inventario-uso-10c4.css`: remove o estilo do banner persistente e acrescenta o botão de cancelamento compacto.
- `templates/base.html`: atualiza a versão do arquivo JS global para contornar o cache do navegador.

O script salva cópias `.bak-10c4-2` e pode ser reexecutado sem duplicar as mudanças. Ele verifica se **10C.4 (inventário visual)** e **10C.4.1 (toasts globais)** já estão instaladas. Não executa migrações nem acessa o PostgreSQL.

## Instalação

1. Faça um commit local ou backup dos arquivos do projeto antes de instalar.
2. Extraia `Ankar_v10_10C_4_2_Avisos_Selecao_Pokemon.zip` na raiz do `PokemonRPG`.
3. Execute:

```powershell
python scripts/instalar_aviso_selecao_10c4_2.py
python -m pytest -q tests/test_aviso_selecao_10c4_2.py
```

4. Reinicie o Flask e recarregue o navegador com `Ctrl+F5`.
5. Teste: (a) Poção em um Pokémon ferido; (b) Poção quando todos estiverem com PV cheio; (c) Cancelar após aparecer a notificação; (d) aplicação e contagem de itens após a cura.

## Pendências visuais mantidas

- Ajustes finos da área de gerenciamento do mestre em telas menores.
- Revisão do layout responsivo da mochila.

Nenhum item, Pokémon, quantidade ou relação no banco é criado, removido ou atualizado pela **instalação deste pacote**.
