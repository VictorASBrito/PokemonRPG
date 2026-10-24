# Itens e inventário no PostgreSQL

Esta etapa torna o PostgreSQL a fonte oficial para o catálogo de itens e para
todas as movimentações do inventário dos personagens.

## Funcionalidades entregues

### Catálogo administrativo de itens

O mestre pode acessar:

```text
/mestre/catalogo/itens
```

A tela permite:

- pesquisar por nome, código ou descrição;
- filtrar por categoria, situação, origem e uso;
- criar categorias durante o cadastro;
- criar, editar e duplicar itens;
- configurar preço, imagem e descrição;
- definir se o item é consumível, equipável ou utilizável em batalha;
- criar efeitos por um editor visual;
- desativar e reativar registros sem apagar vínculos antigos;
- registrar as alterações em `historico_alteracoes`.

Os efeitos são armazenados em `itens.efeitos` com estrutura versionada. Os tipos
iniciais incluem recuperação de PV, remoção de status, alteração de atributo,
dano, modificador de cálculo, evolução, Mega Evolução e efeito textual.

> O botão de uso consome a quantidade e registra os efeitos configurados no
> histórico. A execução automática de cura, dano ou status será integrada ao
> futuro assistente de combate.

### Inventário do personagem

O jogador pode acessar:

```text
/jogador/inventario
```

O mestre pode abrir o inventário de qualquer personagem da campanha por:

```text
/mestre/jogadores/<personagem_id>/inventario
```

A tela permite:

- pesquisar e filtrar os itens possuídos;
- consultar quantidades e efeitos;
- consumir itens marcados como consumíveis;
- entregar um item equipável a um Pokémon;
- devolver um item carregado ao inventário;
- trocar o item carregado, devolvendo automaticamente o anterior;
- transferir unidades para outro personagem da mesma campanha;
- adicionar itens e ajustar quantidades quando o acesso é do mestre.

As operações usam bloqueio de linha durante mudanças de quantidade e impedem:

- quantidades negativas;
- consumo acima da quantidade disponível;
- transferência para o próprio personagem;
- transferência entre campanhas diferentes;
- equipamento de item inativo ou não equipável;
- acesso do mestre a personagens de outra campanha.

## Mudança importante nas fichas

O inventário não é mais editado como texto livre na ficha do personagem. A
ficha apresenta um resumo e um link para a tela oficial do inventário.

O item carregado também não é alterado diretamente na ficha do Pokémon. Isso
evita criar ou remover unidades sem movimentar `personagem_itens`.

O fluxo oficial é:

```text
Inventário → escolher item → escolher Pokémon → equipar
```

Ao desequipar, uma unidade volta ao inventário. Ao substituir o item, o item
anterior também retorna automaticamente.

## Migration

Esta versão adiciona:

```text
d94c7ab20e51_catalogo_itens_e_inventario.py
```

Ela inclui em `itens`:

```text
preco
consumivel
equipavel
uso_em_batalha
```

A migration também marca como equipáveis os itens que já estavam carregados por
Pokémon antes da atualização.

Aplique com:

```powershell
flask --app app.py db upgrade
```

Confira:

```powershell
flask --app app.py db current
```

Resultado esperado:

```text
d94c7ab20e51 (head)
```

Não execute novamente a importação dos JSON.

## Diagnósticos

Valide o catálogo:

```powershell
flask --app app.py catalogo verificar
```

O resultado deve incluir:

```text
Catálogo de itens está consistente no PostgreSQL.
```

Valide os inventários:

```powershell
flask --app app.py inventario verificar
```

Resultado esperado:

```text
Itens, inventários e equipamentos estão consistentes no PostgreSQL.
```

O diagnóstico verifica preços negativos, quantidades inválidas, referências
órfãs e Pokémon carregando itens que não estão marcados como equipáveis.

## Teste manual recomendado

1. Entre como mestre e abra **Catálogo → Itens**.
2. Crie um item consumível com preço e efeito de recuperação de PV.
3. Crie ou edite um item equipável.
4. Abra o inventário de um jogador.
5. Adicione três unidades do item consumível.
6. Consuma uma unidade e confirme a nova quantidade.
7. Adicione uma unidade do item equipável.
8. Entregue o item a um Pokémon e confirme que ele saiu do inventário.
9. Retire o item do Pokémon e confirme que ele retornou.
10. Transfira uma unidade para outro personagem da campanha.
11. Atualize a página e reinicie o servidor para validar a persistência.
12. Abra a ficha do personagem e do Pokémon para confirmar que ambas exibem o
    estado atualizado sem permitir alterações paralelas.

## Tabelas principais

```text
categorias_item
itens
personagem_itens
pokemons
personagens
historico_alteracoes
```

## Revisão incremental do cadastro — 23/10/2026

- No salvamento do catálogo, o backend passa a rejeitar preço não inteiro, negativo ou acima de 999.999.999 Pokédolares, mantendo preço em branco como zero.
- Se todos os efeitos forem removidos durante a edição, uma falha de validação em outro campo não deve repor os efeitos antigos no editor. O banco segue inalterado até um envio válido.
- Os cenários de regressão estão em `tests/test_itens_inventario.py` e **ainda precisam de execução integrada em ambiente com Flask instalado**.
- Nenhuma migration foi adicionada. Esta revisão não altera itens já existentes nem corrige inconsistências armazenadas no banco de produção.


