# Pokédex nacional e especificação de evoluções e formas

Data de preparação: 20/11/2026. Branch: feature/pokedex-ordenacao-20261120.

## Diagnóstico comprovado no código

- O catálogo legado tem 1.064 formas e 898 espécies nacionais (Bulbasaur #1, Abomasnow #460, Calyrex #898).
- O campo `especies_pokemon.numero` existia e já era usado para ordenação da página administrativa, mas o importador original o criava como NULL. Assim, a lista caía em ordem alfabética.
- A coluna `ordem_catalogo` no JSON é a **ordem da forma**, e NÃO o número nacional: Venusaur Mega está na posição 4, mas Charmander é a espécie #4.
- O normalizador do importador tratava Nidoran♀ e Nidoran♂ como a mesma espécie; a fonte identifica ambos separadamente.
- O esquema já possui `evolucoes_pokemon`, com vínculos forma_origem/forma_destino e requisitos em JSON, mas o fluxo de evolução ainda não está integrado às fichas. Não presumir que os vínculos estejam populados.

## Etapa P1 — Correção incremental da Pokédex

1. `app/services/pokedex_service.py` obtém o número nacional pela primeira ocorrência de cada espécie no catálogo original, ignorando formas extras. Nidoran♂ recebe código específico `nidoran-m`, preservando o código legado `nidoran` da fêmea.
2. O importador passa a preencher números apenas quando estão vazios; valores definidos manualmente pelo mestre NÃO são sobrescritos.
3. Listagens de formas e autocomplete passam a ordenar pelo número nacional, depois nome da espécie e forma, com desempate por ID.
4. Para **bancos já existentes**, o comando `flask --app app.py catalogo pokedex-preencher` mostra candidatos sem alterar registros. Após backup e revisão, `--aplicar` preenche apenas números ausentes e corrige o vínculo da forma legada `nidoran-2` quando corresponde à fonte original. Não apaga formas, Pokémon de jogador, inventários nem dados de outras espécies.
5. Espécies personalizadas ou não encontradas na fonte permanecem sem número e aparecem após as espécies numeradas. Divergências de números já existentes são apenas reportadas, nunca reescritas automaticamente.
6. Sem migration ou atualização automática do PostgreSQL na instalação do código. Aplicação explícita é obrigatória para corrigir os dados de instalações antigas.

### Instalação segura no computador do mestre

```powershell
# 1) Backup do PostgreSQL e uploads da instalação.
flask --app app.py db current
flask --app app.py catalogo pokedex-preencher
# Conferir candidatos, conflitos e caso Nidoran.
flask --app app.py catalogo pokedex-preencher --aplicar
flask --app app.py catalogo pokedex-preencher
python -m pytest -q tests/test_pokedex_ordenacao.py tests/test_catalogo_admin.py tests/test_importacao_fontes.py
```

Critérios visuais: Bulbasaur #1, Ivysaur #2, Venusaur #3 (suas formas Mega no mesmo número), Charmander #4; Abomasnow #460; espécies regionais com o número da espécie-base; personalizados sem número no final. Validar catálogo e autocomplete no navegador.

## Etapas futuras — Evoluções, variantes e mudança de forma (ainda NÃO implementadas)

### E1. Auditoria e consolidação da genealogia

- Fonte: Ankar e tabela de espécies/formas já existentes, usando o manual PKMRPG 2.5 como apoio, sem desfazer adaptações expressas de Ankar.
- Auditar cada `FormaPokemon` por tipo: normal, regional, mega, alternativa e personalizada. Verificar status, nomes duplicados, atributos base e tipos.
- Auditar `EvolucaoPokemon`: vínculos válidos, ciclos indevidos para evolução irreversível, requisitos, destinos faltantes e forma origem/destino. Registrar a origem de cada regra e listar lacunas para revisão do mestre antes de criar relacionamentos em massa.
- Regional NÃO é evolução da forma normal: Rattata e Rattata (Alola) são variantes da mesma espécie nacional; Rattata (Alola) evolui para Raticate (Alola), jamais para a forma comum por inferência.
- Pokémon personalizados do mestre entram no mesmo grafo, com regras explícitas no cadastro e sem depender de IDs ou nomes fixos do catálogo oficial.

### E2. Relacionamentos administrativos

A tabela `evolucoes_pokemon` já tem origem, destino, tipo_requisito, requisitos JSON e ativo. Recomenda-se um serviço de domínio com tipos de transição explícitos, sem confundir os significados:

| Transição | Exemplo | Requisito | Persistência |
| --- | --- | --- | --- |
| Evolução normal | Charmander → Charmeleon | nível mínimo 16 | Definitiva, voluntária |
| Evolução por item | Espécie A → B | item + regras da campanha | Definitiva, voluntária |
| Evolução alternativa | Eevee → um destino escolhido | condição específica por aresta | Definitiva, voluntária |
| Mudança de forma | Morpeko Forma Cheia ↔ Faminta | condição definida pelo mestre | Reversível |
| Mega Evolução | Charizard → Mega X/Y | Mega Pedra, Pedra Chave, combate | Temporária, nunca substitui espécie permanentemente |
| Formas regionais | Meowth comum / Alola / Galar | escolha de origem, não evolução entre regiões | Variantes distintas sob mesma espécie |

Telas administrativas devem permitir criar, ativar, editar, excluir logicamente e revisar vínculos; mostrar pré-evolução e evoluções possíveis com requisitos. Fazer validação de IDs reais, impedir auto-vínculo e ciclos permanentes e proteger contra apagar vínculos usados em fichas. A criação de espécies ou formas personalizadas pode vincular ao catálogo anterior imediatamente, sem inferência por nome.

### E3. Ações na ficha do Pokémon

- Elegibilidade deve usar **`personagens.nivel`**, nível único compartilhado, não criar nível individual.
- O botão **Evoluir** aparece somente quando existe aresta ativa, destino ativo e requisitos satisfeitos; a evolução não ocorre sem clique.
- Um treinador pode aceitar ou adiar uma evolução. Regras de amizade e XP individual removidas de Ankar NÃO retornam por acidente; requisitos dessas categorias ficam sob decisão do mestre.
- Jogador comum pode executar apenas transições elegíveis explicitamente liberadas; não ganha edição arbitrária de espécie/formas. Tester/Mestre mantêm o que as permissões atuais já autorizam.
- Mudança de forma reversível mostra **Alterar forma**; exemplo prioritário: Morpeko do Bartz. Isso não usa o fluxo de evolução definitiva.
- Ao trocar a forma, recalcular todos os atributos a partir dos novos atributos base sem perder ID do Pokémon, treinador, Shiny, natureza, apelido, equipe, Box, item e histórico; validar preservação de PV e golpes. Guardar auditoria e usar transação atômica com controle de permissão.
- **Decisão de design a confirmar:** preservar o percentual atual de PV ao recalcular máximo ou preservar pontos absolutos até o novo teto; não impor regra silenciosamente.

### E4. Mega Evolução e Campo

- Conforme o manual 2.5 (cap. 9), Mega Evolução é temporária durante batalhas, requer pedra específica e Pedra Chave, ocupa um turno, permite apenas uma Mega ativa por time e desfaz no fim do combate ou ao desmaiar.
- A infraestrutura de Campo até 16 times existe, mas ainda não há um motor de turnos concluído. O estado Mega deve viver no contexto do combate, com retorno garantido à forma original. Não gravar uma Mega como evolução permanente da ficha.
- Recomenda-se testar troca de Pokémon, saída de Campo, retorno de Pokébola, desmaio, encerramento e conflitos de simultaneidade antes de ativar no site.

### E5. Casos de aceitação

Bulbasaur → Ivysaur → Venusaur; Charmander → Charmeleon → Charizard → Mega X/Y; formas Alola/Galar com linhas evolutivas regionais; Eevee com múltiplos destinos; Morpeko reversível; espécies personalizadas encadeadas pelo mestre; níveis abaixo do mínimo; destino inativo; item ausente; Pv recalculado; jogador sem permissão; duas solicitações simultâneas.

**Importante:** E1–E5 constituem um roteiro técnico proposto, NÃO funcionalidades entregues pelo PR P1.


## Auditoria preliminar da fonte de formas (GitHub, 20/11/2026)

A fonte JSON foi lida integralmente, sem consultar ou alterar o PostgreSQL do mestre. Aplicando a mesma regra de classificação do importador aos 1.064 registros: 871 formas marcadas como normal, 38 regionais, 50 Mega e 105 alternativas. São categorias de registros da fonte, não uma confirmação de vínculos evolutivos.

- Morpeko tem duas formas catalogadas: **Morpeko (Satisfeito)** e **Morpeko (Faminto)**; ambas estão classificadas como alternativas. A associação reversível precisa ser cadastrada explicitamente.
- Rattata e Raticate de Alola, Meowth de Alola/Galar, Persian de Alola e Darumaka de Galar já aparecem como formas regionais separadas na fonte.
- Darmanitan de Galar usa os nomes **Darmanitan (Galar Normal)** e **Darmanitan (Galar Zen)**; a forma comum também se chama **Darmanitan (Normal)**, razão pela qual uma verificação ingênua de nomes sem parênteses não encontra uma forma-base literal.
- O agrupamento de espécies da importação deve ser auditado após o reparo dos dois Nidoran. A mera existência de formas regionais NÃO comprova que os vínculos entre origem e destino estão corretos.

**CI do PR #9:** workflow Pokédex concluído com sucesso: 10 testes passaram em 6,10 s no GitHub Actions (Python 3.12, SQLite de testes). Não substitui validação no PostgreSQL real.
