# Importação das nove fichas recebidas — campanha Ankar

## Arquivos utilizados

- Ficha Tuts - Pokemon.xlsx
- Ficha Manu - Pokemon.xlsx
- Ficha Braz - Pokemon.xlsx
- Ficha Jão - Pokemon.xlsx
- Ficha Nanda - Pokemon.xlsx
- Ficha Lucas - Pokemon.xlsx
- Ficha Jaré - Pokemon.xlsx
- Ficha Vini - Pokemon.xlsx
- Ficha Mari - Pokemon.xlsx

As planilhas originais **não precisam estar na pasta do projeto**. Os dados foram preparados em `app/seed/fichas_jogadores_ankar.json`.

| Login | Nome exibido | Personagem | Nível | Equipe | Box | Itens distintos |
|---|---|---|---:|---:|---:|---:|
| `tuts` | Tuts | Power | 40 | 6 | 28 | 14 |
| `manu` | Manu | Astrid | 42 | 6 | 37 | 15 |
| `braz` | Braz | Erivaldo Jr | 44 | 6 | 6 | 12 |
| `jao` | Jão | Juliano lima | 40 | 6 | 8 | 14 |
| `nanda` | Nanda | Bili | 40 | 6 | 20 | 12 |
| `lucas` | Lucas | Chelle | 42 | 6 | 12 | 10 |
| `jare` | Jaré | Bartz | 40 | 6 | 8 | 9 |
| `vini` | Vini | Priscilla | 40 | 6 | 12 | 15 |
| `mari` | Mari | Claire François | 40 | 6 | 24 | 8 |

**A senha inicial de todos é `12345`, conforme solicitado.** A primeira autenticação exige que cada um escolha sua própria senha de 10+ caracteres.

## Antes de importar

1. Faça um backup do PostgreSQL e da pasta `static/uploads/`.
2. Preserve `.env`, `data/` e `static/uploads/` ao extrair o projeto.
3. Confira `POKEMON_RPG_CAMPANHA=ankar` e a conexão com o banco.
4. Não execute novamente a importação legada `dados importar`.

## Comandos

Primeiro, verifique se o banco está atualizado:

```powershell
flask --app app.py db current
```

Simule a importação **sem gravar nenhum registro**:

```powershell
flask --app app.py jogadores-planilhas importar
```

Analise os avisos de espécies, naturezas e golpes sem correspondência. Para gravar:

```powershell
flask --app app.py jogadores-planilhas importar --aplicar
```

Ou importe apenas uma ficha:

```powershell
flask --app app.py jogadores-planilhas importar --login manu --aplicar
```

Confira:

```powershell
flask --app app.py usuarios verificar
flask --app app.py pokemon verificar
flask --app app.py inventario verificar
```

## Política de importação

- Cria somente contas e personagens **que ainda não existem** no banco.
- Se o login já existir, preserva o registro e não redefine a senha.
- Se já houver personagem ativo com o mesmo nome na campanha, pula para evitar duplicação; resolva o vínculo existente manualmente.
- Os Pokémon mantêm o nível **do jogador**; não importamos XP, PP ou amizade.
- As Boxes antigas são reunidas na Box única do personagem, respeitando o limite de 100.
- Nomes de Pokémon, golpes e naturezas só são vinculados quando existe **correspondência não ambígua** no catálogo; não são criadas espécies falsas. Incompatibilidades são apresentadas como avisos antes de gravar.
- Itens do inventário ainda não encontrados no catálogo são registrados como itens personalizados, sem efeitos automáticos inventados.
- Cada ficha é salva em transação própria: erro cancela a importação daquele jogador, sem deixar metade da ficha cadastrada.
- A execução repetida não recria contas já importadas.

## Revisões confirmadas antes da gravação (22/10/2026)