## Auditoria avançada, somente leitura — 23/10/2026

Após a confirmação do usuário de **9 testes aprovados em 10,86 s** na etapa de validação de itens, foi acrescentado um comando diagnóstico independente para os registros do catálogo:

```powershell
flask --app app.py catalogo auditar-itens
```

Para exibir todos os achados (sem limite de 50):

```powershell
flask --app app.py catalogo auditar-itens --todos
```

**O que analisa:** quantidade de itens ativos e por categoria, referências de categorias inexistentes/inativas, códigos equivalentes com diferença de caixa/espaçamento, possíveis nomes repetidos dentro de uma categoria, preços inválidos, JSON de efeitos inválido, formato legado, efeitos com tipo/alvo incorretos e referências a status/atributos/tipos inexistentes ou inativos.

**Como interpretar:**

- `ERRO` indica problema concreto dentro das regras de estrutura/validação do sistema e faz o comando encerrar com erro, **sem alterar dados**.
- `AVISO` indica suspeita, dado legado ou classificação que pode ser intencional; requer decisão do mestre antes de ajustes.
- `0 erro(s), 0 aviso(s)` significa apenas que os testes automatizados de integridade passaram, **não** que todos os itens do manual 2.5 estejam presentes nem que cada preço/efeito esteja correto.

O diagnóstico **não acessa arquivos `.env` no relatório**, não executa correção automática, não importa catálogos e não atualiza migrations. Complemente com:

```powershell
flask --app app.py catalogo verificar
flask --app app.py inventario verificar
```

Para validar os testes após aplicar o pacote:

```powershell
python -m pytest -q tests/test_itens_inventario.py tests/test_auditoria_itens.py
```

**Estado de execução nesta revisão:** oito testes puros passaram e o Python compilou os arquivos novos; testes integrados Flask estão pendentes no ambiente do desenvolvedor. O PostgreSQL da campanha não foi acessado por este pacote. **Não faça mudanças automáticas nos itens antes de analisar os achados e preservar um backup.**

## Revisão de naturezas importadas como equipamento — 23/10/2026

O resultado executado pelo mestre mostrou **110 registros de inventário, 456 unidades e 48 Pokémon com itens equipados**, com integridade referencial confirmada pelo comando `inventario verificar`.

A auditoria `catalogo auditar-itens --todos` apontou avisos exclusivamente associados a itens sem categoria, com códigos `importado-ficha-*`. A leitura do JSON congelado `app/seed/fichas_jogadores_ankar.json` identificou a causa de um subconjunto: **49 campos `item` de Pokémon repetem exatamente o respectivo valor `natureza`**, representando 21 nomes de naturezas distintos. São dados do pacote de origem, não uma consulta ao PostgreSQL; por isso a contagem de vínculos atuais pode divergir de 49.

**Mudança no importador:** `app/commands/planilhas_jogadores.py` deixa de cadastrar/equipar como item um campo `item` igual ao nome da natureza; registra aviso para a importação. O JSON de origem é preservado para rastreabilidade.

**Diagnóstico e reparo controlado (somente campanha Ankar):**

```powershell
flask --app app.py catalogo revisar-naturezas-importadas
```

O comando **simula por padrão** e informa a quantidade de vínculos elegíveis e a quantidade rejeitada por segurança. Um vínculo só será considerado elegível quando **todos** os critérios se verificarem no banco: item criado pelo importador com código `importado-ficha-{slug(nome)}`, mesmo nome que a natureza do Pokémon, personalizado/equipável, sem categoria, preço zero, sem efeito, não consumível, não utilizável em batalha e sem qualquer referência em `personagem_itens`. Vínculos de outras campanhas são ignorados.

Somente após fazer backup, revisar a simulação e aprovar a correção, executar:

```powershell
flask --app app.py catalogo revisar-naturezas-importadas --aplicar
```

Ao aplicar, o comando apenas zera `pokemons.item_equipado_id` para os candidatos, registra cada alteração em `historico_alteracoes` e salva todos os vínculos em uma transação. **Não remove/desativa itens do catálogo, não altera naturezas, PV, quantidades ou registros de inventário.** Como os itens continuam no catálogo sem categoria, os avisos de `auditar-itens` continuarão aparecendo: não os esconda nem classifique artificialmente. Eles precisarão de revisão posterior, incluindo os itens genuínos da ficha.

Verifique depois:

```powershell
flask --app app.py inventario verificar
flask --app app.py catalogo auditar-itens --todos
python -m pytest -q tests/test_reparo_natureza_importada.py tests/test_auditoria_itens.py
```

**Limite da validação:** a análise do JSON de origem e três cenários unitários isolados passaram no ambiente de preparação. O comando Flask e os testes integrados no PostgreSQL **não foram executados** neste ambiente. Em particular, **não execute `jogadores-planilhas importar --aplicar` novamente apenas para corrigir esta falha**; isso não repara a importação existente e pode criar dados desnecessários.


> Observação: a implementação de capturáveis em campo foi iniciada em módulo separado e não altera o inventário nesta etapa.
