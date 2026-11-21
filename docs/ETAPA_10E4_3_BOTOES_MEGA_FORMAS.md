# Etapa 10E.4.3 — Botões de Mega e formas no retrato

Correção após revisão visual do painel expandido (Morpeko, Castform e Blaziken).

## Regras de apresentação

- Os controles continuam ancorados no rodapé da **imagem do Pokémon**, com evolução à esquerda e formas/Mega à direita. Não há uma faixa de controles sob os golpes.
- **Mega única e liberada:** botão direto com **KeyStone + Mega Evoluir**. Se a Mega não estiver liberada, o mesmo rótulo abre menu com a explicação e a opção desabilitada.
- **Uma forma alternativa:** botão direto com a **imagem do destino + nome da forma**, incluindo Shiny quando a forma tiver imagem Shiny cadastrada. Confirmação prévia mantida.
- **Várias alternativas:** botão **Trocar de forma** com ícone de mudança que abre menu suspenso. Cada opção tem miniatura de 34×34 px e nome da forma. Não há alteração da forma até escolher uma opção.
- **Duas ou mais Megas:** botão **KeyStone + Mega Evoluir** abre opções de destino (ex.: Charizard X/Y), respeitando a autorização do mestre.
- **Reverter:** botão de retorno à forma original continua disponível; CSRF e preservação da identidade e dano continuam no serviço.

## Causa e resolução do bug visual

A regra global em `static/css/sistema-ui.css` era
`body.app-shell .retrato-pokemon-dashboard img { width: 100%; height: 100%; ... }`.
Por ser mais específica que as regras de `static/css/dashboard.css`, ela forçava as imagens aninhadas nos controles e menus a ocupar a área inteira do retrato. Isso provocava cortes, imagens gigantes e rolagem dupla (Castform).

Agora a regra afeta **somente `body.app-shell .retrato-pokemon-dashboard > img`**, e os filhos de botões têm tamanho, alinhamento e limites próprios. O menu suspenso abre acima do ícone, com rolagem limitada à lista quando necessário; imagens e textos permanecem no contêiner.

## Arquivos
- `static/css/sistema-ui.css` — seletor restrito à imagem principal.
- `templates/jogador/_acoes_retrato.html` — textos e imagem correta de cada controle.
- `static/css/dashboard.css` — aparência dos botões, limites das miniaturas, dimensionamento responsivo.
- `tests/test_painel_expandido_evolucao_10e4_1.py` — regressões das formas/Mega/CSS.

Sem alterações de esquema, migração ou dados em banco. Revisar no navegador do mestre e dos jogadores após integração.
