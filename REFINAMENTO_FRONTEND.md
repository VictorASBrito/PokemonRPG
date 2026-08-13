# Refinamento do frontend

Esta etapa torna a interface mais densa e adequada ao uso durante a sessão.

## Layout fluido

O contêiner principal não possui mais largura máxima de 1180 px. Em telas grandes ele usa praticamente toda a largura disponível, mantendo apenas uma margem lateral pequena e responsiva.

Os cabeçalhos hero das páginas operacionais foram ocultados visualmente. Os títulos continuam no HTML/título do documento para contexto e acessibilidade, enquanto os botões da página permanecem disponíveis em uma barra compacta.

## Tema claro e escuro

O botão **Tema** na barra superior alterna entre claro e escuro. A escolha fica armazenada no navegador em `localStorage` (`pokemon-rpg-tema`) e não exige alteração no banco de dados.

Na primeira visita, quando ainda não existe escolha salva, a interface respeita a preferência de tema do sistema operacional.

## Pokébola

O ícone da marca usa `static/img/pokebola.png`, baseado no arquivo fornecido para o projeto. O mesmo ícone substitui o símbolo genérico usado no cartão Pokémon do catálogo.

## Foto do personagem

A ficha permite manter uma URL externa ou enviar PNG, JPG/JPEG, WEBP ou GIF. Uploads são armazenados em:

```text
static/uploads/perfis/
```

O PostgreSQL continua guardando apenas a URL em `personagens.foto_url`, portanto nenhuma migration foi necessária.

O comando `flask --app app.py midia verificar` também passa a validar as imagens de perfil.

## Backup

Como os perfis agora também podem usar arquivos locais, preserve sempre:

```text
.env
static/uploads/
```

junto ao backup do PostgreSQL.

## Segunda rodada — contraste escuro e equipe expansível

- O modo escuro recebeu uma nova hierarquia de contraste para aproximar a leitura do modo claro: fundo, cartões, superfícies internas, bordas e texto secundário agora possuem separação visual maior.
- Slots vazios da Box/equipe/dashboard deixaram de usar os tons claros herdados do tema padrão.
- As áreas de arte dos Pokémon continuam claras para preservar a leitura de sprites e PNGs, enquanto os cartões permanecem escuros.
- O dashboard do jogador passa a exibir a equipe em 3 colunas nos desktops, formando duas fileiras de 3 slots.
- Clicar em um Pokémon no dashboard não abre mais a edição imediatamente. O cartão passa para o modo de foco, ocupa a maior área da equipe e mostra atributos atuais, bases, natureza, gênero, status, item, dados de defesa, golpes detalhados e anotações.
- Os demais Pokémon são reorganizados em uma coluna compacta à direita. Clicar em outro Pokémon troca o foco; clicar novamente no Pokémon em foco ou pressionar `Esc` retorna à grade normal.
- A edição continua acessível por um botão explícito dentro da visualização expandida.


## Ajuste de contraste, retratos e densidade da equipe

- O modo escuro não usa mais fundos claros nos retratos de Pokémon; sprites ficam sobre uma superfície escura com brilho radial sutil.
- O dashboard mantém a equipe em grade 3x2 e corrige a largura do retrato para impedir sobreposição com nome/PV.
- No modo expandido, o cartão principal deixa de recolher por clique. O retorno ocorre pelo botão **Recolher** ou pela tecla `Esc`, permitindo selecionar e copiar informações.
- A tela de Equipe utiliza até 6 Pokémon por linha no desktop.
- A Equipe ativa dentro da Box e a própria Box utilizam até 6 cartões por linha no desktop, com quebra responsiva em telas menores.
