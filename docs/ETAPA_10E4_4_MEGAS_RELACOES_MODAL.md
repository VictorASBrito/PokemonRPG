# 10E.4.4 — Mega Evoluções por relações do catálogo e modal de confirmação

## Diagnóstico

A administração já possuía a relação `mega` em `EvolucaoPokemon.requisitos["tipo_relacao"]`, mas o sistema de transformação do jogador verificava somente a lista fixa `data/referencias/transformacoes_10e4.json`. Isso impedia que uma ligação manual — por exemplo `Scolipede → Scolipede (Mega)` — aparecesse como opção no Painel, mesmo se cadastrada.

## Nova fonte para Mega

- `app/services/transformacoes_service.py` consulta **as relações Mega do catálogo** para a forma permanente atual do Pokémon.
- Se houver pelo menos uma relação do tipo Mega cadastrada para essa forma, somente os destinos de **relações ativas** são oferecidos. Relações inativas não são oferecidas. Isso permite ao mestre editar/desativar uma Mega já conhecida do JSON.
- Se **não houver nenhuma relação Mega cadastrada**, a lista local verificada da versão 10E.4 continua funcionando como compatibilidade com campanhas existentes.
- Destinos precisam existir, estar ativos, ter categoria `mega` e pertencer à **mesma espécie** da origem; códigos livres sem relação não autorizam Mega.
- O botão de Mega só é efetivamente ativável para o dono do Pokémon quando o mestre autorizou o **treinador**, o Pokémon possui PV e nenhuma outra Mega desse treinador está ativa. Não depende do Campo nem exige Mega Pedra ou Pedra Chave. Forma permanente e dados pessoais são preservados.
- Novas ligações são gravadas pelo fluxo administrativo já existente, com log de auditoria; **nenhuma migração** é necessária.

## Configurar Scolipede

1. No Catálogo do Mestre, abrir a forma principal **Scolipede** e selecionar **Relações**.
2. Pesquisar `Scolipede` como destino, escolher **Scolipede (Mega)**, com `categoria=mega` (mesma espécie).
3. Ao escolher Mega, o formulário seleciona **Mega Evolução temporária** e **Evento ou condição especial**.
4. Não é necessário informar nível, item, pedra ou texto de condição; o requisito operacional é a permissão Mega do treinador. Notas do mestre e referências são opcionais.
5. Registrar relação. Se a relação já existir, editar/reativar a relação em vez de criar duplicada.
6. No Painel do Mestre, autorizar a Mega do treinador. O jogador terá o botão **Mega Evoluir + Keystone** no Painel do Pokémon.

Observação: criar/editar a relação no Catálogo não concede automaticamente a permissão Mega ao treinador nem transforma o Pokémon no banco.

## Modal de confirmação

- Evoluir, Mega Evoluir, Mudar de Forma e Reverter Forma na visualização expandida usam um único `<dialog>` nativo de interface, renderizado no centro do site.
- O texto exibe ação, destino e consequência (por exemplo, consumo de item ou irreversibilidade) vindo do `data-confirmacao` existente.
- Cancelar, Esc e clique no fundo fecham sem POST; confirmar realiza um único POST usando `requestSubmit` e os campos/CSRF existentes. O servidor verifica novamente todas as permissões.
- Modal usa `aria-labelledby`, `aria-describedby`, foco inicial em Cancelar e fundo escurecido.
- CSS e JS possuem versão atualizada no template, evitando cache da implantação anterior.

## Arquivos principais

`app/services/transformacoes_service.py`, `app/services/evolucoes_admin_service.py`,
`templates/mestre/catalogo/pokemon_relacoes.html`,
`static/js/relacoes-pokemon.js`,
`templates/jogador/dashboard.html`,
`static/js/dashboard-pokemon.js`, `static/css/dashboard.css`,
`tests/test_painel_expandido_evolucao_10e4_1.py`.

## Testes de regressão

- Relação personalizada Scolipede Mega: antes de cadastrar não aparece; após cadastrar aparece e pode ser ativada com permissão; desativar impede novas escolhas.
- Cadastro impede Mega de outra espécie e seleciona o tipo Mega ao pesquisar destino com categoria Mega.
- HTML do modal existe e JS não chama `window.confirm`.
- Suítes existentes de Mega, evoluções, catálogo e painel continuam ativas no CI.

**Sem migration e sem modificação de dados reais em produção pelo assistente.**
