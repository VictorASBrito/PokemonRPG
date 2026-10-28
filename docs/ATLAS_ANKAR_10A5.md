# Etapa 10A.5 — Navegação fixa pelo mapa da Região de Ankar

**Data:** 28/10/2026. **Escopo:** interface do Atlas, revisão dos pontos interativos e testes. Mantida a Etapa 10A.4.1 (detalhes de Pokémon e modal de geração de capturáveis).

## Mudanças

- Retirados os botões de zoom e “Localizar” da imagem, assim como o seletor duplicado “Localizar no mapa” da coluna da direita. A lista de locais e a pesquisa abaixo do mapa continuam disponíveis.
- Adicionado filtro **Todos · 119** como padrão, com as opções existentes **Rotas · 73**, **Cidades · 26** e **Pontos de interesse · 20**.
- Reposicionados manualmente os **119 pontos** do arquivo `app/data/mapa_ankar_pontos.json` com base nos centros dos números e símbolos da arte original `Mapa.jpg`: 73 rotas, 18 cidades ginásio, 8 auxiliares e 20 pontos de interesse. O JSON mantém os mesmos identificadores, categorias, nomes e propriedades dos locais.
- Reduzido o alvo visual de cada marcador para **17 px** no desktop e **20 px** em telas pequenas. Não há duplicação de números no mapa; os círculos ficam transparentes quando não há foco, hover ou seleção.
- Eliminadas as caixas flutuantes em CSS que transbordavam as bordas. O nome do local selecionado aparece no **Explorador da região**, à direita ou abaixo da imagem.
- A imagem ocupa exatamente o espaço da área do mapa, em proporção **1533:2048**, sem zoom, scrollbar interno, centralização automática ou transformação de escala.
- A seleção por `?local=<slug>#ankar-mapa` e os links para a ficha de cada local continuam funcionando. O primeiro clique mostra o resumo, o segundo abre a ficha. Os links continuam disponíveis por teclado.

## Arquivos do pacote incremental

- `app/data/mapa_ankar_pontos.json` — coordenadas revisadas, sem alteração de catálogo.
- `templates/regiao/indice.html` — novos filtros, sem zoom ou seletor duplicado.
- `static/js/atlas-ankar.js` — filtro Todos e seleção simplificada; módulo de modal de capturáveis preservado.
- `static/css/atlas-ankar.css` — correções de tamanho, alinhamento e limites da área do mapa, sem alterar tema global.
- `tests/test_mapa_ankar_visual.py` — teste antigo atualizado para a interface aprovada (não exige mais zoom).
- `tests/test_ankar_10a5_mapa_fixo.py` — regressões de estrutura, coordenadas, acessibilidade, seleção e documentação.
- `scripts/registrar_atlas_10a5.py` — atualização idempotente dos documentos históricos.

## Aplicação

Extraia o ZIP na **raiz** do PokemonRPG mantendo as pastas. Os arquivos do Atlas desta etapa substituem os correspondentes. Não reinstale a Etapa 10A.4.1 nem substitua os demais arquivos do projeto.

```powershell
python scripts/registrar_atlas_10a5.py
python -m pytest -q tests/test_ankar_10a5_mapa_fixo.py tests/test_mapa_ankar_visual.py tests/test_ankar_10a4.py tests/test_atlas_ankar.py tests/test_atlas_ankar_flask.py
```

Reinicie o servidor e faça recarga forçada de `/regiao/ankar` (`Ctrl+F5`) para descartar versões antigas do CSS/JS. As URLs dos assets desta etapa usam o parâmetro `v10a5` para renovar o cache.

## Validação feita no ambiente de preparo

- `node --check static/js/atlas-ankar.js` — passou.
- `python -m pytest -q tests/test_ankar_10a5_mapa_fixo.py tests/test_mapa_ankar_visual.py` — **12 testes passaram**.
- Navegador Chromium (renderização isolada): larguras 1440, 820 e 390 px, sem rolagem horizontal da página nem interna da imagem; filtro **Todos = 119**, Rotas = 73, Cidades = 26, POIs = 20; seleção e hover com medidas estáveis e sem erros JavaScript.
- **Pendente:** integração Flask/PostgreSQL e conferência de todos os pontos no navegador instalado pelo responsável pela campanha. A página de capturáveis não foi alterada.

**Sem migrations; sem alteração no banco, nas planilhas XLSX ou no GitHub.**
