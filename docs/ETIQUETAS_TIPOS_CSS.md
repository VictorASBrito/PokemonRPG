# Etiquetas de tipos Pokémon — CSS e tradução

## O que mudou

As etiquetas agora são renderizadas como pequenos `<span>` com cor, contorno,
brilho suave e texto em português, tomando como referência a **aparência** das
etiquetas enviadas pelo mestre. Não são utilizadas imagens recortadas. As imagens
PNG antigas foram removidas do pacote.

O componente compartilhado `templates/componentes/tipos.html` é usado nos
cartões do dashboard do jogador (normal, expandido e lateral), na equipe, na
Box, na edição de Pokémon, no catálogo e no painel do mestre.

A tradução e normalização de aliases conhecidos ficam em
`app/services/tipos_visual.py` (filtro Jinja `tipo_visual`). Por exemplo:

- `Fire` ou `Fogo` → **Fogo** (vermelho)
- `Water` ou `Água` → **Água** (azul)
- `Grass` ou `Grama` → **Grama** (verde)
- `Fighting` ou `Lutador` → **Lutador** (marrom)
- `Steel`, `Aço` ou `Metal` → **Metal** (cinza)

Tipos personalizados mantêm a descrição cadastrada, com o visual neutro.
O backend **não modifica os tipos no banco de dados**, suas relações ou a
matriz de efetividade. É somente uma mudança de apresentação.

## Onde personalizar

`static/css/tipos.css` guarda as cores por classe:

```css
.etiqueta-tipo--fire { --tipo-cor: #e1532f; }
```

O tema claro ou escuro não sobrescreve essas cores. O tamanho padrão é uma
mini-etiqueta de 20px de altura, com densidade menor nos painéis compactos.

## Instalação

Atualize os arquivos de código, preservando `.env`, `data/` e
`static/uploads/`. Não é necessária migration. Reinicie o servidor e faça
**Ctrl+F5** no navegador para atualizar o CSS em cache.

Teste com `pytest -q`, especialmente `tests/test_tipos_visuais.py`.
