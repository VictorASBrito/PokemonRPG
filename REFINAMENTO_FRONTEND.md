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