- **Jão / Juliano lima:** o primeiro Pokémon é **Scolipede**, identificado na planilha como `Mega?` por motivos de lore. A espécie usada para vincular ao catálogo será `Scolipede`; a identificação original `Mega?` fica documentada no JSON de importação, sem mudar o apelido **Yoda**, e sem criar uma forma fictícia.
- **Manu / Astrid:** números Shiny confirmados: **1, 12, 20, 26, 37, 45, 60, 80, 82, 100**. O PV que veio em branco continua preparado como 30 (Saúde × 10).
- **Vini / Priscilla:** números Shiny confirmados: **4, 75, 14, 36, 97, 5, 35, 42, 76, 17**.
- **Mari / Claire François:** o PV atual **30** foi preservado, conforme orientação do mestre, apesar de constar `30/24` na planilha.

As fichas originais permanecem intactas: essas correções são aplicadas ao pacote JSON que o importador utiliza. Antes de gravar, revise os alertas do catálogo com a simulação.
- Algumas planilhas identificam o nome do jogador de maneira diferente do nome do arquivo (por exemplo, Tuts/Elliot, Nanda/Mago e Lucas/Luquinhas). O login e o nome da conta usam a identificação do **arquivo enviada pelo mestre**; o nome do personagem segue a célula `NOME` da ficha.

## Acesso remoto

Após importar, inicie o servidor de teste e, em outro terminal, o túnel sem e-mails:

```powershell
python servidor_teste.py
# Segundo terminal:
.\scripts\2_tunel_cloudflare.ps1
```

**Importante:** enquanto uma conta ainda tiver a senha inicial `12345`, outra pessoa que conheça o login poderá tentar acessá-la. Não compartilhe a URL fora do grupo e peça a troca imediata no primeiro login.

## Revisão adicional: naturezas, Bulbasaur Vínculo e PV (22/10/2026)

As quatro listas de naturezas informadas pelo mestre foram aplicadas **na ordem
original dos Pokémon de cada Box**, preservando todos os 54 Pokémon de equipe e
155 registros de Box:

- **Braz**: seis naturezas (Koffing até Chinchou).
- **Nanda**: vinte naturezas (Weezing até Sandile).
- **Lucas**: doze naturezas (Sealeo até Electabuzz).
- **Vini**: doze naturezas (Clamperl até Skrelp).

Nas planilhas dessas quatro pessoas, `Comum` e `Shiny` haviam sido lidos como
se fossem naturezas. Corrigimos o campo e mantivemos a variante Shiny em
**Axew, Prinplup e Simipour (Nanda)** e **Corsola (Lucas)**. Os demais Pokémon
daquelas Boxes, onde estava `Comum`, permanecem comuns.

**Bulbasaur (Vínculo), da Manu:** a simulação anunciará a criação de uma forma
personalizada independente da forma normal do Bulbasaur. Ela ficará vinculada
à espécie **Bulbasaur**, terá tipos **Grama/Veneno**, atributos base **PV 70,
Ataque 9, Defesa 9, Ataque Especial 12, Defesa Especial 11, Velocidade 9** e
as URLs normal/Shiny fornecidas pelo mestre. A forma só será adicionada ao
catálogo ao executar `--aplicar` para a ficha de Manu; é criada na **mesma
transação** que a conta e seus Pokémon. As informações extras `236` e `6%`
foram preservadas em metadados, sem atribuir um significado não confirmado
ou afetar cálculos. Se a forma já existir com esse nome, é reutilizada e
não é sobrescrita.

**Mari:** PV atual permanece **30**. Como a ficha preparada já possui Saúde 3
e a regra padrão de Ankar é 10 PV por ponto, o máximo calculado é **30**;
o aviso anterior de `30/24` foi removido.

**Manu:** o PV inicial preparado continua em 30 porque o campo veio em branco
na planilha. Esse aviso continuará na simulação até confirmação do valor.

### Conferência sem gravar

```powershell
flask --app app.py jogadores-planilhas importar
```

Verifique que não apareçam mais avisos relativos a `Comum`, `Shiny` ou à
inexistência de **Bulbasaur (Vínculo)**; a simulação deverá informar que a
forma especial será cadastrada na aplicação. Persistências só ocorrem com:

```powershell
flask --app app.py jogadores-planilhas importar --aplicar
```

Nenhuma migration nova é necessária para essa revisão. Não repita a importação
legada de catálogo. Faça backup do banco antes de gravar.
